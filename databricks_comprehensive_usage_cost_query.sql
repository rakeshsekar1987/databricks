-- ============================================================================
-- COMPREHENSIVE DATABRICKS USAGE & COST ANALYSIS QUERY (v5 - Fixed Issues)
-- ============================================================================
-- 
-- FIXES IN V5:
--   - notebook_path: Added note that billing doesn't capture notebook for jobs
--   - cron_schedule: Added job_found flag to debug join issues
--   - how_was_it_triggered: Fixed logic to handle missing job metadata
--   - warehouse: Clarified that warehouse columns only apply to SQL usage
--
-- BUSINESS GOALS ADDRESSED:
--   1. Job run cost → total_list_cost_usd
--   2. Execution time → execution_time_minutes/formatted
--   3. Execution source → executed_from
--   4. Cluster used → cluster_name, cluster_id
--   5. Trigger type → how_was_it_triggered
--   6. Node/Warehouse/Cluster details → detailed columns
--
-- Filters:
--   - Date: 2025-01-01 to 2025-12-31
--   - Workspace: 5244115429641560
-- ============================================================================

WITH 
-- ============================================================================
-- CTE 1: FILTERED USAGE WITH COST
-- ============================================================================
usage_with_cost AS (
  SELECT
    u.workspace_id,
    u.record_id,
    u.billing_origin_product,
    u.sku_name,
    u.usage_metadata.job_id AS job_id,
    u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.job_name AS job_name_from_usage,
    u.usage_metadata.cluster_id AS cluster_id,
    u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    u.usage_metadata.dlt_update_id AS dlt_update_id,
    u.usage_metadata.instance_pool_id AS instance_pool_id,
    u.usage_metadata.node_type AS node_type,
    -- NOTE: notebook_path is ONLY populated for ALL_PURPOSE (interactive) usage
    -- For JOBS, the notebook info is in job task config, NOT in billing metadata
    u.usage_metadata.notebook_path AS notebook_path,
    u.identity_metadata.run_as AS run_as,
    u.custom_tags,
    u.product_features.is_serverless AS is_serverless,
    u.usage_start_time,
    u.usage_end_time,
    u.usage_quantity,
    u.usage_quantity * CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_cost
  FROM system.billing.usage u
  INNER JOIN system.billing.list_prices lp 
    ON u.cloud = lp.cloud 
    AND u.sku_name = lp.sku_name 
    AND u.usage_start_time >= lp.price_start_time 
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
  WHERE 
    u.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND u.workspace_id = 5244115429641560
    AND u.billing_origin_product IN ('JOBS', 'ALL_PURPOSE', 'SQL', 'DLT')
),

