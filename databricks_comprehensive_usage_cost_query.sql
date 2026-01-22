-- ============================================================================
-- COMPREHENSIVE DATABRICKS USAGE & COST ANALYSIS QUERY (v2 - Corrected)
-- ============================================================================
-- Purpose: Analyze all compute usage including Jobs, SQL, Interactive clusters,
--          and DLT pipelines with full cost, cluster details, and execution metrics
-- 
-- Captures:
--   - Job runs (scheduled and manual)
--   - SQL warehouse queries
--   - Interactive/All-purpose cluster usage
--   - Pool-based workloads
--   - DLT pipeline runs
--   - Notebook paths, cluster specs, execution time, trigger type
--
-- Fixes in v2:
--   - Fixed FIRST_VALUE window function misuse (replaced with FIRST aggregate)
--   - Fixed workspace_id type comparison
--   - Fixed TIMESTAMPDIFF usage with aggregates
--   - Removed delete_time filter to include deleted resources in historical analysis
--   - Used GROUP BY ALL for cleaner syntax
--   - Fixed job_id type casting for joins
-- ============================================================================

WITH 
-- ============================================================================
-- CTE 1: Get the most recent version of each job (SCD Type 2 handling)
-- Note: Don't filter by delete_time - we want to show info for deleted jobs too
-- ============================================================================
most_recent_jobs AS (
  SELECT
    workspace_id,
    job_id,
    name AS job_name,
    creator_user_name,
    run_as_user_name,
    trigger_type,
    -- Extract cron schedule if exists
    trigger.schedule.quartz_cron_expression AS cron_schedule,
    trigger.schedule.timezone_id AS schedule_timezone,
    paused AS is_paused,
    tags AS job_tags,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.jobs
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 2: Get the most recent version of each cluster (SCD Type 2 handling)
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
    driver_instance_pool_id,
    worker_instance_pool_id,
    dbr_version,
    data_security_mode,
    tags AS cluster_tags,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, cluster_id ORDER BY change_time DESC) AS rn
  FROM system.compute.clusters
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 3: Node type specifications (for cluster sizing details)
-- ============================================================================
node_specs AS (
  SELECT
    node_type,
    core_count,
    memory_mb,
    ROUND(memory_mb / 1024.0, 1) AS memory_gb,
    gpu_count
  FROM system.compute.node_types
),

-- ============================================================================
-- CTE 4: SQL Warehouse information
-- ============================================================================
warehouse_info AS (
  SELECT
    workspace_id,
    warehouse_id,
    warehouse_name,
    warehouse_type,
    warehouse_size,
    min_clusters AS warehouse_min_clusters,
    max_clusters AS warehouse_max_clusters
  FROM system.compute.warehouses
),

