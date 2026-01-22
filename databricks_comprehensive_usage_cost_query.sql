-- ============================================================================
-- COMPREHENSIVE DATABRICKS USAGE & COST ANALYSIS QUERY (v3 - Optimized)
-- ============================================================================
-- Purpose: Analyze all compute usage with cost, cluster details, execution metrics
-- 
-- Optimizations:
--   - Filters pushed to earliest CTEs
--   - Dimension tables filtered by workspace_id
--   - Only necessary columns selected
--   - Conditional joins to avoid unnecessary lookups
--
-- Tables Used (verified against sample data):
--   - system.billing.usage (usage records)
--   - system.billing.list_prices (pricing - join on sku_name, cloud, time range)
--   - system.access.workspaces_latest (workspace info - join on workspace_id)
--   - system.lakeflow.jobs (job definitions - join on job_id as STRING)
--   - system.compute.clusters (cluster info - join on cluster_id)
--   - system.compute.node_types (node specs - join on node_type)
--   - system.compute.warehouses (SQL warehouses - join on warehouse_id)
--   - system.lakeflow.pipelines (DLT pipelines - join on pipeline_id)
--
-- Key Type Notes:
--   - usage_metadata.job_id is STRING, jobs.job_id is BIGINT (cast required)
--   - product_features.is_serverless is STRING ("true"/"false"), not BOOLEAN
--   - custom_tags is MAP<STRING,STRING>, access via ['key']
-- ============================================================================

-- Configuration: Set your filters here
-- Date Range: 2025-01-01 to 2025-12-31
-- Workspace ID: 5244115429641560

WITH 
-- ============================================================================
-- CTE 1: FILTERED USAGE WITH COST (Primary filter - runs first)
-- All filters applied here to reduce data early
-- ============================================================================
usage_with_cost AS (
  SELECT
    u.workspace_id,
    u.record_id,
    u.billing_origin_product,
    u.sku_name,
    
    -- Entity type classification
    CONCAT_WS(
      ' ',
      CASE WHEN u.product_features.is_serverless = 'true' THEN 'SERVERLESS' ELSE '' END,
      CASE 
        WHEN u.billing_origin_product = 'JOBS' THEN 'JOB'
        WHEN u.billing_origin_product = 'DLT' THEN 'PIPELINE'
        WHEN u.billing_origin_product = 'ALL_PURPOSE' THEN 'INTERACTIVE'
        WHEN u.billing_origin_product = 'SQL' THEN 'SQL_WAREHOUSE'
        ELSE u.billing_origin_product
      END
    ) AS entity_type,
    
    -- Resource identifiers (only what we need)
    u.usage_metadata.job_id AS job_id,
    u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.job_name AS job_name_from_usage,
    u.usage_metadata.cluster_id AS cluster_id,
    u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    u.usage_metadata.dlt_update_id AS dlt_update_id,
    u.usage_metadata.instance_pool_id AS instance_pool_id,
    u.usage_metadata.node_type AS node_type,
    u.usage_metadata.notebook_path AS notebook_path,
    
    -- Identity
    u.identity_metadata.run_as AS run_as,
    
    -- Custom tags
    u.custom_tags,
    
    -- Product features
    u.product_features.is_serverless AS is_serverless,
    
    -- Time metrics
    u.usage_start_time,
    u.usage_end_time,
    
    -- Cost calculation
    u.usage_quantity,
    u.usage_quantity * CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_cost

  FROM system.billing.usage u
  INNER JOIN system.billing.list_prices lp 
    ON u.cloud = lp.cloud 
    AND u.sku_name = lp.sku_name 
    AND u.usage_start_time >= lp.price_start_time 
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
  
  WHERE 
    -- *** PRIMARY FILTERS - Applied first for optimization ***
    u.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND u.workspace_id = 5244115429641560
    AND u.billing_origin_product IN ('JOBS', 'ALL_PURPOSE', 'SQL', 'DLT')
),

