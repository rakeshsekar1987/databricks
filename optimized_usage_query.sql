-- =====================================================================================
-- OPTIMIZED USAGE QUERY
-- Using column names from original query
-- Filter Parameters:
--   Start Date: 2025-01-01
--   End Date: 2026-01-28
--   Workspace ID: 5244115429641560
-- =====================================================================================

-- =====================================================================================
-- DIMENSION TABLES: Pre-filter and deduplicate once
-- =====================================================================================
WITH most_recent_jobs AS (
  SELECT
    workspace_id,
    job_id,
    job_name,
    creator_user_name,
    run_as,
    cron_schedule,
    schedule_timezone,
    trigger_type
  FROM system.lakeflow.jobs
  WHERE workspace_id = 5244115429641560
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY workspace_id, job_id
    ORDER BY change_time DESC
  ) = 1
),

most_recent_pipelines AS (
  SELECT
    workspace_id,
    pipeline_id,
    pipeline_name,
    pipeline_type,
    pipeline_creator,
    run_as,
    is_serverless_pipeline
  FROM system.lakeflow.pipelines
  WHERE workspace_id = 5244115429641560
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY workspace_id, pipeline_id
    ORDER BY change_time DESC
  ) = 1
),

most_recent_clusters AS (
  SELECT
    workspace_id,
    cluster_id,
    cluster_name,
    cluster_source,
    cluster_owner,
    dbr_version,
    driver_node_type,
    worker_node_type,
    worker_count,
    min_autoscale_workers,
    max_autoscale_workers
  FROM system.compute.clusters
  WHERE workspace_id = 5244115429641560
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY workspace_id, cluster_id
    ORDER BY change_time DESC
  ) = 1
),

warehouse_info AS (
  SELECT
    workspace_id,
    warehouse_id,
    warehouse_name,
    warehouse_type,
    warehouse_size
  FROM system.compute.warehouses
  WHERE workspace_id = 5244115429641560
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY workspace_id, warehouse_id
    ORDER BY change_time DESC
  ) = 1
),

-- Node specs
node_specs AS (
  SELECT
    node_type,
    core_count,
    memory_gb
  FROM system.compute.node_types
),

-- Workspace info
workspace_info AS (
  SELECT
    workspace_id,
    workspace_name,
    workspace_url
  FROM system.compute.workspaces
  WHERE workspace_id = 5244115429641560
),

-- =====================================================================================
-- USAGE DATA: Filter early with specific workspace and date range
-- =====================================================================================
usage_base AS (
  SELECT
    -- Keys
    u.workspace_id,
    u.sku_name,
    u.billing_origin_product,
    u.cloud,
    
    -- Metadata fields (extracted once)
    u.usage_metadata.job_id AS job_id,
    u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.job_name AS job_name_from_usage,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    u.usage_metadata.dlt_update_id AS dlt_update_id,
    u.usage_metadata.cluster_id AS cluster_id,
    u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.instance_pool_id AS instance_pool_id,
    u.usage_metadata.node_type AS node_type,
    u.usage_metadata.notebook_path AS notebook_path,
    
    -- Identity
    u.identity_metadata.run_as AS run_as,
    
    -- Serverless flag
    u.product_features.is_serverless AS is_serverless,
    
    -- Entity type (computed once)
    CONCAT_WS(' ',
      IF(u.product_features.is_serverless, 'SERVERLESS', ''),
      IF(u.billing_origin_product = 'JOBS', 'JOB', 'PIPELINE')
    ) AS entity_type,
    
    -- Metrics
    u.usage_quantity,
    u.usage_start_time,
    u.usage_end_time,
    
    -- Tags
    u.custom_tags,
    
    -- Workspace info
    w.workspace_name,
    w.workspace_url
    
  FROM system.billing.usage u
  LEFT JOIN workspace_info w
    ON u.workspace_id = w.workspace_id
  WHERE
    -- Workspace filter (specific workspace)
    u.workspace_id = 5244115429641560
    -- Product filter (include all relevant products)
    AND (
      u.billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
      OR (u.billing_origin_product = 'SQL' AND u.usage_metadata.dlt_pipeline_id IS NOT NULL)
    )
    -- Date filter - CRITICAL for partition pruning
    AND u.usage_date BETWEEN '2025-01-01' AND '2026-01-28'
),

-- =====================================================================================
-- COST CALCULATION: Join with prices
-- =====================================================================================
usage_with_costs AS (
  SELECT
    u.*,
    u.usage_quantity * lp.pricing.default AS list_cost
  FROM usage_base u
  INNER JOIN system.billing.list_prices lp
    ON u.cloud = lp.cloud
    AND u.sku_name = lp.sku_name
    AND u.usage_start_time >= lp.price_start_time
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
),