-- ============================================================================
-- CTE 5: DLT Pipeline information
-- ============================================================================
most_recent_pipelines AS (
  SELECT
    workspace_id,
    pipeline_id,
    name AS pipeline_name,
    pipeline_type,
    created_by AS pipeline_creator,
    run_as AS pipeline_run_as,
    settings.serverless AS is_serverless_pipeline,
    settings.photon AS is_photon_pipeline,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, pipeline_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.pipelines
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 6: Base usage with cost calculation
-- Joins usage with list_prices to get costs
-- ============================================================================
usage_with_cost AS (
  SELECT
    -- Identifiers
    u.account_id,
    u.workspace_id,
    u.record_id,
    
    -- Usage classification
    u.billing_origin_product,
    u.sku_name,
    u.usage_type,
    
    -- Derive entity type similar to reference query pattern
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
    
    -- Resource identifiers from usage_metadata
    u.usage_metadata.job_id AS job_id,
    u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.job_name AS job_name_from_usage,
    u.usage_metadata.cluster_id AS cluster_id,
    u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    u.usage_metadata.dlt_update_id AS dlt_update_id,
    u.usage_metadata.instance_pool_id AS instance_pool_id,
    u.usage_metadata.node_type AS node_type,
    
    -- Notebook information
    u.usage_metadata.notebook_id AS notebook_id,
    u.usage_metadata.notebook_path AS notebook_path,
    
    -- Endpoint/Serving information
    u.usage_metadata.endpoint_id AS endpoint_id,
    u.usage_metadata.endpoint_name AS endpoint_name,
    
    -- Identity information
    u.identity_metadata.run_as AS run_as,
    u.identity_metadata.created_by AS created_by,
    
    -- Custom tags for cost allocation
    u.custom_tags,
    
    -- Product features
    u.product_features.is_photon AS is_photon,
    u.product_features.is_serverless AS is_serverless,
    u.product_features.jobs_tier AS jobs_tier,
    u.product_features.sql_tier AS sql_tier,
    u.product_features.dlt_tier AS dlt_tier,
    
    -- Time metrics
    u.usage_start_time,
    u.usage_end_time,
    u.usage_date,
    
    -- Usage and cost
    u.usage_quantity,
    u.usage_unit,
    u.usage_quantity * CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_cost

  FROM system.billing.usage u
  
  -- Join to get pricing (same pattern as reference query)
  INNER JOIN system.billing.list_prices lp 
    ON u.cloud = lp.cloud 
    AND u.sku_name = lp.sku_name 
    AND u.usage_start_time >= lp.price_start_time 
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
  
  WHERE 
    -- Date filter - adjust as needed
    u.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    -- Workspace filter - NOTE: workspace_id is BIGINT, use without quotes
    AND u.workspace_id = 5244115429641560
    -- Include all compute-related billing products
    AND u.billing_origin_product IN ('JOBS', 'ALL_PURPOSE', 'SQL', 'DLT', 'MODEL_SERVING', 'SERVERLESS_REAL_TIME_INFERENCE', 'LAKEFLOW_CONNECT')
),

-- ============================================================================
-- CTE 7: Aggregate usage by logical execution unit
-- Uses FIRST() aggregate with TRUE for ignore nulls (Databricks SQL syntax)
-- Uses GROUP BY ALL for cleaner code
-- ============================================================================
aggregated_usage AS (
  SELECT
    workspace_id,
    billing_origin_product,
    entity_type,
    sku_name,
    
    -- Entity identifier: job_id for jobs, pipeline_id for DLT, cluster_id for interactive
    COALESCE(job_id, dlt_pipeline_id, cluster_id, warehouse_id) AS entity_id,
    
    -- Run identifier: job_run_id for jobs, dlt_update_id for DLT
    CASE 
      WHEN billing_origin_product = 'JOBS' THEN job_run_id
      WHEN billing_origin_product = 'DLT' THEN dlt_update_id
      ELSE cluster_id  -- For interactive, group by cluster
    END AS run_id,
    
    -- Job information
    job_id,
    job_run_id,
    
    -- Cluster information  
    cluster_id,
    
    -- SQL Warehouse information
    warehouse_id,
    
    -- DLT Pipeline information
    dlt_pipeline_id,
    dlt_update_id,
    
    -- Pool information
    FIRST(instance_pool_id, TRUE) AS instance_pool_id,
    
    -- Node type used (take first non-null)
    FIRST(node_type, TRUE) AS node_type,
    
    -- Notebook path (take first non-null)
    FIRST(notebook_path, TRUE) AS notebook_path,
    
    -- Job name from usage metadata
    FIRST(job_name_from_usage, TRUE) AS job_name_from_usage,
    
    -- Identity (take first non-null)
    FIRST(run_as, TRUE) AS run_as,
    FIRST(created_by, TRUE) AS created_by,
    
    -- Custom tags (take first non-null)
    FIRST(custom_tags, TRUE) AS custom_tags,
    
    -- Product features (take first non-null)
    FIRST(is_photon, TRUE) AS is_photon,
    FIRST(is_serverless, TRUE) AS is_serverless,
    FIRST(jobs_tier, TRUE) AS jobs_tier,
    
    -- Aggregated metrics
    SUM(usage_quantity) AS total_dbu,
    SUM(list_cost) AS total_list_cost,
    
    -- Time range
    MIN(usage_start_time) AS execution_start_time,
    MAX(usage_end_time) AS execution_end_time,
    
    -- Record counts
    COUNT(DISTINCT record_id) AS usage_record_count

  FROM usage_with_cost
  
  GROUP BY ALL
),

-- ============================================================================
-- CTE 8: Calculate execution duration (separate to avoid aggregate in function)
-- ============================================================================
usage_with_duration AS (
  SELECT
    a.*,
    -- Calculate execution duration in minutes using unix_timestamp
    ROUND(
      (UNIX_TIMESTAMP(a.execution_end_time) - UNIX_TIMESTAMP(a.execution_start_time)) / 60.0, 
      2
    ) AS execution_duration_minutes
  FROM aggregated_usage a
)

-- ============================================================================
-- FINAL SELECT: Join all information together
-- ============================================================================
SELECT
    -- ========================================================================
    -- WORKSPACE INFO
    -- ========================================================================
    u.workspace_id,
    w.workspace_name,
    w.workspace_url,
    
    -- ========================================================================
    -- USAGE TYPE CLASSIFICATION
    -- ========================================================================
    u.billing_origin_product AS usage_category,
    u.entity_type,
    CASE 
      WHEN u.entity_type LIKE '%JOB%' AND u.job_run_id IS NOT NULL THEN 'Job Run'
      WHEN u.entity_type LIKE '%JOB%' AND u.job_run_id IS NULL THEN 'Job Cluster Usage'
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'Interactive Cluster'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'SQL Warehouse Query'
      WHEN u.entity_type LIKE '%PIPELINE%' THEN 'DLT Pipeline Run'
      WHEN u.billing_origin_product = 'MODEL_SERVING' THEN 'Model Serving'
      ELSE u.billing_origin_product
    END AS usage_type_description,
    
    -- ========================================================================
    -- JOB DETAILS
    -- ========================================================================
    u.job_id,
    COALESCE(j.job_name, u.job_name_from_usage) AS job_name,
    u.job_run_id,
    j.creator_user_name AS job_creator,
    j.run_as_user_name AS job_run_as_user,
    
    -- Trigger type determination
    CASE
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'INTERACTIVE'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'SQL_QUERY'
      WHEN u.entity_type LIKE '%PIPELINE%' THEN 
        CASE WHEN p.is_serverless_pipeline = TRUE THEN 'DLT_SERVERLESS' ELSE 'DLT_SCHEDULED' END
      WHEN j.trigger_type IS NOT NULL THEN j.trigger_type
      WHEN j.cron_schedule IS NOT NULL THEN 'CRON'
      WHEN u.job_id IS NOT NULL THEN 'MANUAL_OR_API'
      ELSE 'UNKNOWN'
    END AS trigger_type,
    
    -- Is it a scheduled cron job?
    CASE 
      WHEN j.cron_schedule IS NOT NULL THEN 'SCHEDULED'
      WHEN j.trigger_type = 'CRON' THEN 'SCHEDULED'
      WHEN u.entity_type LIKE '%INTERACTIVE%' THEN 'INTERACTIVE'
      WHEN u.entity_type LIKE '%SQL_WAREHOUSE%' THEN 'AD_HOC'
      ELSE 'MANUAL'
    END AS run_trigger_category,
    
    j.cron_schedule,
    j.schedule_timezone,
    j.is_paused AS job_is_paused,
    
    -- ========================================================================
    -- NOTEBOOK DETAILS
    -- ========================================================================
    u.notebook_path,
    
    -- ========================================================================
    -- CLUSTER DETAILS
    -- ========================================================================
    u.cluster_id,
    c.cluster_name,
    c.cluster_source,
    c.cluster_owner,
    c.dbr_version AS databricks_runtime_version,
    c.data_security_mode,
    
    -- Driver node specifications
    c.driver_node_type,
    driver_specs.core_count AS driver_cores,
    driver_specs.memory_gb AS driver_memory_gb,
    driver_specs.gpu_count AS driver_gpu_count,
    
    -- Worker node specifications
    c.worker_node_type,
    worker_specs.core_count AS worker_cores,
    worker_specs.memory_gb AS worker_memory_gb,
    worker_specs.gpu_count AS worker_gpu_count,
    
    -- Worker count (fixed or autoscale)
    c.worker_count AS fixed_worker_count,
    c.min_autoscale_workers,
    c.max_autoscale_workers,
    
    -- Cluster size description
    CASE 
      WHEN c.worker_count IS NOT NULL THEN 
        CONCAT(
          COALESCE(CAST(c.worker_count AS STRING), '0'), ' workers (fixed) | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A')
        )
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT(
          COALESCE(CAST(c.min_autoscale_workers AS STRING), '0'), '-', 
          COALESCE(CAST(c.max_autoscale_workers AS STRING), '0'), ' workers (autoscale) | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A')
        )
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      ELSE 'Unknown Configuration'
    END AS cluster_size_description,
    
    -- Estimated total cores at max capacity
    COALESCE(driver_specs.core_count, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS max_total_cores,
    
    -- Estimated total memory at max capacity (GB)
    COALESCE(driver_specs.memory_gb, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.memory_gb, 0)) 
      AS max_total_memory_gb,
    
    -- ========================================================================
    -- INSTANCE POOL DETAILS
    -- ========================================================================
    u.instance_pool_id,
    CASE 
      WHEN u.instance_pool_id IS NOT NULL THEN 'Pool-based'
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      ELSE 'On-demand'
    END AS compute_type,
    
    -- ========================================================================
    -- SQL WAREHOUSE DETAILS
    -- ========================================================================
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    CONCAT(
      COALESCE(CAST(wh.warehouse_min_clusters AS STRING), '1'), '-', 
      COALESCE(CAST(wh.warehouse_max_clusters AS STRING), '1')
    ) AS warehouse_cluster_range,
    
    -- ========================================================================
    -- DLT PIPELINE DETAILS
    -- ========================================================================
    u.dlt_pipeline_id,
    u.dlt_update_id,
    p.pipeline_name,
    p.pipeline_type,
    p.pipeline_creator,
    p.pipeline_run_as,
    
    -- ========================================================================
    -- PRODUCT FEATURES
    -- ========================================================================
    u.is_photon,
    u.is_serverless,
    u.jobs_tier,
    u.sku_name,
    
    -- ========================================================================
    -- IDENTITY & COST ALLOCATION
    -- ========================================================================
    COALESCE(u.run_as, j.run_as_user_name, p.pipeline_run_as) AS run_as,
    u.created_by,
    u.custom_tags,
    
    -- Extract common custom tags for easy filtering/grouping
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['OWNER'] AS owner_tag,
    u.custom_tags['ENGAGEMENT_ID'] AS engagement_id,
    u.custom_tags['DEPLOYMENT_ID'] AS deployment_id,
    
    -- ========================================================================
    -- COST METRICS
    -- ========================================================================
    ROUND(u.total_dbu, 4) AS total_dbu,
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    
    -- ========================================================================
    -- EXECUTION TIME METRICS
    -- ========================================================================
    u.execution_start_time,
    u.execution_end_time,
    u.execution_duration_minutes,
    
    -- Format execution time for readability
    CASE 
      WHEN u.execution_duration_minutes IS NULL THEN 'N/A'
      WHEN u.execution_duration_minutes >= 1440 THEN 
        CONCAT(
          CAST(FLOOR(u.execution_duration_minutes / 1440) AS STRING), 'd ', 
          CAST(FLOOR(MOD(u.execution_duration_minutes, 1440) / 60) AS STRING), 'h ',
          CAST(CAST(MOD(u.execution_duration_minutes, 60) AS INT) AS STRING), 'm'
        )
      WHEN u.execution_duration_minutes >= 60 THEN 
        CONCAT(
          CAST(FLOOR(u.execution_duration_minutes / 60) AS STRING), 'h ', 
          CAST(CAST(MOD(u.execution_duration_minutes, 60) AS INT) AS STRING), 'm'
        )
      ELSE 
        CONCAT(CAST(ROUND(u.execution_duration_minutes, 1) AS STRING), 'm')
    END AS execution_duration_formatted,
    
    -- Execution hours (for easier aggregation)
    ROUND(u.execution_duration_minutes / 60.0, 2) AS execution_duration_hours,
    
    -- ========================================================================
    -- METADATA
    -- ========================================================================
    u.usage_record_count,
    u.run_id,
    u.entity_id

