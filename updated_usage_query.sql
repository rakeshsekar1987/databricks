-- =====================================================================================
-- UPDATED USAGE QUERY
-- Built using reference query logic while preserving all original columns
-- =====================================================================================

-- =====================================================================================
-- STEP 1: Tag Entry Parsing (from reference query)
-- =====================================================================================
WITH tag_entry_parsing AS (
  SELECT
    explode(
      split(
        IF(
          trim(:param_single_tag_key) = '<USE TAG FILTER>',
          :param_tag_entries,
          :param_single_tag_key
        ),
        ';'
      )
    ) AS tag_entry,
    contains(tag_entry, '=') AS is_filter,
    IF(is_filter, split(tag_entry, '=')[0], tag_entry) AS tag_key
),

-- Parse tag entries
tag_entry_parsed AS (
  SELECT
    array_sort(collect_list(tag_key)) AS all_keys,
    array_sort(collect_list(IF(is_filter, tag_key, NULL))) AS filter_keys,
    array_sort(collect_list(IF(is_filter, tag_entry, NULL))) AS filter_expected
  FROM tag_entry_parsing
),

-- =====================================================================================
-- STEP 2: Base Usage with Restrictions (from reference query)
-- Includes: JOBS, DLT, LAKEFLOW_CONNECT, and SQL with DLT pipelines
-- =====================================================================================
usage_with_restrictions AS (
  SELECT
    t1.*,
    t2.workspace_name,
    t2.workspace_url,
    CONCAT_WS(
      ' ',
      CASE WHEN t1.product_features.is_serverless THEN 'SERVERLESS' ELSE '' END,
      CASE WHEN t1.billing_origin_product = 'JOBS' THEN 'JOB' ELSE 'PIPELINE' END
    ) AS entity_type,
    -- Extract commonly used fields for easier access
    t1.usage_metadata.job_id AS job_id,
    t1.usage_metadata.job_run_id AS job_run_id,
    t1.usage_metadata.job_name AS job_name_from_usage,
    t1.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    t1.usage_metadata.dlt_update_id AS dlt_update_id,
    t1.usage_metadata.cluster_id AS cluster_id,
    t1.usage_metadata.warehouse_id AS warehouse_id,
    t1.usage_metadata.instance_pool_id AS instance_pool_id,
    t1.usage_metadata.node_type AS node_type,
    t1.usage_metadata.notebook_path AS notebook_path,
    t1.identity_metadata.run_as AS run_as,
    CAST(t1.product_features.is_serverless AS STRING) AS is_serverless
  FROM system.billing.usage t1
  LEFT JOIN system.access.workspaces_latest t2 
    ON t1.workspace_id = t2.workspace_id
  WHERE
    -- Include all relevant billing products (from reference query)
    (
      t1.billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
      OR (
        t1.billing_origin_product = 'SQL'
        AND t1.usage_metadata.dlt_pipeline_id IS NOT NULL
      )
    )
    -- Date filter
    AND t1.usage_date BETWEEN :param_start_date AND :param_end_date
    -- Optional workspace filter
    AND IF(
      :param_workspace = '<ALL WORKSPACES>',
      TRUE,
      t2.workspace_name = :param_workspace
    )
    -- Optional run_as filter
    AND IF(
      :param_run_as = '<ALL USERS>',
      TRUE,
      t1.identity_metadata.run_as = :param_run_as
    )
    -- Optional cluster type filter
    AND IF(
      :param_cluster_type = '<ALL CLUSTER TYPES>',
      TRUE,
      IF(
        :param_cluster_type = 'Serverless',
        t1.product_features.is_serverless = TRUE,
        t1.product_features.is_serverless = FALSE
      )
    )
),

-- Filter by object type (Jobs vs Pipelines)
usage_filtered_by_type AS (
  SELECT *
  FROM usage_with_restrictions
  WHERE IF(
    :param_object_type = '<ALL>',
    TRUE,
    IF(
      :param_object_type = 'Jobs',
      entity_type RLIKE 'JOB',
      entity_type RLIKE 'PIPELINE'
    )
  )
),

