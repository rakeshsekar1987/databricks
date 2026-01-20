WITH list_cost_per_job_run AS (
  SELECT
    t1.workspace_id,
    t1.usage_metadata.job_id,
    t1.usage_metadata.job_run_id AS run_id,
    SUM(t1.usage_quantity * list_prices.pricing.default) AS list_cost,
    FIRST(identity_metadata.run_as, TRUE) AS run_as,
    FIRST(t1.custom_tags, TRUE) AS custom_tags,
    MIN(t1.usage_start_time) AS job_start_time,
    MAX(t1.usage_end_time) AS job_end_time,
    ROUND(
      (UNIX_TIMESTAMP(MAX(t1.usage_end_time)) - UNIX_TIMESTAMP(MIN(t1.usage_start_time))) / 60.0,
      2
    ) AS execution_time_minutes
  FROM system.billing.usage t1
  INNER JOIN system.billing.list_prices list_prices ON
    t1.cloud = list_prices.cloud AND
    t1.sku_name = list_prices.sku_name AND
    t1.usage_start_time >= list_prices.price_start_time AND
    (t1.usage_end_time <= list_prices.price_end_time OR list_prices.price_end_time IS NULL)
  WHERE
    t1.billing_origin_product = 'JOBS'
    AND t1.workspace_id = 1234455
    AND t1.usage_date >= '2025-01-01'
    AND t1.usage_date < '2026-01-01'
  GROUP BY ALL
),
most_recent_jobs AS (
  SELECT
    *,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
  FROM
    system.lakeflow.jobs 
  WHERE
    workspace_id = 1234455
  QUALIFY rn = 1
)
SELECT
    t1.workspace_id,
    t2.name,
    t1.job_id,
    t1.run_id,
    t1.run_as,
    t1.job_start_time,
    t1.job_end_time,
    t1.execution_time_minutes,
    SUM(list_cost) AS list_cost
FROM list_cost_per_job_run t1
  LEFT JOIN most_recent_jobs t2 USING (workspace_id, job_id)
GROUP BY ALL
ORDER BY list_cost DESC