FROM usage_with_duration u

-- Join workspace info
LEFT JOIN system.access.workspaces_latest w
  ON u.workspace_id = w.workspace_id

-- Join job info (job_id in usage is STRING, in jobs table is BIGINT)
LEFT JOIN most_recent_jobs j
  ON u.entity_type LIKE '%JOB%'
  AND u.workspace_id = j.workspace_id 
  AND u.job_id = CAST(j.job_id AS STRING)

-- Join cluster info
LEFT JOIN most_recent_clusters c
  ON u.workspace_id = c.workspace_id 
  AND u.cluster_id = c.cluster_id

-- Join driver node specs
LEFT JOIN node_specs driver_specs
  ON c.driver_node_type = driver_specs.node_type

-- Join worker node specs  
LEFT JOIN node_specs worker_specs
  ON c.worker_node_type = worker_specs.node_type

-- Join warehouse info
LEFT JOIN warehouse_info wh
  ON u.workspace_id = wh.workspace_id 
  AND u.warehouse_id = wh.warehouse_id

-- Join pipeline info
LEFT JOIN most_recent_pipelines p
  ON u.entity_type LIKE '%PIPELINE%'
  AND u.workspace_id = p.workspace_id 
  AND u.dlt_pipeline_id = p.pipeline_id

ORDER BY 
  u.total_list_cost DESC,
  u.execution_start_time DESC;


