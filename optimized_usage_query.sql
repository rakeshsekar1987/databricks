-- =====================================================================================
-- OPTIMIZED USAGE QUERY (FIXED)
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
    name,
    creator_user_name,
    run_as,
    job_type,
    tags
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
    name,
    pipeline_type,
    creator_user_name,
    run_as,
    serverless
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
    creator_user_name AS owner,
    spark_version AS dbr_version,
    driver_node_type_id AS driver_node_type,
    node_type_id AS worker_node_type,
    num_workers,
    autoscale_min_workers AS min_autoscale_workers,
    autoscale_max_workers AS max_autoscale_workers
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
    name AS warehouse_name,
    warehouse_type,
    cluster_size AS warehouse_size
  FROM system.compute.warehouses
  WHERE workspace_id = 5244115429641560
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY workspace_id, warehouse_id
    ORDER BY change_time DESC
  ) = 1
),

-- Node specs - small table, will be broadcast
node_specs AS (
  SELECT
    node_type_id AS node_type,
    num_cores AS core_count,
    memory_mb / 1024.0 AS memory_gb
  FROM system.compute.node_types
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
  LEFT JOIN system.access.workspaces_latest w
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

    -- Entity URL
    CASE 
      WHEN u.job_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/jobs/', u.job_id, '" target="_blank">', 
               COALESCE(j.name, u.job_name_from_usage, u.job_id), '</a>')
      WHEN u.dlt_pipeline_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/pipelines/', u.dlt_pipeline_id, '" target="_blank">', 
               COALESCE(p.name, u.dlt_pipeline_id), '</a>')
      WHEN u.warehouse_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/sql/warehouses/', u.warehouse_id, '" target="_blank">', 
               COALESCE(wh.warehouse_name, u.warehouse_id), '</a>')
      WHEN u.cluster_id IS NOT NULL THEN 
        CONCAT('<a href="', u.workspace_url, '/compute/clusters/', u.cluster_id, '" target="_blank">', 
               COALESCE(c.cluster_name, u.cluster_id), '</a>')
      ELSE NULL
    END AS entity_url,

    -- Cost metrics
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    ROUND(u.total_dbu, 4) AS total_dbu_consumed,
    
    -- Execution time
    ROUND((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 60.0, 2) AS execution_time_minutes,
    ROUND((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 3600.0, 2) AS execution_time_hours,
    
    -- Formatted execution time
    CASE 
      WHEN u.execution_start_time IS NULL THEN 'N/A'
      ELSE
        CONCAT(
          IF(FLOOR((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 86400) > 0,
            CONCAT(CAST(FLOOR((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)) / 86400) AS STRING), 'd '), ''),
          IF(FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 86400) / 3600) > 0,
            CONCAT(CAST(FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 86400) / 3600) AS STRING), 'h '), ''),
          CAST(FLOOR(MOD((UNIX_TIMESTAMP(u.execution_end_time) - UNIX_TIMESTAMP(u.execution_start_time)), 3600) / 60) AS STRING), 'm'
        )
    END AS execution_time_formatted,
    u.execution_start_time,
    u.execution_end_time,
    
    -- Executed from
    CASE 
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NOT NULL THEN 'Scheduled/Automated Job'
      WHEN u.billing_origin_product = 'JOBS' THEN 'Job Cluster (Ad-hoc)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NOT NULL THEN 'Personal Notebook (Interactive Cluster)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' THEN 'Interactive Cluster Session'
      WHEN u.billing_origin_product = 'SQL' THEN 'SQL Warehouse Query'
      WHEN u.billing_origin_product = 'DLT' THEN 'DLT Pipeline Run'
      WHEN u.billing_origin_product = 'LAKEFLOW_CONNECT' THEN 'Lakeflow Connect Pipeline'
      ELSE u.billing_origin_product
    END AS executed_from,
    
    u.notebook_path,
    COALESCE(j.name, u.job_name_from_usage, p.name) AS job_or_pipeline_name,
    u.job_id,
    u.job_run_id,
    u.dlt_pipeline_id,
    u.dlt_update_id,
    
    -- Cluster info
    c.cluster_name,
    u.cluster_id,
    c.cluster_source AS cluster_created_by,
    c.owner AS cluster_owner,
    c.dbr_version AS databricks_runtime,
    
    -- Trigger type (simplified without schedule/trigger columns)
    CASE
      WHEN u.billing_origin_product = 'ALL_PURPOSE' THEN 'Manual - Personal Interactive Cluster'
      WHEN u.billing_origin_product = 'SQL' THEN 'Manual - SQL Warehouse Query'
      WHEN u.billing_origin_product = 'DLT' THEN 
        IF(p.serverless, 'Automated - DLT Pipeline (Serverless)', 'Automated - DLT Pipeline')
      WHEN u.billing_origin_product = 'LAKEFLOW_CONNECT' THEN 'Automated - Lakeflow Connect'
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NOT NULL THEN 'Automated - Job Run'
      WHEN u.is_serverless AND u.job_id IS NOT NULL THEN 'Serverless Job Compute'
      ELSE 'Unknown'
    END AS how_was_it_triggered,
    
    -- Job type instead of schedule
    j.job_type,
    
    -- Node specs
    u.node_type AS node_type_used,
    ns.core_count AS node_cores,
    ns.memory_gb AS node_memory_gb,
    
    -- Cluster sizing
    c.driver_node_type,
    ds.core_count AS driver_cores,
    ds.memory_gb AS driver_memory_gb,
    c.worker_node_type,
    ws.core_count AS worker_cores,
    ws.memory_gb AS worker_memory_gb,
    c.num_workers AS fixed_worker_count,
    
    IF(c.min_autoscale_workers IS NOT NULL,
      CONCAT(CAST(c.min_autoscale_workers AS STRING), ' to ', CAST(c.max_autoscale_workers AS STRING)),
      NULL
    ) AS autoscale_worker_range,
    
    -- Cluster size summary
    CASE 
      WHEN u.is_serverless THEN 'Serverless (auto-scaled)'
      WHEN c.num_workers IS NOT NULL THEN 
        CONCAT('Fixed: ', CAST(c.num_workers AS STRING), ' workers | Driver: ', 
          COALESCE(c.driver_node_type, 'N/A'), ' | Workers: ', COALESCE(c.worker_node_type, 'N/A'))
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT('Autoscale: ', CAST(c.min_autoscale_workers AS STRING), '-', CAST(c.max_autoscale_workers AS STRING), 
          ' workers | Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' | Workers: ', COALESCE(c.worker_node_type, 'N/A'))
      ELSE 'Unknown Configuration'
    END AS cluster_size_details,
    
    -- Total capacity
    COALESCE(ds.core_count, 0) + 
      (COALESCE(c.num_workers, c.max_autoscale_workers, 0) * COALESCE(ws.core_count, 0)) AS total_max_cores,
    COALESCE(ds.memory_gb, 0) + 
      (COALESCE(c.num_workers, c.max_autoscale_workers, 0) * COALESCE(ws.memory_gb, 0)) AS total_max_memory_gb,
    
    -- Instance pool
    u.instance_pool_id,
    IF(u.instance_pool_id IS NOT NULL, 'Yes - Using Instance Pool', 'No - On-Demand/Serverless') AS uses_instance_pool,
    
    -- Warehouse info
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    IF(wh.warehouse_id IS NOT NULL,
      CONCAT('Type: ', COALESCE(wh.warehouse_type, 'N/A'), ' | Size: ', COALESCE(wh.warehouse_size, 'N/A')),
      NULL
    ) AS warehouse_details,
    
    -- Pipeline info
    p.name AS pipeline_name,
    p.pipeline_type,
    p.creator_user_name AS pipeline_creator,
    
    -- Compute type
    u.entity_type,
    CASE 
      WHEN u.is_serverless THEN 'Serverless'
      WHEN u.instance_pool_id IS NOT NULL THEN 'Pool-based'
      WHEN u.warehouse_id IS NOT NULL THEN 'SQL Warehouse'
      ELSE 'On-Demand Cluster'
    END AS compute_type,
    
    -- Identity & tags
    u.run_as,
    j.creator_user_name AS job_creator,
    u.custom_tags,
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['OWNER'] AS owner_tag

FROM usage_agg u

-- Dimension joins with workspace scoping
LEFT JOIN most_recent_jobs j
  ON u.entity_type LIKE '%JOB%'
  AND u.workspace_id = j.workspace_id
  AND u.job_id = CAST(j.job_id AS STRING)

LEFT JOIN most_recent_pipelines p
  ON u.entity_type LIKE '%PIPELINE%'
  AND u.workspace_id = p.workspace_id
  AND u.dlt_pipeline_id = p.pipeline_id

LEFT JOIN most_recent_clusters c
  ON u.cluster_id IS NOT NULL
  AND u.workspace_id = c.workspace_id
  AND u.cluster_id = c.cluster_id

LEFT JOIN warehouse_info wh
  ON u.warehouse_id IS NOT NULL
  AND u.workspace_id = wh.workspace_id
  AND u.warehouse_id = wh.warehouse_id

-- Node specs joins (small tables - will be broadcast)
LEFT JOIN node_specs ns ON u.node_type = ns.node_type
LEFT JOIN node_specs ds ON c.driver_node_type = ds.node_type
LEFT JOIN node_specs ws ON c.worker_node_type = ws.node_type

ORDER BY u.total_list_cost DESC, u.execution_start_time DESC
LIMIT 100000;