-- =====================================================================================
-- AGGREGATION: Group by all dimension keys
-- =====================================================================================
usage_agg AS (
  SELECT
    -- Dimensions
    workspace_id,
    workspace_name,
    workspace_url,
    sku_name,
    billing_origin_product,
    entity_type,
    job_id,
    job_run_id,
    job_name_from_usage,
    dlt_pipeline_id,
    dlt_update_id,
    cluster_id,
    warehouse_id,
    instance_pool_id,
    node_type,
    notebook_path,
    run_as,
    is_serverless,
    
    -- Aggregated metrics
    SUM(list_cost) AS total_list_cost,
    SUM(usage_quantity) AS total_dbu,
    MIN(usage_start_time) AS execution_start_time,
    MAX(usage_end_time) AS execution_end_time,
    
    -- First non-null tags
    FIRST(custom_tags, TRUE) AS custom_tags
    
  FROM usage_with_costs
  GROUP BY ALL
)

-- =====================================================================================
-- FINAL SELECT: Join dimensions and compute derived columns
-- =====================================================================================
SELECT
    -- Workspace
    u.workspace_id,
    u.workspace_name,
    u.sku_name,

    -- Entity URL (clickable link for dashboards)
    CASE 
      WHEN u.job_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/jobs/', u.job_id, '" target="_blank">', 
               COALESCE(j.job_name, u.job_name_from_usage, u.job_id), '</a>')
      WHEN u.dlt_pipeline_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/pipelines/', u.dlt_pipeline_id, '" target="_blank">', 
               COALESCE(p.pipeline_name, u.dlt_pipeline_id), '</a>')
      WHEN u.warehouse_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/sql/warehouses/', u.warehouse_id, '" target="_blank">', 
               COALESCE(wh.warehouse_name, u.warehouse_id), '</a>')
      WHEN u.cluster_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/compute/clusters/', u.cluster_id, '" target="_blank">', 
               COALESCE(c.cluster_name, u.cluster_id), '</a>')
      ELSE NULL
    END AS entity_url,

    -- =========================================================================
    -- GOAL 1: JOB RUN COST (Cost of single job run)
    -- =========================================================================
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    ROUND(u.total_dbu, 4) AS total_dbu_consumed,
    
    -- =========================================================================
    -- GOAL 2: TOTAL EXECUTION TIME
    -- =========================================================================
    ROUND((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 60.0, 2) AS execution_time_minutes,
    ROUND((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 3600.0, 2) AS execution_time_hours,
    CASE 
      WHEN u.execution_start_time IS NULL THEN 'N/A'
      WHEN (UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 60.0 >= 1440 THEN 
        CONCAT(FLOOR((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 86400), 'd ', 
               FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 86400) / 3600), 'h ', 
               CAST(FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 3600) / 60) AS INT), 'm')
      WHEN (UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 60.0 >= 60 THEN 
        CONCAT(FLOOR((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 3600), 'h ', 
               CAST(FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 3600) / 60) AS INT), 'm')
      ELSE CONCAT(ROUND((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 60.0, 1), 'm')
    END AS execution_time_formatted,
    u.execution_start_time,
    u.execution_end_time,
    
    -- =========================================================================
    -- GOAL 3: WHERE WAS IT EXECUTED FROM (Job/Pipeline/Personal Notebook/SQL)
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
      WHEN u.billing_origin_product = 'LAKEFLOW_CONNECT'
        THEN 'Lakeflow Connect Pipeline'
      ELSE u.billing_origin_product
    END AS executed_from,
    
    u.notebook_path,
    
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
    -- GOAL 5: HOW WAS IT TRIGGERED (Cron/Manual/Interactive/SQL)
    -- =========================================================================
    CASE
      -- Interactive cluster usage (personal notebook)
      WHEN u.billing_origin_product = 'ALL_PURPOSE' 
        THEN 'Manual - Personal Interactive Cluster'
      
      -- SQL Warehouse queries
      WHEN u.billing_origin_product = 'SQL' 
        THEN 'Manual - SQL Warehouse Query'
      
      -- DLT Pipelines
      WHEN u.billing_origin_product = 'DLT' AND p.is_serverless_pipeline = TRUE 
        THEN 'Automated - DLT Pipeline (Serverless)'
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'Automated - DLT Pipeline'
      
      -- Lakeflow Connect
      WHEN u.billing_origin_product = 'LAKEFLOW_CONNECT'
        THEN 'Automated - Lakeflow Connect'
      
      -- Jobs with cron schedule
      WHEN j.cron_schedule IS NOT NULL 
        THEN 'Automated - Cron Scheduled Job'
      WHEN j.trigger_type = 'CRON' 
        THEN 'Automated - Cron Scheduled Job'
      
      -- Jobs with other trigger types
      WHEN j.trigger_type = 'CONTINUOUS' 
        THEN 'Automated - Continuous Job'
      WHEN j.trigger_type = 'FILE_ARRIVAL' 
        THEN 'Automated - File Arrival Trigger'
      WHEN j.trigger_type IS NOT NULL 
        THEN CONCAT('Automated - ', j.trigger_type)
      
      -- Jobs without schedule (manual or API triggered)
      WHEN u.job_id IS NOT NULL AND j.cron_schedule IS NULL 
        THEN 'Manual - Job Run (API/UI Triggered)'
      
      -- Serverless job compute
      WHEN u.is_serverless = TRUE AND u.job_id IS NOT NULL 
        THEN 'Manual - Serverless Job Compute'
      
      ELSE 'Unknown'
    END AS how_was_it_triggered,
    
    j.cron_schedule,
    j.schedule_timezone,
    
    -- =========================================================================
    -- GOAL 6: NODE, WAREHOUSE, AND CLUSTER SIZE DETAILS
    -- =========================================================================
    
    -- Node Details
    u.node_type AS node_type_used,
    node_specs.core_count AS node_cores,
    node_specs.memory_gb AS node_memory_gb,
    
    -- Cluster Size Details (for classic compute)
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
    
    -- Total Cluster Capacity
    CASE 
      WHEN u.is_serverless = TRUE THEN 'Serverless (auto-scaled)'
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
    
    COALESCE(driver_specs.core_count, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS total_max_cores,
    
    COALESCE(driver_specs.memory_gb, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.memory_gb, 0)) 
      AS total_max_memory_gb,
    
    -- Instance Pool Details
    u.instance_pool_id,
    CASE 
      WHEN u.instance_pool_id IS NOT NULL THEN 'Yes - Using Instance Pool'
      ELSE 'No - On-Demand/Serverless'
    END AS uses_instance_pool,
    
    -- SQL Warehouse Details
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    CASE 
      WHEN wh.warehouse_id IS NOT NULL THEN
        CONCAT(
          'Type: ', COALESCE(wh.warehouse_type, 'N/A'), ' | ',
          'Size: ', COALESCE(wh.warehouse_size, 'N/A')
        )
      ELSE NULL
    END AS warehouse_details,
    
    -- DLT Pipeline Details
    p.pipeline_name,
    p.pipeline_type,
    p.pipeline_creator,
    
    -- =========================================================================
    -- ADDITIONAL CONTEXT
    -- =========================================================================
    
    -- Entity Type
    u.entity_type,
    
    -- Compute Type
    CASE 
      WHEN u.is_serverless = TRUE THEN 'Serverless'
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
    u.custom_tags['OWNER'] AS owner_tag

FROM usage_agg u

-- =====================================================================================
-- JOINS: Using workspace_id for proper scoping
-- =====================================================================================

-- Join to Jobs (with workspace scoping)
LEFT JOIN most_recent_jobs j
  ON u.entity_type LIKE '%JOB%'
  AND u.workspace_id = j.workspace_id
  AND u.job_id = CAST(j.job_id AS STRING)

-- Join to Pipelines (with workspace scoping)
LEFT JOIN most_recent_pipelines p
  ON u.entity_type LIKE '%PIPELINE%'
  AND u.workspace_id = p.workspace_id
  AND u.dlt_pipeline_id = p.pipeline_id

-- Join to Clusters (with workspace scoping)
LEFT JOIN most_recent_clusters c 
  ON u.cluster_id IS NOT NULL
  AND u.workspace_id = c.workspace_id
  AND u.cluster_id = c.cluster_id

-- Join to Node Specs for usage node type
LEFT JOIN node_specs 
  ON u.node_type = node_specs.node_type

-- Join to Node Specs for driver
LEFT JOIN node_specs driver_specs 
  ON c.driver_node_type = driver_specs.node_type

-- Join to Node Specs for workers
LEFT JOIN node_specs worker_specs 
  ON c.worker_node_type = worker_specs.node_type

-- Join to Warehouses (with workspace scoping)
LEFT JOIN warehouse_info wh
  ON u.warehouse_id IS NOT NULL
  AND u.workspace_id = wh.workspace_id
  AND u.warehouse_id = wh.warehouse_id

ORDER BY 
  u.total_list_cost DESC, 
  u.execution_start_time DESC
LIMIT 100000;