-- ============================================================================
-- OPTIONAL: PARAMETERIZED VERSION (for Databricks SQL Dashboards)
-- ============================================================================
-- Uncomment and use with SQL parameters for interactive filtering
/*
WITH 
-- ... (same CTEs as above) ...
-- Replace the WHERE clause in usage_with_cost with:
  WHERE 
    u.usage_date BETWEEN :param_start_date AND :param_end_date
    AND IF(:param_workspace = '<ALL WORKSPACES>', TRUE, w.workspace_name = :param_workspace)
    AND IF(:param_run_as = '<ALL USERS>', TRUE, u.identity_metadata.run_as = :param_run_as)
    AND IF(
      :param_cluster_type = '<ALL CLUSTER TYPES>',
      TRUE,
      IF(
        :param_cluster_type = 'Serverless',
        u.product_features.is_serverless = 'true',
        u.product_features.is_serverless = 'false'
      )
    )
*/


-- ============================================================================
-- SUMMARY BY CATEGORY (Optional - Uncomment to use)
-- ============================================================================
/*
SELECT
    billing_origin_product AS usage_category,
    entity_type,
    COUNT(DISTINCT run_id) AS total_runs,
    COUNT(DISTINCT job_id) AS unique_jobs,
    COUNT(DISTINCT cluster_id) AS unique_clusters,
    COUNT(DISTINCT dlt_pipeline_id) AS unique_pipelines,
    ROUND(SUM(total_dbu), 2) AS total_dbu,
    ROUND(SUM(total_list_cost_usd), 2) AS total_cost_usd,
    ROUND(SUM(execution_duration_minutes), 0) AS total_execution_minutes,
    ROUND(SUM(execution_duration_minutes) / 60.0, 1) AS total_execution_hours
FROM (
    -- Insert main query here
)
GROUP BY billing_origin_product, entity_type
ORDER BY total_cost_usd DESC;
*/


-- ============================================================================
-- SUMMARY BY CLIENT/TEAM (Optional - Uncomment to use)
-- ============================================================================
/*
SELECT
    client_name,
    service_line,
    team_name,
    environment,
    COUNT(DISTINCT run_id) AS total_runs,
    ROUND(SUM(total_dbu), 2) AS total_dbu,
    ROUND(SUM(total_list_cost_usd), 2) AS total_cost_usd,
    ROUND(SUM(execution_duration_hours), 1) AS total_execution_hours
FROM (
    -- Insert main query here
)
WHERE client_name IS NOT NULL
GROUP BY client_name, service_line, team_name, environment
ORDER BY total_cost_usd DESC;
*/