-- ============================================================================
-- CTE 2: WORKSPACE INFO (Filtered by workspace_id)
-- ============================================================================
workspace_info AS (
  SELECT
    workspace_id,
    workspace_name,
    workspace_url
  FROM system.access.workspaces_latest
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 3: JOBS (Filtered by workspace_id, most recent version only)
-- ============================================================================
most_recent_jobs AS (
  SELECT
    workspace_id,
    job_id,
    name AS job_name,
    creator_user_name,
    run_as_user_name,
    trigger_type,
    trigger.schedule.quartz_cron_expression AS cron_schedule,
    trigger.schedule.timezone_id AS schedule_timezone,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.jobs
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 4: CLUSTERS (Filtered by workspace_id, most recent version only)
-- ============================================================================
most_recent_clusters AS (
  SELECT
    workspace_id,
    cluster_id,
    cluster_name,
    cluster_source,
    owned_by AS cluster_owner,
    driver_node_type,
    worker_node_type,
    worker_count,
    min_autoscale_workers,
    max_autoscale_workers,
    dbr_version,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, cluster_id ORDER BY change_time DESC) AS rn
  FROM system.compute.clusters
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 5: NODE SPECS (Only for node types used in our data)
-- ============================================================================
node_specs AS (
  SELECT DISTINCT
    ns.node_type,
    ns.core_count,
    ROUND(ns.memory_mb / 1024.0, 1) AS memory_gb
  FROM system.compute.node_types ns
  WHERE EXISTS (
    SELECT 1 FROM usage_with_cost u WHERE u.node_type = ns.node_type
  )
  OR EXISTS (
    SELECT 1 FROM most_recent_clusters c 
    WHERE c.driver_node_type = ns.node_type OR c.worker_node_type = ns.node_type
  )
),

-- ============================================================================
-- CTE 6: SQL WAREHOUSES (Filtered by workspace_id)
-- Note: warehouse_id column required for join with usage_metadata.warehouse_id
-- ============================================================================
warehouse_info AS (
  SELECT
    workspace_id,
    warehouse_id,  -- Join key to usage_metadata.warehouse_id
    warehouse_name,
    warehouse_type,
    warehouse_size
  FROM system.compute.warehouses
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 7: DLT PIPELINES (Filtered by workspace_id, most recent version only)
-- ============================================================================
most_recent_pipelines AS (
  SELECT
    workspace_id,
    pipeline_id,
    name AS pipeline_name,
    pipeline_type,
    created_by AS pipeline_creator,
    settings.serverless AS is_serverless_pipeline,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, pipeline_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.pipelines
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 8: AGGREGATE USAGE BY RUN
-- ============================================================================
aggregated_usage AS (
  SELECT
    workspace_id,
    billing_origin_product,
    entity_type,
    sku_name,
    
    -- Entity ID
    COALESCE(job_id, dlt_pipeline_id, cluster_id, warehouse_id) AS entity_id,
    
    -- Run ID
    CASE 
      WHEN billing_origin_product = 'JOBS' THEN job_run_id
      WHEN billing_origin_product = 'DLT' THEN dlt_update_id
      ELSE cluster_id
    END AS run_id,
    
    job_id,
    job_run_id,
    cluster_id,
    warehouse_id,
    dlt_pipeline_id,
    dlt_update_id,
    
    FIRST(instance_pool_id, TRUE) AS instance_pool_id,
    FIRST(node_type, TRUE) AS node_type,
    FIRST(notebook_path, TRUE) AS notebook_path,
    FIRST(job_name_from_usage, TRUE) AS job_name_from_usage,
    FIRST(run_as, TRUE) AS run_as,
    FIRST(custom_tags, TRUE) AS custom_tags,
    FIRST(is_serverless, TRUE) AS is_serverless,
    
    -- Aggregated metrics
    SUM(usage_quantity) AS total_dbu,
    SUM(list_cost) AS total_list_cost,
    MIN(usage_start_time) AS execution_start_time,
    MAX(usage_end_time) AS execution_end_time,
    COUNT(DISTINCT record_id) AS usage_record_count

  FROM usage_with_cost
  GROUP BY ALL
),

-- ============================================================================
-- CTE 9: ADD EXECUTION DURATION
-- ============================================================================
usage_with_duration AS (
  SELECT
    a.*,
    ROUND((UNIX_TIMESTAMP(a.execution_end_time) - UNIX_TIMESTAMP(a.execution_start_time)) / 60.0, 2) AS execution_duration_minutes
  FROM aggregated_usage a
)

-- ============================================================================
-- FINAL SELECT
-- ============================================================================
SELECT
    -- WORKSPACE
    u.workspace_id,
    w.workspace_name,
    
    -- ENTITY URL (Clickable link for dashboards)
    CASE 
      WHEN u.entity_type LIKE '%JOB%' AND u.job_id IS NOT NULL THEN 
        CONCAT(
          '<a href="', w.workspace_url, '/jobs/', u.job_id, '" target="_blank">',
          COALESCE(j.job_name, u.job_name_from_usage, u.job_id),
          '</a>'
        )
      WHEN u.entity_type LIKE '%PIPELINE%' AND u.dlt_pipeline_id IS NOT NULL THEN 
        CONCAT(
          '<a href="', w.workspace_url, '/pipelines/', u.dlt_pipeline_id, '" target="_blank">',
          COALESCE(p.pipeline_name, u.dlt_pipeline_id),
          '</a>'
        )
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' AND u.warehouse_id IS NOT NULL THEN 
        CONCAT(
          '<a href="', w.workspace_url, '/sql/warehouses/', u.warehouse_id, '" target="_blank">',
          COALESCE(wh.warehouse_name, u.warehouse_id),
          '</a>'
        )
      WHEN u.entity_type LIKE '%INTERACTIVE%' AND u.cluster_id IS NOT NULL THEN 
        CONCAT(
          '<a href="', w.workspace_url, '/compute/clusters/', u.cluster_id, '" target="_blank">',
          COALESCE(c.cluster_name, u.cluster_id),
          '</a>'
        )
      ELSE COALESCE(j.job_name, p.pipeline_name, c.cluster_name, wh.warehouse_name, u.entity_id)
    END AS entity_url,
    
    -- USAGE CLASSIFICATION
    u.billing_origin_product AS usage_category,
    u.entity_type,
    CASE 
      WHEN u.entity_type LIKE '%JOB%' AND u.job_run_id IS NOT NULL THEN 'Job Run'
      WHEN u.entity_type LIKE '%JOB%' THEN 'Job Cluster'
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'Interactive Cluster'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'SQL Warehouse'
      WHEN u.entity_type LIKE '%PIPELINE%' THEN 'DLT Pipeline'
      ELSE u.billing_origin_product
    END AS usage_type_description,
    
    -- JOB DETAILS
    u.job_id,
    COALESCE(j.job_name, u.job_name_from_usage) AS job_name,
    u.job_run_id,
    j.creator_user_name AS job_creator,
    
    -- TRIGGER TYPE
    CASE
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'INTERACTIVE'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'SQL_QUERY'
      WHEN u.entity_type LIKE '%PIPELINE%' THEN 'DLT_PIPELINE'
      WHEN j.trigger_type IS NOT NULL THEN j.trigger_type
      WHEN j.cron_schedule IS NOT NULL THEN 'CRON'
      WHEN u.job_id IS NOT NULL THEN 'MANUAL_OR_API'
      ELSE 'UNKNOWN'
    END AS trigger_type,
    
    -- SCHEDULED vs MANUAL
    CASE 
      WHEN j.cron_schedule IS NOT NULL OR j.trigger_type = 'CRON' THEN 'SCHEDULED'
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'INTERACTIVE'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'AD_HOC'
      ELSE 'MANUAL'
    END AS run_trigger_category,
    
    j.cron_schedule,
    
    -- NOTEBOOK PATH
    u.notebook_path,
    
    -- CLUSTER DETAILS
    u.cluster_id,
    c.cluster_name,
    c.cluster_source,
    c.driver_node_type,
    driver_specs.core_count AS driver_cores,
    driver_specs.memory_gb AS driver_memory_gb,
    c.worker_node_type,
    worker_specs.core_count AS worker_cores,
    worker_specs.memory_gb AS worker_memory_gb,
    c.worker_count AS fixed_worker_count,
    c.min_autoscale_workers,
    c.max_autoscale_workers,
    
    -- CLUSTER SIZE DESCRIPTION
    CASE 
      WHEN c.worker_count IS NOT NULL THEN 
        CONCAT(c.worker_count, ' workers (fixed) | Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' | Workers: ', COALESCE(c.worker_node_type, 'N/A'))
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT(c.min_autoscale_workers, '-', c.max_autoscale_workers, ' workers (autoscale) | Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' | Workers: ', COALESCE(c.worker_node_type, 'N/A'))
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      ELSE 'Unknown'
    END AS cluster_size_description,
    
    -- TOTAL CORES
    COALESCE(driver_specs.core_count, 0) + (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) AS max_total_cores,
    
    -- INSTANCE POOL
    u.instance_pool_id,
    CASE 
      WHEN u.instance_pool_id IS NOT NULL THEN 'Pool-based'
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      ELSE 'On-demand'
    END AS compute_type,
    
    -- SQL WAREHOUSE
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    
    -- DLT PIPELINE
    u.dlt_pipeline_id,
    u.dlt_update_id,
    p.pipeline_name,
    p.pipeline_type,
    
    -- IDENTITY & TAGS
    u.run_as,
    u.custom_tags,
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['OWNER'] AS owner_tag,
    
    -- COST
    ROUND(u.total_dbu, 4) AS total_dbu,
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    
    -- EXECUTION TIME
    u.execution_start_time,
    u.execution_end_time,
    u.execution_duration_minutes,
    ROUND(u.execution_duration_minutes / 60.0, 2) AS execution_duration_hours,
    
    CASE 
      WHEN u.execution_duration_minutes IS NULL THEN 'N/A'
      WHEN u.execution_duration_minutes >= 1440 THEN 
        CONCAT(FLOOR(u.execution_duration_minutes / 1440), 'd ', FLOOR(MOD(u.execution_duration_minutes, 1440) / 60), 'h ', CAST(MOD(u.execution_duration_minutes, 60) AS INT), 'm')
      WHEN u.execution_duration_minutes >= 60 THEN 
        CONCAT(FLOOR(u.execution_duration_minutes / 60), 'h ', CAST(MOD(u.execution_duration_minutes, 60) AS INT), 'm')
      ELSE CONCAT(ROUND(u.execution_duration_minutes, 1), 'm')
    END AS execution_duration_formatted,
    
    -- METADATA
    u.usage_record_count,
    u.entity_id,
    u.run_id

FROM usage_with_duration u

-- Workspace (pre-filtered)
LEFT JOIN workspace_info w ON u.workspace_id = w.workspace_id

-- Jobs (conditional join - only for JOB entity types)
LEFT JOIN most_recent_jobs j
  ON u.entity_type LIKE '%JOB%'
  AND u.job_id = CAST(j.job_id AS STRING)

-- Clusters
LEFT JOIN most_recent_clusters c ON u.cluster_id = c.cluster_id

-- Node specs for driver
LEFT JOIN node_specs driver_specs ON c.driver_node_type = driver_specs.node_type

-- Node specs for workers
LEFT JOIN node_specs worker_specs ON c.worker_node_type = worker_specs.node_type

-- Warehouses (conditional join - only for SQL entity types)
LEFT JOIN warehouse_info wh
  ON u.entity_type LIKE '%SQL_WAREHOUSE%'
  AND u.warehouse_id = wh.warehouse_id

-- Pipelines (conditional join - only for PIPELINE entity types)
LEFT JOIN most_recent_pipelines p
  ON u.entity_type LIKE '%PIPELINE%'
  AND u.dlt_pipeline_id = p.pipeline_id

ORDER BY u.total_list_cost DESC, u.execution_start_time DESC;
