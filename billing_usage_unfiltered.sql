-- Optimized Unfiltered Billing Usage Query
-- Workspace ID: 5244115429641560
-- Date range: 2025-01-01 to 2026-01-28

WITH 
-- Step 1: Get usage data with only required columns (avoid SELECT *)
usage_base AS (
  SELECT
    workspace_id,
    cloud,
    sku_name,
    usage_quantity,
    usage_start_time,
    usage_end_time,
    usage_metadata.job_id,
    usage_metadata.job_run_id,
    usage_metadata.dlt_pipeline_id,
    usage_metadata.job_name,
    identity_metadata.run_as,
    custom_tags,
    product_features.is_serverless,
    billing_origin_product
  FROM system.billing.usage
  WHERE 
    workspace_id = 5244115429641560
    AND usage_date BETWEEN '2025-01-01' AND '2026-01-28'
    AND (
      billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
      OR (billing_origin_product = 'SQL' AND usage_metadata.dlt_pipeline_id IS NOT NULL)
    )
),

-- Step 2: Pre-filter list prices to reduce join size
filtered_prices AS (
  SELECT 
    cloud,
    sku_name,
    price_start_time,
    price_end_time,
    pricing.default as unit_price
  FROM system.billing.list_prices
  WHERE price_start_time <= '2026-01-28'
    AND (price_end_time >= '2025-01-01' OR price_end_time IS NULL)
),

-- Step 3: Calculate costs per entity - matches original logic exactly
list_cost_per_entity AS (
  SELECT
    u.workspace_id,
    -- Build entity_type exactly like original: concat_ws(" ", serverless_part, type_part)
    TRIM(CONCAT_WS(' ', 
      CASE WHEN u.is_serverless THEN 'SERVERLESS' ELSE '' END,
      CASE WHEN u.billing_origin_product = 'JOBS' THEN 'JOB' ELSE 'PIPELINE' END
    )) as entity_type,
    COALESCE(u.job_id, u.dlt_pipeline_id) as entity_id,
    -- Runs: COUNT DISTINCT job_run_id for jobs, dlt_pipeline_id for pipelines
    CASE
      WHEN u.billing_origin_product = 'JOBS' THEN COUNT(DISTINCT u.job_run_id)
      ELSE COUNT(DISTINCT u.dlt_pipeline_id)
    END as runs,
    SUM(u.usage_quantity * p.unit_price) as list_cost,
    -- Use first() with ignoreNulls=true to match original behavior
    FIRST(u.run_as, true) as run_as,
    FIRST(u.custom_tags, true) as custom_tags,
    FIRST(u.job_name, true) as name,
    MAX(u.usage_end_time) as last_seen_date
  FROM usage_base u
  INNER JOIN filtered_prices p 
    ON u.cloud = p.cloud
    AND u.sku_name = p.sku_name
    AND u.usage_start_time >= p.price_start_time
    AND (u.usage_end_time <= p.price_end_time OR p.price_end_time IS NULL)
  GROUP BY 
    u.workspace_id,
    TRIM(CONCAT_WS(' ', 
      CASE WHEN u.is_serverless THEN 'SERVERLESS' ELSE '' END,
      CASE WHEN u.billing_origin_product = 'JOBS' THEN 'JOB' ELSE 'PIPELINE' END
    )),
    COALESCE(u.job_id, u.dlt_pipeline_id),
    -- Need to include this in GROUP BY for the CASE in runs
    u.billing_origin_product = 'JOBS'
),

-- Step 4: Get most recent jobs (filtered by workspace early for performance)
most_recent_jobs AS (
  SELECT
    workspace_id,
    job_id,
    name,
    run_as
  FROM (
    SELECT
      workspace_id,
      job_id,
      name,
      run_as,
      ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) as rn
    FROM system.lakeflow.jobs
    WHERE workspace_id = 5244115429641560
  )
  WHERE rn = 1
),

-- Step 5: Get most recent pipelines (filtered by workspace early for performance)
most_recent_pipelines AS (
  SELECT
    workspace_id,
    pipeline_id,
    name,
    run_as
  FROM (
    SELECT
      workspace_id,
      pipeline_id,
      name,
      run_as,
      ROW_NUMBER() OVER(PARTITION BY workspace_id, pipeline_id ORDER BY change_time DESC) as rn
    FROM system.lakeflow.pipelines
    WHERE workspace_id = 5244115429641560
  )
  WHERE rn = 1
),

-- Step 6: Combine with job/pipeline metadata - matches original coalesce order
output AS (
  SELECT
    t1.workspace_id,
    t1.entity_type,
    -- Name: coalesce(pipeline.name, job.name, usage.name) - matches original order
    COALESCE(t3.name, t2.name, t1.name) as name,
    t1.entity_id,
    t1.runs,
    -- Run_as: coalesce(usage.run_as, job.run_as, pipeline.run_as) - matches original order
    COALESCE(t1.run_as, t2.run_as, t3.run_as) as run_as,
    t1.custom_tags,
    SUM(t1.list_cost) as list_cost,
    t1.last_seen_date
  FROM list_cost_per_entity t1
  LEFT JOIN most_recent_jobs t2 ON (
    t1.entity_type LIKE '%JOB%'
    AND t1.workspace_id = t2.workspace_id
    AND t1.entity_id = t2.job_id
  )
  LEFT JOIN most_recent_pipelines t3 ON (
    t1.entity_type LIKE '%PIPELINE%'
    AND t1.workspace_id = t3.workspace_id
    AND t1.entity_id = t3.pipeline_id
  )
  GROUP BY ALL
  ORDER BY list_cost DESC
)

-- Final output with HTML formatting
SELECT
  COALESCE(
    CONCAT('<a href="', t2.workspace_url, '" target="_blank">', t2.workspace_name, '</a>'),
    CAST(t1.workspace_id AS STRING)
  ) as workspace,
  COALESCE(
    CASE 
      WHEN t1.entity_type LIKE '%JOB%' THEN 
        CONCAT(
          '<a href="', t2.workspace_url, '/jobs/', t1.entity_id, '" target="_blank">',
          COALESCE(t1.name, t1.entity_id),
          '</a>'
        )
      ELSE
        CONCAT(
          '<a href="', t2.workspace_url, '/pipelines/', t1.entity_id, '" target="_blank">',
          COALESCE(t1.name, t1.entity_id),
          '</a>'
        )
    END,
    t1.name
  ) as entity_url,
  t1.workspace_id,
  t1.entity_type,
  t1.name,
  t1.entity_id,
  t1.runs,
  t1.run_as,
  t1.custom_tags,
  t1.list_cost,
  t1.last_seen_date
FROM output t1
LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
ORDER BY t1.list_cost DESC;
