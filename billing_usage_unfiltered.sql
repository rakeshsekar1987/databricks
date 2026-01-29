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

-- Step 3: Calculate costs per entity with optimized entity_type
list_cost_per_entity AS (
  SELECT
    u.workspace_id,
    -- Simplified entity_type: use boolean flag for faster comparisons later
    u.is_serverless,
    (u.billing_origin_product = 'JOBS') as is_job,
    COALESCE(u.job_id, u.dlt_pipeline_id) as entity_id,
    -- Conditional aggregation based on entity type
    COUNT(DISTINCT CASE WHEN u.billing_origin_product = 'JOBS' THEN u.job_run_id END) as job_runs,
    COUNT(DISTINCT CASE WHEN u.billing_origin_product != 'JOBS' THEN u.dlt_pipeline_id END) as pipeline_runs,
    SUM(u.usage_quantity * p.unit_price) as list_cost,
    MAX(u.run_as) as run_as,
    MAX(u.custom_tags) as custom_tags,
    MAX(u.job_name) as name,
    MAX(u.usage_end_time) as last_seen_date
  FROM usage_base u
  INNER JOIN filtered_prices p 
    ON u.cloud = p.cloud
    AND u.sku_name = p.sku_name
    AND u.usage_start_time >= p.price_start_time
    AND (u.usage_end_time <= p.price_end_time OR p.price_end_time IS NULL)
  GROUP BY 
    u.workspace_id,
    u.is_serverless,
    u.billing_origin_product = 'JOBS',
    COALESCE(u.job_id, u.dlt_pipeline_id)
),

-- Step 4: Get most recent jobs (filtered by workspace early)
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

-- Step 5: Get most recent pipelines (filtered by workspace early)
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

-- Step 6: Combine with job/pipeline metadata
enriched_data AS (
  SELECT
    c.workspace_id,
    c.is_serverless,
    c.is_job,
    CONCAT_WS(' ', 
      IF(c.is_serverless, 'SERVERLESS', ''), 
      IF(c.is_job, 'JOB', 'PIPELINE')
    ) as entity_type,
    c.entity_id,
    IF(c.is_job, c.job_runs, c.pipeline_runs) as runs,
    COALESCE(p.name, j.name, c.name) as name,
    COALESCE(c.run_as, j.run_as, p.run_as) as run_as,
    c.custom_tags,
    c.list_cost,
    c.last_seen_date
  FROM list_cost_per_entity c
  LEFT JOIN most_recent_jobs j 
    ON c.is_job 
    AND c.workspace_id = j.workspace_id 
    AND c.entity_id = j.job_id
  LEFT JOIN most_recent_pipelines p 
    ON NOT c.is_job 
    AND c.workspace_id = p.workspace_id 
    AND c.entity_id = p.pipeline_id
),

-- Step 7: Get workspace info (single lookup)
workspace_info AS (
  SELECT workspace_id, workspace_name, workspace_url
  FROM system.access.workspaces_latest
  WHERE workspace_id = 5244115429641560
)

-- Final output with HTML formatting
SELECT
  COALESCE(
    CONCAT('<a href="', w.workspace_url, '" target="_blank">', w.workspace_name, '</a>'),
    CAST(e.workspace_id AS STRING)
  ) as workspace,
  CONCAT(
    '<a href="', 
    w.workspace_url, 
    IF(e.is_job, '/jobs/', '/pipelines/'),
    e.entity_id,
    '" target="_blank">',
    COALESCE(e.name, e.entity_id),
    '</a>'
  ) as entity_url,
  e.workspace_id,
  e.entity_type,
  e.name,
  e.entity_id,
  e.runs,
  e.run_as,
  e.custom_tags,
  e.list_cost,
  e.last_seen_date
FROM enriched_data e
LEFT JOIN workspace_info w ON e.workspace_id = w.workspace_id
ORDER BY e.list_cost DESC;