-- =====================================================================================
-- STEP 3: Apply Tag Filtering (from reference query)
-- =====================================================================================
filtered_usage AS (
  SELECT
    u.*,
    transform(tep.filter_keys, k -> CONCAT(k, '=', u.custom_tags[k])) AS filter_actual,
    transform(tep.all_keys, k -> CONCAT(k, '=', u.custom_tags[k])) AS kvp,
    IF(
      size(tep.filter_keys) = 0 OR filter_actual = tep.filter_expected,
      array_join(kvp, ';'),
      ''
    ) AS _custom_tag_key_value_pairs,
    IF(
      _custom_tag_key_value_pairs = '',
      '<MISMATCH>',
      _custom_tag_key_value_pairs
    ) AS custom_tag_key_value_pairs
  FROM usage_filtered_by_type u
  CROSS JOIN tag_entry_parsed tep
  WHERE
    custom_tag_key_value_pairs != '<MISMATCH>'
    OR trim(:param_tag_entries) = '<ANY>'
),

-- =====================================================================================
-- STEP 4: Calculate Costs with List Prices (from reference query)
-- =====================================================================================
usage_with_costs AS (
  SELECT
    u.*,
    u.usage_quantity * lp.pricing.default AS list_cost
  FROM filtered_usage u
  INNER JOIN system.billing.list_prices lp
    ON u.cloud = lp.cloud
    AND u.sku_name = lp.sku_name
    AND u.usage_start_time >= lp.price_start_time
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
),

-- =====================================================================================
-- STEP 5: Aggregate Usage Data (similar to reference query's list_cost_per_job)
-- =====================================================================================
usage_aggregated AS (
  SELECT
    workspace_id,
    workspace_name,
    workspace_url,
    entity_type,
    sku_name,
    billing_origin_product,
    
    -- Entity IDs
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
    
    -- Execution time calculation
    MIN(usage_start_time) AS execution_start_time,
    MAX(usage_end_time) AS execution_end_time,
    ROUND(
      (UNIX_TIMESTAMP(MAX(usage_end_time)) - UNIX_TIMESTAMP(MIN(usage_start_time))) / 60.0,
      2
    ) AS execution_time_minutes,
    
    -- Custom tags (first non-null)
    FIRST(custom_tags, TRUE) AS custom_tags
    
  FROM usage_with_costs
  GROUP BY
    workspace_id,
    workspace_name,
    workspace_url,
    entity_type,
    sku_name,
    billing_origin_product,
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
    is_serverless
),

-- =====================================================================================
-- STEP 6: Most Recent Jobs (from reference query)
-- =====================================================================================
most_recent_jobs AS (
  SELECT *
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY workspace_id, job_id
        ORDER BY change_time DESC
      ) AS rn
    FROM system.lakeflow.jobs
  )
  WHERE rn = 1
),

-- =====================================================================================
-- STEP 7: Most Recent Pipelines (from reference query)
-- =====================================================================================
most_recent_pipelines AS (
  SELECT *
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY workspace_id, pipeline_id
        ORDER BY change_time DESC
      ) AS rn
    FROM system.lakeflow.pipelines
  )
  WHERE rn = 1
),

-- =====================================================================================
-- STEP 8: Most Recent Clusters
-- =====================================================================================
most_recent_clusters AS (
  SELECT *
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY workspace_id, cluster_id
        ORDER BY change_time DESC
      ) AS rn
    FROM system.compute.clusters
  )
  WHERE rn = 1
),

-- =====================================================================================
-- STEP 9: Warehouse Info
-- =====================================================================================
warehouse_info AS (
  SELECT *
  FROM (
    SELECT
      *,
      ROW_NUMBER() OVER (
        PARTITION BY workspace_id, warehouse_id
        ORDER BY change_time DESC
      ) AS rn
    FROM system.compute.warehouses
  )
  WHERE rn = 1
),

-- =====================================================================================
-- STEP 10: Node Specs (for hardware details)
-- =====================================================================================
node_specs AS (
  SELECT
    node_type,
    core_count,
    memory_mb / 1024 AS memory_gb
  FROM system.compute.node_types
)