-- ============================================================================
-- CTE 2: WORKSPACE INFO
-- ============================================================================
workspace_info AS (
  SELECT workspace_id, workspace_name, workspace_url
  FROM system.access.workspaces_latest
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 3: ALL JOBS (Not filtered by workspace to catch cross-workspace refs)
-- Convert job_id to STRING for easier joining
-- ============================================================================
most_recent_jobs AS (
  SELECT
    workspace_id AS job_workspace_id,
    CAST(job_id AS STRING) AS job_id_str,  -- Convert to STRING for join
    job_id AS job_id_original,
    name AS job_name,
    creator_user_name,
    run_as_user_name,
    trigger_type,
    trigger.schedule.quartz_cron_expression AS cron_schedule,
    trigger.schedule.timezone_id AS schedule_timezone,
    -- Check if job has any schedule configuration
    CASE 
      WHEN trigger.schedule.quartz_cron_expression IS NOT NULL THEN TRUE
      WHEN trigger_type = 'CRON' THEN TRUE
      WHEN trigger_type = 'CONTINUOUS' THEN TRUE
      WHEN trigger_type = 'FILE_ARRIVAL' THEN TRUE
      ELSE FALSE
    END AS has_schedule,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.jobs
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 4: CLUSTERS
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
-- CTE 5: NODE SPECS
-- ============================================================================
node_specs AS (
  SELECT DISTINCT
    node_type,
    core_count,
    memory_mb,
    ROUND(memory_mb / 1024.0, 1) AS memory_gb
  FROM system.compute.node_types
),

-- ============================================================================
-- CTE 6: SQL WAREHOUSES
-- ============================================================================
warehouse_info AS (
  SELECT
    workspace_id,
    warehouse_id,
    warehouse_name,
    warehouse_type,
    warehouse_size
  FROM system.compute.warehouses
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 7: DLT PIPELINES
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
    sku_name,
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
usage_final AS (
  SELECT
    a.*,
    ROUND((UNIX_TIMESTAMP(a.execution_end_time) - UNIX_TIMESTAMP(a.execution_start_time)) / 60.0, 2) AS execution_time_minutes
  FROM aggregated_usage a
)

-- ============================================================================
-- FINAL SELECT
-- ============================================================================
SELECT
    -- =========================================================================
    -- GOAL 1: JOB RUN COST
    -- =========================================================================
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    ROUND(u.total_dbu, 4) AS total_dbu_consumed,
    
    -- =========================================================================
    -- GOAL 2: TOTAL EXECUTION TIME
    -- =========================================================================
    u.execution_time_minutes,
    ROUND(u.execution_time_minutes / 60.0, 2) AS execution_time_hours,
    CASE 
      WHEN u.execution_time_minutes IS NULL THEN 'N/A'
      WHEN u.execution_time_minutes >= 1440 THEN 
        CONCAT(FLOOR(u.execution_time_minutes / 1440), 'd ', 
               FLOOR(MOD(u.execution_time_minutes, 1440) / 60), 'h ', 
               CAST(MOD(u.execution_time_minutes, 60) AS INT), 'm')
      WHEN u.execution_time_minutes >= 60 THEN 
        CONCAT(FLOOR(u.execution_time_minutes / 60), 'h ', 
               CAST(MOD(u.execution_time_minutes, 60) AS INT), 'm')
      ELSE CONCAT(ROUND(u.execution_time_minutes, 1), 'm')
    END AS execution_time_formatted,
    u.execution_start_time,
    u.execution_end_time,
    
    -- =========================================================================
    -- GOAL 3: WHERE WAS IT EXECUTED FROM
    -- =========================================================================
    CASE 
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NOT NULL 
        THEN 'Scheduled/Automated Job'
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NULL 
        THEN 'Job Cluster (Ad-hoc)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NOT NULL 
        THEN 'Personal Notebook (Interactive Cluster)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NULL 
        THEN 'Interactive Cluster Session'
      WHEN u.billing_origin_product = 'SQL' 
        THEN 'SQL Warehouse Query'
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'DLT Pipeline Run'
      ELSE u.billing_origin_product
    END AS executed_from,
    
    -- Notebook path (NOTE: Only available for ALL_PURPOSE/interactive usage)
    -- For JOBS, notebook info is in job task configuration, not billing metadata
    u.notebook_path,
    CASE 
      WHEN u.billing_origin_product = 'JOBS' AND u.notebook_path IS NULL 
        THEN 'Notebook path not available in billing data for jobs - check job task configuration'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NULL 
        THEN 'No notebook - cluster session only'
      WHEN u.notebook_path IS NOT NULL 
        THEN u.notebook_path
      ELSE 'N/A'
    END AS notebook_path_info,
    
    -- Job/Pipeline Name & ID
    COALESCE(j.job_name, u.job_name_from_usage, p.pipeline_name) AS job_or_pipeline_name,
    u.job_id,
    u.job_run_id,
    u.dlt_pipeline_id,
    u.dlt_update_id,
    
    -- =========================================================================
    -- GOAL 4: WHICH CLUSTER WAS USED
    -- =========================================================================
    c.cluster_name,
    u.cluster_id,
    c.cluster_source AS cluster_created_by,
    c.cluster_owner,
    c.dbr_version AS databricks_runtime,
    
    -- =========================================================================
    -- GOAL 5: HOW WAS IT TRIGGERED (FIXED LOGIC)
    -- =========================================================================
    CASE
      -- Interactive cluster usage (personal notebook/session)
      WHEN u.billing_origin_product = 'ALL_PURPOSE' 
        THEN 'Manual - Personal Interactive Cluster'
      
      -- SQL Warehouse queries (always manual/ad-hoc)
      WHEN u.billing_origin_product = 'SQL' 
        THEN 'Manual - SQL Warehouse Query'
      
      -- DLT Pipelines (usually automated)
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'Automated - DLT Pipeline'
      
      -- JOBS: Check if we found the job in lakeflow.jobs
      -- If job found and has cron schedule
      WHEN u.billing_origin_product = 'JOBS' AND j.cron_schedule IS NOT NULL 
        THEN 'Automated - Cron Scheduled Job'
      
      -- If job found and trigger_type indicates schedule
      WHEN u.billing_origin_product = 'JOBS' AND j.trigger_type = 'CRON' 
        THEN 'Automated - Cron Scheduled Job'
      WHEN u.billing_origin_product = 'JOBS' AND j.trigger_type = 'CONTINUOUS' 
        THEN 'Automated - Continuous Job'
      WHEN u.billing_origin_product = 'JOBS' AND j.trigger_type = 'FILE_ARRIVAL' 
        THEN 'Automated - File Arrival Trigger'
      WHEN u.billing_origin_product = 'JOBS' AND j.trigger_type IS NOT NULL 
        THEN CONCAT('Automated - ', j.trigger_type)
      
      -- If job found but no schedule (manual/API triggered)
      WHEN u.billing_origin_product = 'JOBS' AND j.job_id_str IS NOT NULL AND j.has_schedule = FALSE
        THEN 'Manual - Job Run (API/UI Triggered)'
      
      -- If job NOT found in lakeflow.jobs (deleted job or data issue)
      WHEN u.billing_origin_product = 'JOBS' AND j.job_id_str IS NULL 
        THEN 'Unknown - Job Not Found in Catalog (may be deleted)'
      
      ELSE 'Unknown'
    END AS how_was_it_triggered,
    
    -- Cron schedule details (will be NULL if job not found or no schedule)
    j.cron_schedule,
    j.schedule_timezone,
    
    -- Debug: Was the job found in lakeflow.jobs?
    CASE 
      WHEN u.billing_origin_product != 'JOBS' THEN 'N/A - Not a Job'
      WHEN j.job_id_str IS NOT NULL THEN 'Yes - Job Found'
      ELSE 'No - Job Not Found in system.lakeflow.jobs'
    END AS job_metadata_found,
    
    -- =========================================================================
    -- GOAL 6: NODE, WAREHOUSE, AND CLUSTER SIZE DETAILS
    -- =========================================================================
    
    -- Node Details (from usage_metadata)
    u.node_type AS node_type_used,
    node_specs.core_count AS node_cores,
    node_specs.memory_gb AS node_memory_gb,
    
    -- Cluster Size Details
    c.driver_node_type,
    driver_specs.core_count AS driver_cores,
    driver_specs.memory_gb AS driver_memory_gb,
    c.worker_node_type,
    worker_specs.core_count AS worker_cores,
    worker_specs.memory_gb AS worker_memory_gb,
    c.worker_count AS fixed_worker_count,
    CASE 
      WHEN c.min_autoscale_workers IS NOT NULL 
        THEN CONCAT(c.min_autoscale_workers, ' to ', c.max_autoscale_workers)
      ELSE NULL
    END AS autoscale_worker_range,
    
    -- Full cluster description
    CASE 
      WHEN u.is_serverless = 'true' THEN 'Serverless (auto-scaled by Databricks)'
      WHEN c.cluster_id IS NULL THEN 'Cluster details not found'
      WHEN c.worker_count IS NOT NULL THEN 
        CONCAT(
          'Fixed: ', c.worker_count, ' workers | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' (', COALESCE(driver_specs.core_count, 0), ' cores, ', COALESCE(driver_specs.memory_gb, 0), ' GB) | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A'), ' (', COALESCE(worker_specs.core_count, 0), ' cores, ', COALESCE(worker_specs.memory_gb, 0), ' GB each)'
        )
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT(
          'Autoscale: ', c.min_autoscale_workers, '-', c.max_autoscale_workers, ' workers | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' (', COALESCE(driver_specs.core_count, 0), ' cores, ', COALESCE(driver_specs.memory_gb, 0), ' GB) | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A'), ' (', COALESCE(worker_specs.core_count, 0), ' cores, ', COALESCE(worker_specs.memory_gb, 0), ' GB each)'
        )
      ELSE 'Unknown Configuration'
    END AS cluster_size_details,
    
    -- Total capacity
    COALESCE(driver_specs.core_count, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS total_max_cores,
    
    COALESCE(driver_specs.memory_gb, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.memory_gb, 0)) 
      AS total_max_memory_gb,
    
    -- Instance Pool
    u.instance_pool_id,
    CASE 
      WHEN u.instance_pool_id IS NOT NULL THEN 'Yes - Using Instance Pool'
      ELSE 'No - On-Demand or Serverless'
    END AS uses_instance_pool,
    
    -- =========================================================================
    -- SQL WAREHOUSE DETAILS (Only populated for SQL usage)
    -- For JOBS/ALL_PURPOSE/DLT these will be NULL - this is expected!
    -- =========================================================================
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    CASE 
      WHEN u.billing_origin_product != 'SQL' 
        THEN 'N/A - Not SQL Warehouse Usage'
      WHEN u.warehouse_id IS NULL 
        THEN 'Warehouse ID not captured in billing'
      WHEN wh.warehouse_id IS NULL 
        THEN 'Warehouse not found in system.compute.warehouses'
      ELSE CONCAT('Type: ', COALESCE(wh.warehouse_type, 'N/A'), ' | Size: ', COALESCE(wh.warehouse_size, 'N/A'))
    END AS warehouse_details,
    
    -- DLT Pipeline Details
    p.pipeline_name,
    p.pipeline_type,
    p.pipeline_creator,
    
    -- =========================================================================
    -- ENTITY URL
    -- =========================================================================
    CASE 
      WHEN u.job_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/jobs/', u.job_id, '" target="_blank">', 
               COALESCE(j.job_name, u.job_name_from_usage, u.job_id), '</a>')
      WHEN u.dlt_pipeline_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/pipelines/', u.dlt_pipeline_id, '" target="_blank">', 
               COALESCE(p.pipeline_name, u.dlt_pipeline_id), '</a>')
      WHEN u.warehouse_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/sql/warehouses/', u.warehouse_id, '" target="_blank">', 
               COALESCE(wh.warehouse_name, u.warehouse_id), '</a>')
      WHEN u.cluster_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/compute/clusters/', u.cluster_id, '" target="_blank">', 
               COALESCE(c.cluster_name, u.cluster_id), '</a>')
      ELSE NULL
    END AS entity_url,
    
    -- Compute Type
    CASE 
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      WHEN u.instance_pool_id IS NOT NULL THEN 'Pool-based'
      WHEN u.warehouse_id IS NOT NULL THEN 'SQL Warehouse'
      ELSE 'On-Demand Cluster'
    END AS compute_type,
    
    -- Identity & Tags
    u.run_as,
    j.creator_user_name AS job_creator,
    u.custom_tags,
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['OWNER'] AS owner_tag,
    
    -- Workspace
    u.workspace_id,
    w.workspace_name,
    
    -- SKU
    u.sku_name,
    u.billing_origin_product

FROM usage_final u

-- Joins
LEFT JOIN workspace_info w 
  ON u.workspace_id = w.workspace_id

-- Jobs join: Use STRING comparison (job_id in usage is STRING)
LEFT JOIN most_recent_jobs j
  ON u.job_id IS NOT NULL
  AND u.job_id = j.job_id_str

LEFT JOIN most_recent_clusters c 
  ON u.cluster_id IS NOT NULL
  AND u.cluster_id = c.cluster_id

LEFT JOIN node_specs 
  ON u.node_type = node_specs.node_type

LEFT JOIN node_specs driver_specs 
  ON c.driver_node_type = driver_specs.node_type

LEFT JOIN node_specs worker_specs 
  ON c.worker_node_type = worker_specs.node_type

-- Warehouse join: Only for SQL usage
LEFT JOIN warehouse_info wh
  ON u.billing_origin_product = 'SQL'
  AND u.warehouse_id IS NOT NULL
  AND u.warehouse_id = wh.warehouse_id

LEFT JOIN most_recent_pipelines p
  ON u.dlt_pipeline_id IS NOT NULL
  AND u.dlt_pipeline_id = p.pipeline_id

ORDER BY 
  u.total_list_cost DESC, 
  u.execution_start_time DESC;
