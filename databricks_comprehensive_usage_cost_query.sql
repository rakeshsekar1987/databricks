-- ============================================================================
-- COMPREHENSIVE DATABRICKS USAGE & COST ANALYSIS QUERY
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
-- ============================================================================

WITH 
-- ============================================================================
-- CTE 1: Get the most recent version of each job (SCD Type 2 handling)
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
  WHERE delete_time IS NULL OR delete_time = '-'
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
  WHERE delete_time IS NULL OR delete_time = '-'
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
pipeline_info AS (
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
  WHERE delete_time IS NULL OR delete_time = '-'
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 6: Unified usage records with cost calculation
-- This is the core CTE that captures ALL usage types
-- ============================================================================
unified_usage_with_cost AS (
  SELECT
    -- Identifiers
    u.account_id,
    u.workspace_id,
    u.record_id,
    
    -- Usage classification
    u.billing_origin_product,
    u.sku_name,
    u.usage_type,
    
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
    
    -- Calculate execution time in minutes for this usage record
    TIMESTAMPDIFF(MINUTE, u.usage_start_time, u.usage_end_time) AS usage_duration_minutes,
    
    -- Usage and cost
    u.usage_quantity,
    u.usage_unit,
    CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_price_per_dbu,
    u.usage_quantity * CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_cost,
    
    -- Effective price (after any promotions)
    CAST(lp.pricing.effective_list.default AS DECIMAL(18, 6)) AS effective_price_per_dbu,
    u.usage_quantity * CAST(lp.pricing.effective_list.default AS DECIMAL(18, 6)) AS effective_cost

  FROM system.billing.usage u
  
  -- Join to get pricing
  INNER JOIN system.billing.list_prices lp 
    ON u.cloud = lp.cloud 
    AND u.sku_name = lp.sku_name 
    AND u.usage_start_time >= lp.price_start_time 
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
  
  WHERE 
    -- Date filter - adjust as needed
    u.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    -- Workspace filter - adjust or remove as needed
    AND u.workspace_id = '5244115429641560'
    -- Include all compute-related billing products
    AND u.billing_origin_product IN ('JOBS', 'ALL_PURPOSE', 'SQL', 'DLT', 'MODEL_SERVING', 'SERVERLESS_REAL_TIME_INFERENCE')
),

-- ============================================================================
-- CTE 7: Aggregate usage by logical execution unit
-- Groups by the appropriate identifier based on usage type
-- ============================================================================
aggregated_usage AS (
  SELECT
    u.workspace_id,
    u.billing_origin_product,
    u.sku_name,
    
    -- Job information
    u.job_id,
    u.job_run_id,
    u.job_name_from_usage,
    
    -- Cluster information  
    u.cluster_id,
    
    -- SQL Warehouse information
    u.warehouse_id,
    
    -- DLT Pipeline information
    u.dlt_pipeline_id,
    u.dlt_update_id,
    
    -- Pool information
    u.instance_pool_id,
    
    -- Node type used
    u.node_type,
    
    -- Notebook path
    FIRST_VALUE(u.notebook_path) IGNORE NULLS OVER (
      PARTITION BY u.workspace_id, u.billing_origin_product, 
                   COALESCE(u.job_run_id, u.cluster_id, u.warehouse_id, u.dlt_update_id)
      ORDER BY u.usage_start_time
    ) AS notebook_path,
    
    -- Identity
    FIRST(u.run_as, TRUE) AS run_as,
    FIRST(u.created_by, TRUE) AS created_by,
    
    -- Custom tags
    FIRST(u.custom_tags, TRUE) AS custom_tags,
    
    -- Product features
    FIRST(u.is_photon, TRUE) AS is_photon,
    FIRST(u.is_serverless, TRUE) AS is_serverless,
    FIRST(u.jobs_tier, TRUE) AS jobs_tier,
    
    -- Aggregated metrics
    SUM(u.usage_quantity) AS total_dbu,
    SUM(u.list_cost) AS total_list_cost,
    SUM(u.effective_cost) AS total_effective_cost,
    SUM(u.usage_duration_minutes) AS total_usage_minutes,
    
    -- Time range
    MIN(u.usage_start_time) AS execution_start_time,
    MAX(u.usage_end_time) AS execution_end_time,
    
    -- Calculate actual execution duration (wall clock time)
    TIMESTAMPDIFF(MINUTE, MIN(u.usage_start_time), MAX(u.usage_end_time)) AS execution_wall_time_minutes,
    
    -- Record counts
    COUNT(DISTINCT u.record_id) AS usage_record_count

  FROM unified_usage_with_cost u
  
  GROUP BY
    u.workspace_id,
    u.billing_origin_product,
    u.sku_name,
    u.job_id,
    u.job_run_id,
    u.job_name_from_usage,
    u.cluster_id,
    u.warehouse_id,
    u.dlt_pipeline_id,
    u.dlt_update_id,
    u.instance_pool_id,
    u.node_type,
    u.notebook_path
)

-- ============================================================================
-- FINAL SELECT: Join all information together
-- ============================================================================
SELECT
    -- ========================================================================
    -- IDENTIFIERS
    -- ========================================================================
    a.workspace_id,
    w.workspace_name,
    
    -- ========================================================================
    -- USAGE TYPE CLASSIFICATION
    -- ========================================================================
    a.billing_origin_product AS usage_category,
    CASE 
      WHEN a.billing_origin_product = 'JOBS' AND a.job_run_id IS NOT NULL THEN 'Scheduled/Triggered Job Run'
      WHEN a.billing_origin_product = 'JOBS' AND a.job_run_id IS NULL THEN 'Job Cluster Usage'
      WHEN a.billing_origin_product = 'ALL_PURPOSE' THEN 'Interactive Cluster'
      WHEN a.billing_origin_product = 'SQL' THEN 'SQL Warehouse Query'
      WHEN a.billing_origin_product = 'DLT' THEN 'DLT Pipeline Run'
      WHEN a.billing_origin_product = 'MODEL_SERVING' THEN 'Model Serving'
      WHEN a.billing_origin_product = 'SERVERLESS_REAL_TIME_INFERENCE' THEN 'Serverless Inference'
      ELSE a.billing_origin_product
    END AS usage_type_description,
    
    -- ========================================================================
    -- JOB DETAILS
    -- ========================================================================
    a.job_id,
    COALESCE(j.job_name, a.job_name_from_usage) AS job_name,
    a.job_run_id,
    j.creator_user_name AS job_creator,
    
    -- Trigger type determination
    CASE
      WHEN a.billing_origin_product = 'ALL_PURPOSE' THEN 'INTERACTIVE'
      WHEN a.billing_origin_product = 'SQL' THEN 'SQL_QUERY'
      WHEN a.billing_origin_product = 'DLT' THEN 
        CASE WHEN p.is_serverless_pipeline = TRUE THEN 'DLT_SERVERLESS' ELSE 'DLT_CLASSIC' END
      WHEN j.trigger_type IS NOT NULL THEN j.trigger_type
      WHEN j.cron_schedule IS NOT NULL THEN 'CRON'
      ELSE 'MANUAL_OR_API'
    END AS trigger_type,
    
    j.cron_schedule,
    j.schedule_timezone,
    j.is_paused AS job_is_paused,
    
    -- ========================================================================
    -- NOTEBOOK DETAILS
    -- ========================================================================
    a.notebook_path,
    
    -- ========================================================================
    -- CLUSTER DETAILS
    -- ========================================================================
    a.cluster_id,
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
    
    -- Total cluster capacity (estimated)
    CASE 
      WHEN c.worker_count IS NOT NULL THEN 
        CONCAT(c.worker_count, ' workers (fixed)')
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT(c.min_autoscale_workers, '-', c.max_autoscale_workers, ' workers (autoscale)')
      ELSE 'Unknown'
    END AS cluster_worker_config,
    
    -- Total cores calculation
    COALESCE(driver_specs.core_count, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS max_total_cores,
    
    -- ========================================================================
    -- INSTANCE POOL DETAILS
    -- ========================================================================
    a.instance_pool_id,
    CASE 
      WHEN a.instance_pool_id IS NOT NULL THEN 'Yes'
      ELSE 'No'
    END AS uses_instance_pool,
    
    -- ========================================================================
    -- SQL WAREHOUSE DETAILS
    -- ========================================================================
    a.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    CONCAT(wh.warehouse_min_clusters, '-', wh.warehouse_max_clusters) AS warehouse_cluster_range,
    
    -- ========================================================================
    -- DLT PIPELINE DETAILS
    -- ========================================================================
    a.dlt_pipeline_id,
    a.dlt_update_id,
    p.pipeline_name,
    p.pipeline_type,
    p.pipeline_creator,
    
    -- ========================================================================
    -- PRODUCT FEATURES
    -- ========================================================================
    a.is_photon,
    a.is_serverless,
    a.jobs_tier,
    a.sku_name,
    
    -- ========================================================================
    -- IDENTITY & COST ALLOCATION
    -- ========================================================================
    a.run_as,
    a.created_by,
    a.custom_tags,
    
    -- Extract common custom tags
    a.custom_tags['ClientName'] AS client_name,
    a.custom_tags['ServiceLine'] AS service_line,
    a.custom_tags['TeamName'] AS team_name,
    a.custom_tags['ENVIRONMENT'] AS environment,
    a.custom_tags['OWNER'] AS owner_tag,
    
    -- ========================================================================
    -- COST METRICS
    -- ========================================================================
    ROUND(a.total_dbu, 4) AS total_dbu,
    ROUND(a.total_list_cost, 2) AS total_list_cost_usd,
    ROUND(a.total_effective_cost, 2) AS total_effective_cost_usd,
    
    -- ========================================================================
    -- EXECUTION TIME METRICS
    -- ========================================================================
    a.execution_start_time,
    a.execution_end_time,
    a.total_usage_minutes AS billed_usage_minutes,
    a.execution_wall_time_minutes AS execution_duration_minutes,
    
    -- Format execution time for readability
    CASE 
      WHEN a.execution_wall_time_minutes >= 1440 THEN 
        CONCAT(FLOOR(a.execution_wall_time_minutes / 1440), 'd ', 
               FLOOR(MOD(a.execution_wall_time_minutes, 1440) / 60), 'h ',
               MOD(a.execution_wall_time_minutes, 60), 'm')
      WHEN a.execution_wall_time_minutes >= 60 THEN 
        CONCAT(FLOOR(a.execution_wall_time_minutes / 60), 'h ', 
               MOD(a.execution_wall_time_minutes, 60), 'm')
      ELSE 
        CONCAT(a.execution_wall_time_minutes, 'm')
    END AS execution_duration_formatted,
    
    -- ========================================================================
    -- METADATA
    -- ========================================================================
    a.usage_record_count

FROM aggregated_usage a

-- Join workspace info
LEFT JOIN system.access.workspaces_latest w
  ON a.workspace_id = w.workspace_id

-- Join job info
LEFT JOIN most_recent_jobs j
  ON a.workspace_id = j.workspace_id 
  AND a.job_id = CAST(j.job_id AS STRING)

-- Join cluster info
LEFT JOIN most_recent_clusters c
  ON a.workspace_id = c.workspace_id 
  AND a.cluster_id = c.cluster_id

-- Join driver node specs
LEFT JOIN node_specs driver_specs
  ON c.driver_node_type = driver_specs.node_type

-- Join worker node specs  
LEFT JOIN node_specs worker_specs
  ON c.worker_node_type = worker_specs.node_type

-- Join warehouse info
LEFT JOIN warehouse_info wh
  ON a.workspace_id = wh.workspace_id 
  AND a.warehouse_id = wh.warehouse_id

-- Join pipeline info
LEFT JOIN pipeline_info p
  ON a.workspace_id = p.workspace_id 
  AND a.dlt_pipeline_id = p.pipeline_id

ORDER BY 
  a.total_list_cost DESC,
  a.execution_start_time DESC;


-- ============================================================================
-- ALTERNATIVE: SUMMARY VIEW BY USAGE TYPE
-- ============================================================================
-- Uncomment below for a high-level summary instead of detailed records

/*
SELECT
    billing_origin_product AS usage_category,
    COUNT(DISTINCT COALESCE(job_run_id, cluster_id, warehouse_id, dlt_update_id)) AS execution_count,
    COUNT(DISTINCT job_id) AS unique_jobs,
    COUNT(DISTINCT cluster_id) AS unique_clusters,
    SUM(total_dbu) AS total_dbu,
    ROUND(SUM(total_list_cost), 2) AS total_cost_usd,
    SUM(execution_wall_time_minutes) AS total_execution_minutes,
    ROUND(SUM(execution_wall_time_minutes) / 60.0, 1) AS total_execution_hours
FROM (
    -- Use the main query above as subquery
)
GROUP BY billing_origin_product
ORDER BY total_cost_usd DESC;
*/