-- =====================================================================================
-- FINAL SELECT: All original columns preserved
-- =====================================================================================
SELECT
    -- Workspace
    u.workspace_id,
    u.workspace_name,
    
    -- SKU
    u.sku_name,

    -- Entity URL (clickable link for dashboards)
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

    -- =========================================================================
    -- GOAL 1: JOB RUN COST (Cost of single job run)
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
    COALESCE(j.name, u.job_name_from_usage, p.name) AS job_or_pipeline_name,
    u.job_id,
    u.job_run_id,
    u.dlt_pipeline_id,
    u.dlt_update_id,
    
    -- =========================================================================
    -- GOAL 4: WHICH CLUSTER WAS USED
    -- =========================================================================
    c.cluster_name,
    u.cluster_id,
    c.cluster_source AS cluster_created_by,  -- JOB, UI, API
    c.owner AS cluster_owner,
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
      WHEN u.billing_origin_product = 'DLT' AND p.serverless = TRUE 
        THEN 'Automated - DLT Pipeline (Serverless)'
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'Automated - DLT Pipeline'
      
      -- Lakeflow Connect
      WHEN u.billing_origin_product = 'LAKEFLOW_CONNECT'
        THEN 'Automated - Lakeflow Connect'
      
      -- Jobs with schedule
      WHEN j.schedule IS NOT NULL 
        THEN 'Automated - Scheduled Job'
      
      -- Jobs with trigger
      WHEN j.trigger IS NOT NULL 
        THEN 'Automated - Triggered Job'
      
      -- Jobs without schedule (manual or API triggered)
      WHEN u.job_id IS NOT NULL AND j.schedule IS NULL 
        THEN 'Manual - Job Run (API/UI Triggered)'
      
      -- Serverless job compute
      WHEN u.is_serverless = 'true' AND u.job_id IS NOT NULL 
        THEN 'Manual - Serverless Job Compute'
      
      ELSE 'Unknown'
    END AS how_was_it_triggered,
    
    j.schedule AS job_schedule,
    
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
    
    c.num_workers AS fixed_worker_count,
    
    CASE 
      WHEN c.min_autoscale_workers IS NOT NULL 
        THEN CONCAT(c.min_autoscale_workers, ' to ', c.max_autoscale_workers)
      ELSE NULL
    END AS autoscale_worker_range,
    
    -- Total Cluster Capacity
    CASE 
      WHEN u.is_serverless = 'true' THEN 'Serverless (auto-scaled)'
      WHEN c.num_workers IS NOT NULL THEN 
        CONCAT(
          'Fixed: ', c.num_workers, ' workers | ',
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
      (COALESCE(c.num_workers, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS total_max_cores,
    
    COALESCE(driver_specs.memory_gb, 0) + 
      (COALESCE(c.num_workers, c.max_autoscale_workers, 0) * COALESCE(worker_specs.memory_gb, 0)) 
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
    wh.warehouse_type AS warehouse_type,  -- SERVERLESS, PRO, CLASSIC
    wh.warehouse_size AS warehouse_size,  -- SMALL, MEDIUM, LARGE, etc.
    CASE 
      WHEN wh.warehouse_id IS NOT NULL THEN
        CONCAT(
          'Type: ', COALESCE(wh.warehouse_type, 'N/A'), ' | ',
          'Size: ', COALESCE(wh.warehouse_size, 'N/A')
        )
      ELSE NULL
    END AS warehouse_details,
    
    -- DLT Pipeline Details
    p.name AS pipeline_name,
    p.pipeline_type,
    p.creator_user_name AS pipeline_creator,
    
    -- =========================================================================
    -- ADDITIONAL CONTEXT
    -- =========================================================================
    
    -- Entity Type (from reference query logic)
    u.entity_type,
    
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
    u.custom_tags['OWNER'] AS owner_tag

FROM usage_aggregated u

-- =====================================================================================
-- JOINS: Using workspace_id for proper scoping (from reference query)
-- =====================================================================================

-- Join to Jobs (with workspace scoping from reference query)
LEFT JOIN most_recent_jobs j
  ON u.entity_type LIKE '%JOB%'
  AND u.workspace_id = j.workspace_id
  AND u.job_id = CAST(j.job_id AS STRING)

-- Join to Pipelines (with workspace scoping from reference query)
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
