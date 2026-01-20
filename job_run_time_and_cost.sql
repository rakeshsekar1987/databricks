-- eval tags param
WITH tag_entry_parsing AS (
  SELECT
    explode(
      split(
        if(
          trim(:param_single_tag_key) = '<USE TAG FILTER>',
          :param_tag_entries,
          :param_single_tag_key
        ),
        ';'
      )
    ) AS tag_entry,
    contains(tag_entry, '=') AS is_filter,
    if(is_filter, split(tag_entry, '=') [0], tag_entry) AS tag_key
),
-- parse tag entries
tag_entry_parsed AS (
  SELECT
    array_sort(collect_list(tag_key)) AS all_keys,
    array_sort(collect_list(if(is_filter, tag_key, null))) AS filter_keys,
    array_sort(collect_list(if(is_filter, tag_entry, null))) AS filter_expected
  FROM
    tag_entry_parsing
),
usage_with_restrictions AS (
  SELECT
    *
  FROM
    (
      SELECT
        t1.*,
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
        ) AS entity_type
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
        AND (
          usage_date BETWEEN :param_start_date
          AND :param_end_date
        )
        AND IF(
          :param_workspace = '<ALL WORKSPACES>',
          true,
          workspace_name = :param_workspace
        )
        AND IF(
          :param_run_as = '<ALL USERS>',
          true,
          identity_metadata.run_as = :param_run_as
        )
        AND IF(
          :param_cluster_type = '<ALL CLUSTER TYPES>',
          true,
          IF(
            :param_cluster_type = 'Serverless',
            product_features.is_serverless = TRUE,
            product_features.is_serverless = FALSE
          )
        )
    )
  WHERE
    IF(
      :param_object_type = '<ALL>',
      true,
      IF(
        :param_object_type = 'Jobs',
        entity_type RLIKE "JOB",
        entity_type RLIKE "PIPELINE"
      )
    )
),
filtered_usage AS (
  SELECT
    *
  FROM
    (
      SELECT
        transform(filter_keys, k -> concat(k, '=', custom_tags [k])) AS filter_actual,
        transform(all_keys, k -> concat(k, '=', custom_tags [k])) AS kvp,
        if(
          size(filter_keys) = 0
          OR filter_actual = filter_expected,
          array_join(kvp, ';'),
          ''
        ) AS _custom_tag_key_value_pairs,
        if(
          _custom_tag_key_value_pairs = "",
          "<MISMATCH>",
          _custom_tag_key_value_pairs
        ) AS custom_tag_key_value_pairs,
        *
      FROM
        usage_with_restrictions,
        tag_entry_parsed
    )
  WHERE
    (
      custom_tag_key_value_pairs != '<MISMATCH>'
      OR trim(:param_tag_entries) = '<ANY>'
    )
),
-- Updated to capture per-run timing information
list_cost_per_job_run AS (
  SELECT
    t1.workspace_id,
    entity_type,
    coalesce(
      t1.usage_metadata.job_id,
      t1.usage_metadata.dlt_pipeline_id
    ) AS entity_id,
    -- Include run_id for per-run granularity
    CASE
      WHEN entity_type RLIKE "JOB" THEN t1.usage_metadata.job_run_id
      ELSE t1.usage_metadata.dlt_update_id
    END AS run_id,
    SUM(t1.usage_quantity * list_prices.pricing.default) AS list_cost,
    FIRST(t1.identity_metadata.run_as, TRUE) AS run_as,
    FIRST(t1.custom_tags, TRUE) AS custom_tags,
    FIRST(usage_metadata.job_name, TRUE) AS name,
    -- Start and end time for each run
    MIN(t1.usage_start_time) AS run_start_time,
    MAX(t1.usage_end_time) AS run_end_time,
    -- Execution time in minutes
    ROUND(
      (UNIX_TIMESTAMP(MAX(t1.usage_end_time)) - UNIX_TIMESTAMP(MIN(t1.usage_start_time))) / 60.0,
      2
    ) AS execution_time_minutes
  FROM
    filtered_usage t1
    INNER JOIN system.billing.list_prices list_prices ON t1.cloud = list_prices.cloud
    AND t1.sku_name = list_prices.sku_name
    AND t1.usage_start_time >= list_prices.price_start_time
    AND (
      t1.usage_end_time <= list_prices.price_end_time
      OR list_prices.price_end_time IS NULL
    )
  GROUP BY
    t1.workspace_id,
    entity_type,
    entity_id,
    run_id
),
most_recent_jobs AS (
  SELECT
    *,
    ROW_NUMBER() OVER(
      PARTITION BY workspace_id,
      job_id
      ORDER BY
        change_time DESC
    ) AS rn
  FROM
    system.lakeflow.jobs QUALIFY rn = 1
),
most_recent_pipelines AS (
  SELECT
    *,
    ROW_NUMBER() OVER(
      PARTITION BY workspace_id,
      pipeline_id
      ORDER BY
        change_time DESC
    ) AS rn
  FROM
    system.lakeflow.pipelines QUALIFY rn = 1
),
output AS (
  SELECT
    t1.workspace_id,
    t1.entity_type,
    coalesce(t3.name, t2.name, t1.name) AS name,
    t1.entity_id,
    t1.run_id,
    t1.run_start_time,
    t1.run_end_time,
    t1.execution_time_minutes,
    coalesce(t1.run_as, t2.run_as, t3.run_as) AS run_as,
    t1.list_cost,
    t1.run_end_time AS last_seen_date
  FROM
    list_cost_per_job_run t1
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
  ORDER BY
    list_cost DESC
  LIMIT
    25000
)
SELECT
  coalesce(CONCAT(
    "<a href='",
    t2.workspace_url,
    "' target='_blank'>",
    t2.workspace_name,
    "</a>"
  ), t1.workspace_id) AS workspace,
  coalesce(CASE 
    WHEN entity_type LIKE '%JOB%' THEN 
      CONCAT(
        "<a href='",
        t2.workspace_url,
        "/jobs/",
        t1.entity_id,
        "' target='_blank'>",
        COALESCE(t1.name, t1.entity_id),
        "</a>"
      )
    ELSE
      CONCAT(
        "<a href='", t2.workspace_url, "/pipelines/",
        t1.entity_id,
        "' target='_blank'>",
        COALESCE(t1.name, t1.entity_id),
        "</a>"
      )
  END, t1.name) AS entity_url,
  t1.entity_type,
  t1.name,
  t1.entity_id,
  t1.run_id,
  t1.run_start_time,
  t1.run_end_time,
  t1.execution_time_minutes,
  t1.run_as,
  t1.list_cost,
  t1.last_seen_date
FROM output t1
  LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
ORDER BY
  list_cost DESC
