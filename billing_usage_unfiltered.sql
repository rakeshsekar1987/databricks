-- Unfiltered billing usage query
-- Workspace ID: 5244115429641560
-- Date range: 2025-01-01 to 2026-01-28

WITH usage_with_restrictions AS (
  SELECT
    t1.*,
    t2.workspace_name,
    t2.workspace_url,
    concat_ws(
      " ",
      CASE
        WHEN product_features.is_serverless THEN "SERVERLESS"
        ELSE ""
      END,
      CASE
        WHEN billing_origin_product = "JOBS" THEN "JOB"
        ELSE "PIPELINE"
      END
    ) as entity_type
  FROM
    system.billing.usage t1 
    LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
  WHERE
    (
      billing_origin_product IN ("JOBS", "DLT", "LAKEFLOW_CONNECT")
      OR (
        billing_origin_product = "SQL"
        AND usage_metadata.dlt_pipeline_id IS NOT NULL
      )
    )
    AND usage_date BETWEEN '2025-01-01' AND '2026-01-28'
    AND workspace_id = 5244115429641560
),
list_cost_per_job AS (
  SELECT
    t1.workspace_id,
    t1.workspace_name,
    t1.workspace_url,
    entity_type,
    coalesce(
      t1.usage_metadata.job_id,
      t1.usage_metadata.dlt_pipeline_id
    ) as entity_id,
    CASE
      WHEN entity_type RLIKE "JOB" THEN COUNT(DISTINCT usage_metadata.job_run_id)
      ELSE COUNT(DISTINCT usage_metadata.dlt_pipeline_id)
    END as runs,
    SUM(t1.usage_quantity * list_prices.pricing.default) as list_cost,
    first(identity_metadata.run_as, true) as run_as,
    first(t1.custom_tags, true) as custom_tags,
    first(usage_metadata.job_name, true) as name,
    MAX(t1.usage_end_time) as last_seen_date
  FROM
    usage_with_restrictions t1
    INNER JOIN system.billing.list_prices list_prices 
      ON t1.cloud = list_prices.cloud
      AND t1.sku_name = list_prices.sku_name
      AND t1.usage_start_time >= list_prices.price_start_time
      AND (
        t1.usage_end_time <= list_prices.price_end_time
        OR list_prices.price_end_time IS NULL
      )
  GROUP BY
    ALL
),
most_recent_jobs AS (
  SELECT
    *,
    ROW_NUMBER() OVER(
      PARTITION BY workspace_id, job_id
      ORDER BY change_time DESC
    ) as rn
  FROM
    system.lakeflow.jobs 
  QUALIFY rn = 1
),
most_recent_pipelines AS (
  SELECT
    *,
    ROW_NUMBER() OVER(
      PARTITION BY workspace_id, pipeline_id
      ORDER BY change_time DESC
    ) as rn
  FROM
    system.lakeflow.pipelines 
  QUALIFY rn = 1
),
output AS (
  SELECT
    t1.workspace_id,
    t1.workspace_name,
    t1.workspace_url,
    t1.entity_type,
    coalesce(t3.name, t2.name, t1.name) as name,
    t1.entity_id,
    runs,
    coalesce(t1.run_as, t2.run_as, t3.run_as) as run_as,
    t1.custom_tags,
    SUM(list_cost) as list_cost,
    t1.last_seen_date
  FROM
    list_cost_per_job t1
    LEFT JOIN most_recent_jobs t2 ON (
      t1.entity_type LIKE "%JOB%"
      AND t1.workspace_id = t2.workspace_id
      AND t1.entity_id = t2.job_id
    )
    LEFT JOIN most_recent_pipelines t3 ON (
      t1.entity_type LIKE "%PIPELINE%"
      AND t1.workspace_id = t3.workspace_id
      AND t1.entity_id = t3.pipeline_id
    )
  GROUP BY
    ALL
  ORDER BY
    list_cost DESC
)
SELECT
  coalesce(
    CONCAT(
      "<a href='",
      workspace_url,
      "' target='_blank'>",
      workspace_name,
      "</a>"
    ), 
    CAST(workspace_id AS STRING)
  ) as workspace,
  CASE 
    WHEN entity_type LIKE '%JOB%' THEN 
      CONCAT(
        "<a href='",
        workspace_url,
        "/jobs/",
        entity_id,
        "' target='_blank'>",
        COALESCE(name, entity_id),
        "</a>"
      )
    ELSE
      CONCAT(
        "<a href='", 
        workspace_url, 
        "/pipelines/",
        entity_id,
        "' target='_blank'>",
        COALESCE(name, entity_id),
        "</a>"
      )
  END as entity_url,
  workspace_id,
  entity_type,
  name,
  entity_id,
  runs,
  run_as,
  custom_tags,
  list_cost,
  last_seen_date
FROM output
ORDER BY list_cost DESC;
