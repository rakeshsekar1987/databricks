            -- =====================================================
            -- QUERY FOR JOBS, PIPELINES, AND PERSONAL CLUSTER USAGE
            -- Includes execution times and notebook tracking
            -- =====================================================
            
            -- eval tags param
            with tag_entry_parsing as (
              select
                explode(
                  split(
                    if(
                      trim(:param_single_tag_key) = '<USE TAG FILTER>',
                      :param_tag_entries,
                      :param_single_tag_key
                    ),
                    ';'
                  )
                ) as tag_entry,
                contains(tag_entry, '=') as is_filter,
                if(is_filter, split(tag_entry, '=') [0], tag_entry) as tag_key
            ),
            -- parse tag entries
            tag_entry_parsed as (
              select
                array_sort(collect_list(tag_key)) as all_keys,
                array_sort(collect_list(if(is_filter, tag_key, null))) as filter_keys,
                array_sort(collect_list(if(is_filter, tag_entry, null))) as filter_expected
              from
                tag_entry_parsing
            ),
            
            -- =====================================================
            -- SECTION 1: JOBS AND PIPELINES USAGE (Original Query)
            -- =====================================================
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
                    ) as entity_type
                  FROM
                    system.billing.usage t1 left JOIN system.access.workspaces_latest t2 USING (workspace_id)
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
              select
                *
              from
                (
                  select
                    transform(filter_keys, k -> concat(k, '=', custom_tags [k])) as filter_actual,
                    transform(all_keys, k -> concat(k, '=', custom_tags [k])) as kvp,
                    if(
                      size(filter_keys) = 0
                      or filter_actual = filter_expected,
                      array_join(kvp, ';'),
                      ''
                    ) as _custom_tag_key_value_pairs,
                    if(
                      _custom_tag_key_value_pairs = "",
                      "<MISMATCH>",
                      _custom_tag_key_value_pairs
                    ) as custom_tag_key_value_pairs,
                    *
                  from
                    usage_with_restrictions,
                    tag_entry_parsed
                )
              where
                (
                  custom_tag_key_value_pairs != '<MISMATCH>'
                  OR trim(:param_tag_entries) = '<ANY>'
                )
            ),
            list_cost_per_job as (
              SELECT
                t1.workspace_id,
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
                MAX(t1.usage_end_time) as last_seen_date,
                MIN(t1.usage_start_time) as start_time,
                MAX(t1.usage_end_time) as end_time,
                ROUND(
                  (UNIX_TIMESTAMP(MAX(t1.usage_end_time)) - UNIX_TIMESTAMP(MIN(t1.usage_start_time))) / 60.0,
                  2
                ) as execution_time_minutes,
                NULL as cluster_id,
                NULL as notebook_id
              FROM
                filtered_usage t1
                INNER JOIN system.billing.list_prices list_prices on t1.cloud = list_prices.cloud
                and t1.sku_name = list_prices.sku_name
                and t1.usage_start_time >= list_prices.price_start_time
                and (
                  t1.usage_end_time <= list_prices.price_end_time
                  or list_prices.price_end_time is null
                )
              GROUP BY
                ALL
            ),
            
            -- =====================================================
            -- SECTION 2: PERSONAL/INTERACTIVE CLUSTER USAGE
            -- =====================================================
            personal_cluster_usage AS (
              SELECT
                t1.*,
                "INTERACTIVE CLUSTER" as entity_type
              FROM
                system.billing.usage t1 
                LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
              WHERE
                -- All-Purpose / Interactive compute
                billing_origin_product IN ("ALL_PURPOSE", "INTERACTIVE")
                AND (
                  usage_date BETWEEN :param_start_date
                  AND :param_end_date
                )
                AND IF(
                  :param_workspace = '<ALL WORKSPACES>',
                  true,
                  t2.workspace_name = :param_workspace
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
            ),
            
            -- Get the most recent cluster information
            most_recent_clusters AS (
              SELECT
                *,
                ROW_NUMBER() OVER(
                  PARTITION BY workspace_id, cluster_id
                  ORDER BY change_time DESC
                ) as rn
              FROM
                system.compute.clusters 
              QUALIFY rn = 1
            ),
            
            -- Aggregate personal cluster costs
            list_cost_per_personal_cluster AS (
              SELECT
                t1.workspace_id,
                "INTERACTIVE CLUSTER" as entity_type,
                t1.usage_metadata.cluster_id as entity_id,
                COUNT(DISTINCT usage_date) as runs,  -- Count distinct days as "runs" for interactive
                SUM(t1.usage_quantity * list_prices.pricing.default) as list_cost,
                first(identity_metadata.run_as, true) as run_as,
                first(t1.custom_tags, true) as custom_tags,
                first(c.cluster_name, true) as name,
                MAX(t1.usage_end_time) as last_seen_date,
                MIN(t1.usage_start_time) as start_time,
                MAX(t1.usage_end_time) as end_time,
                ROUND(
                  SUM(t1.usage_quantity) * 60,  -- DBUs typically billed per hour, convert to approximate minutes
                  2
                ) as execution_time_minutes,
                t1.usage_metadata.cluster_id as cluster_id,
                first(t1.usage_metadata.notebook_id, true) as notebook_id
              FROM
                personal_cluster_usage t1
                INNER JOIN system.billing.list_prices list_prices 
                  ON t1.cloud = list_prices.cloud
                  AND t1.sku_name = list_prices.sku_name
                  AND t1.usage_start_time >= list_prices.price_start_time
                  AND (
                    t1.usage_end_time <= list_prices.price_end_time
                    OR list_prices.price_end_time IS NULL
                  )
                LEFT JOIN most_recent_clusters c
                  ON t1.workspace_id = c.workspace_id
                  AND t1.usage_metadata.cluster_id = c.cluster_id
              GROUP BY
                t1.workspace_id,
                t1.usage_metadata.cluster_id
            ),
            
            -- =====================================================
            -- SECTION 3: NOTEBOOK EXECUTION DETAILS (if available)
            -- This provides granular notebook-level tracking
            -- =====================================================
            notebook_usage AS (
              SELECT
                t1.workspace_id,
                "NOTEBOOK" as entity_type,
                COALESCE(t1.usage_metadata.notebook_id, t1.usage_metadata.notebook_path) as entity_id,
                COUNT(*) as runs,
                SUM(t1.usage_quantity * list_prices.pricing.default) as list_cost,
                first(identity_metadata.run_as, true) as run_as,
                first(t1.custom_tags, true) as custom_tags,
                first(t1.usage_metadata.notebook_path, true) as name,
                MAX(t1.usage_end_time) as last_seen_date,
                MIN(t1.usage_start_time) as start_time,
                MAX(t1.usage_end_time) as end_time,
                ROUND(
                  (UNIX_TIMESTAMP(MAX(t1.usage_end_time)) - UNIX_TIMESTAMP(MIN(t1.usage_start_time))) / 60.0,
                  2
                ) as execution_time_minutes,
                first(t1.usage_metadata.cluster_id, true) as cluster_id,
                first(t1.usage_metadata.notebook_id, true) as notebook_id
              FROM
                system.billing.usage t1
                LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
                INNER JOIN system.billing.list_prices list_prices 
                  ON t1.cloud = list_prices.cloud
                  AND t1.sku_name = list_prices.sku_name
                  AND t1.usage_start_time >= list_prices.price_start_time
                  AND (
                    t1.usage_end_time <= list_prices.price_end_time
                    OR list_prices.price_end_time IS NULL
                  )
              WHERE
                t1.usage_metadata.notebook_id IS NOT NULL
                AND billing_origin_product IN ("ALL_PURPOSE", "INTERACTIVE")
                AND (
                  usage_date BETWEEN :param_start_date
                  AND :param_end_date
                )
                AND IF(
                  :param_workspace = '<ALL WORKSPACES>',
                  true,
                  t2.workspace_name = :param_workspace
                )
                AND IF(
                  :param_run_as = '<ALL USERS>',
                  true,
                  identity_metadata.run_as = :param_run_as
                )
              GROUP BY
                t1.workspace_id,
                COALESCE(t1.usage_metadata.notebook_id, t1.usage_metadata.notebook_path)
            ),
            
            -- =====================================================
            -- SECTION 4: COMBINE ALL RESULTS
            -- =====================================================
            most_recent_jobs as (
              SELECT
                *,
                ROW_NUMBER() OVER(
                  PARTITION BY workspace_id,
                  job_id
                  ORDER BY
                    change_time DESC
                ) as rn
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
                ) as rn
              FROM
                system.lakeflow.pipelines QUALIFY rn = 1
            ),
            
            -- Combine jobs/pipelines with personal cluster usage
            combined_usage AS (
              -- Jobs and Pipelines
              SELECT
                t1.workspace_id,
                t1.entity_type,
                coalesce(t3.name, t2.name, t1.name) as name,
                t1.entity_id,
                t1.runs,
                coalesce(t1.run_as, t2.run_as, t3.run_as) as run_as,
                t1.list_cost,
                t1.last_seen_date,
                t1.start_time,
                t1.end_time,
                t1.execution_time_minutes,
                t1.cluster_id,
                t1.notebook_id
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
              
              UNION ALL
              
              -- Personal/Interactive Clusters
              SELECT
                workspace_id,
                entity_type,
                name,
                entity_id,
                runs,
                run_as,
                list_cost,
                last_seen_date,
                start_time,
                end_time,
                execution_time_minutes,
                cluster_id,
                notebook_id
              FROM
                list_cost_per_personal_cluster
              WHERE
                IF(
                  :param_object_type = '<ALL>',
                  true,
                  :param_object_type = 'Interactive Clusters'
                )
              
              UNION ALL
              
              -- Notebook-level details
              SELECT
                workspace_id,
                entity_type,
                name,
                entity_id,
                runs,
                run_as,
                list_cost,
                last_seen_date,
                start_time,
                end_time,
                execution_time_minutes,
                cluster_id,
                notebook_id
              FROM
                notebook_usage
              WHERE
                IF(
                  :param_object_type = '<ALL>',
                  true,
                  :param_object_type = 'Notebooks'
                )
            ),
            
            output AS (
              SELECT
                workspace_id,
                entity_type,
                name,
                entity_id,
                SUM(runs) as runs,
                first(run_as, true) as run_as,
                SUM(list_cost) as list_cost,
                MAX(last_seen_date) as last_seen_date,
                MIN(start_time) as start_time,
                MAX(end_time) as end_time,
                SUM(execution_time_minutes) as execution_time_minutes,
                first(cluster_id, true) as cluster_id,
                first(notebook_id, true) as notebook_id
              FROM
                combined_usage
              GROUP BY
                workspace_id,
                entity_type,
                name,
                entity_id
              ORDER BY
                list_cost DESC
              LIMIT
                25000
            )
            
            -- =====================================================
            -- FINAL OUTPUT
            -- =====================================================
            SELECT
                coalesce(CONCAT(
                  "<a href='",
                  t2.workspace_url,
                  "' target='_blank'>",
                  t2.workspace_name,
                  "</a>"
                ), t1.workspace_id) as workspace,
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
                  WHEN entity_type LIKE '%PIPELINE%' THEN
                    CONCAT(
                      "<a href='", t2.workspace_url, "/pipelines/",
                      t1.entity_id,
                      "' target='_blank'>",
                      COALESCE(t1.name, t1.entity_id),
                      "</a>"
                    )
                  WHEN entity_type = 'INTERACTIVE CLUSTER' THEN
                    CONCAT(
                      "<a href='", t2.workspace_url, "/#setting/clusters/",
                      t1.entity_id,
                      "/configuration' target='_blank'>",
                      COALESCE(t1.name, t1.entity_id),
                      "</a>"
                    )
                  WHEN entity_type = 'NOTEBOOK' THEN
                    CONCAT(
                      "<a href='", t2.workspace_url, "/#notebook/",
                      t1.entity_id,
                      "' target='_blank'>",
                      COALESCE(t1.name, t1.entity_id),
                      "</a>"
                    )
                  ELSE t1.name
                END, t1.name) as entity_url,
                t1.entity_type,
                t1.entity_id,
                t1.name,
                t1.runs,
                t1.run_as,
                t1.start_time,
                t1.end_time,
                t1.execution_time_minutes,
                t1.cluster_id,
                t1.notebook_id,
                t1.list_cost,
                t1.last_seen_date
              FROM output t1
                LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
              ORDER BY
                list_cost DESC
