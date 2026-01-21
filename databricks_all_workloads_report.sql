-- ============================================================================
-- ALL WORKLOADS COST REPORT - JOBS, NOTEBOOKS, SQL, DLT
-- Workspace: USNPCDP003ADB02 (workspace_id: 5244115429641560)
-- Year: 2025
-- ============================================================================
-- Based on working Databricks system table schema
-- Includes: Jobs, Notebooks (All-Purpose), SQL, DLT Pipelines
-- ============================================================================

-- Parameters (adjust these as needed)
-- :param_start_date = '2025-01-01'
-- :param_end_date = '2025-12-31'
-- :param_workspace = 'USNPCDP003ADB02'

WITH 
-- ============================================================================
-- Get most recent job definitions
-- ============================================================================
most_recent_jobs AS (
    SELECT
        *,
        ROW_NUMBER() OVER(
            PARTITION BY workspace_id, job_id
            ORDER BY change_time DESC
        ) AS rn
    FROM system.lakeflow.jobs 
    QUALIFY rn = 1
),

-- ============================================================================
-- Get most recent pipeline definitions
-- ============================================================================
most_recent_pipelines AS (
    SELECT
        *,
        ROW_NUMBER() OVER(
            PARTITION BY workspace_id, pipeline_id
            ORDER BY change_time DESC
        ) AS rn
    FROM system.lakeflow.pipelines 
    QUALIFY rn = 1
),

-- ============================================================================
-- All usage data with workload classification
-- ============================================================================
all_usage AS (
    SELECT
        U.workspace_id,
        W.workspace_name,
        W.workspace_url,
        U.sku_name,
        U.billing_origin_product,
        U.usage_date,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        
        -- Workload Type Classification
        CASE
            WHEN U.billing_origin_product = 'JOBS' THEN 'JOB'
            WHEN U.billing_origin_product IN ('DLT', 'LAKEFLOW_CONNECT') THEN 'DLT_PIPELINE'
            WHEN U.billing_origin_product = 'SQL' AND U.usage_metadata.dlt_pipeline_id IS NOT NULL THEN 'DLT_PIPELINE'
            WHEN U.billing_origin_product = 'SQL' THEN 'SQL_WAREHOUSE'
            WHEN U.billing_origin_product = 'ALL_PURPOSE' THEN 'NOTEBOOK'
            WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'NOTEBOOK'
            ELSE U.billing_origin_product
        END AS workload_type,
        
        -- Compute Type (Serverless vs Classic)
        CASE
            WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
            ELSE 'CLASSIC'
        END AS compute_type,
        
        -- Entity IDs
        U.usage_metadata.job_id AS job_id,
        U.usage_metadata.job_run_id AS job_run_id,
        U.usage_metadata.job_name AS job_name,
        U.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
        U.usage_metadata.dlt_update_id AS dlt_update_id,
        U.usage_metadata.warehouse_id AS warehouse_id,
        U.usage_metadata.cluster_id AS cluster_id,
        U.usage_metadata.notebook_path AS notebook_path,
        U.usage_metadata.node_type AS node_type,
        
        -- Compute Size from node_type
        CASE
            WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E48%' OR U.usage_metadata.node_type LIKE '%DS13%' THEN '3XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_E64%' OR U.usage_metadata.node_type LIKE '%DS14%' THEN '4XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_D4%' THEN 'M'
            WHEN U.usage_metadata.node_type LIKE '%Standard_D8%' THEN 'L'
            WHEN U.usage_metadata.node_type LIKE '%Standard_D16%' THEN 'XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_D32%' THEN '2XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_L4%' THEN 'M'
            WHEN U.usage_metadata.node_type LIKE '%Standard_L8%' THEN 'L'
            WHEN U.usage_metadata.node_type LIKE '%Standard_L16%' THEN 'XL'
            WHEN U.usage_metadata.node_type LIKE '%Standard_L32%' THEN '2XL'
            ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
        END AS compute_size,
        
        -- Run As User
        U.identity_metadata.run_as AS run_as_user,
        
        -- Custom Tags
        U.custom_tags,
        
        -- Cloud info for pricing join
        U.cloud
        
    FROM system.billing.usage U
    LEFT JOIN system.access.workspaces_latest W 
        ON U.workspace_id = W.workspace_id
    WHERE 
        U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
        AND (
            W.workspace_name = 'USNPCDP003ADB02'
            OR U.workspace_id = '5244115429641560'
        )
        -- Include all relevant workload types
        AND (
            U.billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT', 'SQL', 'ALL_PURPOSE')
            OR U.sku_name LIKE '%JOBS%'
            OR U.sku_name LIKE '%ALL_PURPOSE%'
            OR U.sku_name LIKE '%SQL%'
            OR U.sku_name LIKE '%DLT%'
        )
),

-- ============================================================================
-- Join with pricing to get costs
-- ============================================================================
usage_with_cost AS (
    SELECT
        U.*,
        U.usage_quantity * LP.pricing.default AS list_cost
    FROM all_usage U
    INNER JOIN system.billing.list_prices LP 
        ON U.cloud = LP.cloud
        AND U.sku_name = LP.sku_name
        AND U.usage_start_time >= LP.price_start_time
        AND (U.usage_end_time <= LP.price_end_time OR LP.price_end_time IS NULL)
),

-- ============================================================================
-- Aggregate by run/entity
-- ============================================================================
aggregated_usage AS (
    SELECT
        workspace_id,
        workspace_name,
        workspace_url,
        workload_type,
        compute_type,
        compute_size,
        
        -- Entity identification
        COALESCE(job_id, dlt_pipeline_id, warehouse_id, cluster_id) AS entity_id,
        job_id,
        job_run_id,
        job_name,
        dlt_pipeline_id,
        dlt_update_id,
        warehouse_id,
        cluster_id,
        notebook_path,
        node_type,
        
        -- User
        FIRST(run_as_user, TRUE) AS run_as_user,
        
        -- Timing
        MIN(usage_start_time) AS start_time,
        MAX(usage_end_time) AS end_time,
        
        -- Duration in minutes
        ROUND(
            (UNIX_TIMESTAMP(MAX(usage_end_time)) - UNIX_TIMESTAMP(MIN(usage_start_time))) / 60.0,
            2
        ) AS duration_minutes,
        
        -- Run count
        CASE 
            WHEN workload_type = 'JOB' THEN COUNT(DISTINCT job_run_id)
            WHEN workload_type = 'DLT_PIPELINE' THEN COUNT(DISTINCT dlt_update_id)
            ELSE COUNT(DISTINCT usage_date)
        END AS run_count,
        
        -- Usage & Cost
        ROUND(SUM(usage_quantity), 2) AS total_dbus,
        ROUND(SUM(list_cost), 2) AS list_cost_usd,
        
        -- Last activity
        MAX(usage_end_time) AS last_seen_date
        
    FROM usage_with_cost
    GROUP BY
        workspace_id,
        workspace_name,
        workspace_url,
        workload_type,
        compute_type,
        compute_size,
        job_id,
        job_run_id,
        job_name,
        dlt_pipeline_id,
        dlt_update_id,
        warehouse_id,
        cluster_id,
        notebook_path,
        node_type
),

-- ============================================================================
-- Enrich with job/pipeline names
-- ============================================================================
enriched_output AS (
    SELECT
        A.workspace_id,
        A.workspace_name,
        A.workspace_url,
        A.workload_type,
        A.compute_type,
        A.compute_size,
        A.entity_id,
        
        -- Entity Name (from jobs/pipelines tables or usage_metadata)
        COALESCE(
            J.name,
            P.name,
            A.job_name,
            A.notebook_path,
            A.entity_id
        ) AS entity_name,
        
        A.job_id,
        A.job_run_id,
        A.dlt_pipeline_id,
        A.dlt_update_id,
        A.warehouse_id,
        A.cluster_id,
        A.notebook_path,
        A.node_type,
        
        COALESCE(A.run_as_user, J.run_as, P.run_as) AS run_as_user,
        
        A.start_time,
        A.end_time,
        A.duration_minutes,
        A.run_count,
        A.total_dbus,
        A.list_cost_usd,
        A.last_seen_date
        
    FROM aggregated_usage A
    LEFT JOIN most_recent_jobs J 
        ON A.workload_type = 'JOB'
        AND A.workspace_id = J.workspace_id
        AND A.job_id = J.job_id
    LEFT JOIN most_recent_pipelines P 
        ON A.workload_type = 'DLT_PIPELINE'
        AND A.workspace_id = P.workspace_id
        AND A.dlt_pipeline_id = P.pipeline_id
)

-- ============================================================================
-- FINAL OUTPUT
-- ============================================================================
SELECT
    workspace_name,
    workload_type,
    compute_type,
    compute_size,
    entity_name,
    entity_id,
    job_id,
    job_run_id,
    dlt_pipeline_id,
    warehouse_id,
    cluster_id,
    notebook_path,
    node_type,
    run_as_user,
    start_time,
    end_time,
    duration_minutes,
    run_count,
    total_dbus,
    list_cost_usd,
    last_seen_date,
    
    -- Clickable links for dashboard
    CASE 
        WHEN workload_type = 'JOB' AND workspace_url IS NOT NULL THEN 
            CONCAT('<a href="', workspace_url, '/jobs/', job_id, '" target="_blank">', COALESCE(entity_name, job_id), '</a>')
        WHEN workload_type = 'DLT_PIPELINE' AND workspace_url IS NOT NULL THEN 
            CONCAT('<a href="', workspace_url, '/pipelines/', dlt_pipeline_id, '" target="_blank">', COALESCE(entity_name, dlt_pipeline_id), '</a>')
        ELSE entity_name
    END AS entity_link

FROM enriched_output
ORDER BY list_cost_usd DESC
LIMIT 25000;


-- ============================================================================
-- SUMMARY VIEW - Aggregated by workload type
-- ============================================================================
/*
WITH ... (same CTEs as above) ...

SELECT
    workload_type,
    compute_type,
    COUNT(DISTINCT entity_id) AS unique_entities,
    SUM(run_count) AS total_runs,
    ROUND(SUM(total_dbus), 2) AS total_dbus,
    ROUND(SUM(list_cost_usd), 2) AS total_cost_usd
FROM enriched_output
GROUP BY workload_type, compute_type
ORDER BY total_cost_usd DESC;
*/


-- ============================================================================
-- JOB RUNS DETAIL VIEW - Each job run separately
-- ============================================================================
/*
SELECT
    workspace_name,
    'JOB' AS workload_type,
    CASE
        WHEN product_features.is_serverless = TRUE THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    CASE
        WHEN product_features.is_serverless = TRUE THEN 'SERVERLESS'
        WHEN usage_metadata.node_type LIKE '%E4%' OR usage_metadata.node_type LIKE '%DS3%' THEN 'M'
        WHEN usage_metadata.node_type LIKE '%E8%' OR usage_metadata.node_type LIKE '%DS4%' THEN 'L'
        WHEN usage_metadata.node_type LIKE '%E16%' OR usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
        WHEN usage_metadata.node_type LIKE '%E32%' OR usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
        WHEN usage_metadata.node_type LIKE '%E48%' OR usage_metadata.node_type LIKE '%DS13%' THEN '3XL'
        WHEN usage_metadata.node_type LIKE '%E64%' OR usage_metadata.node_type LIKE '%DS14%' THEN '4XL'
        ELSE COALESCE(usage_metadata.node_type, 'UNKNOWN')
    END AS compute_size,
    usage_metadata.job_id AS job_id,
    usage_metadata.job_name AS job_name,
    usage_metadata.job_run_id AS job_run_id,
    usage_metadata.notebook_path AS notebook_path,
    usage_metadata.cluster_id AS cluster_id,
    usage_metadata.node_type AS node_type,
    identity_metadata.run_as AS run_as_user,
    MIN(usage_start_time) AS start_time,
    MAX(usage_end_time) AS end_time,
    ROUND((UNIX_TIMESTAMP(MAX(usage_end_time)) - UNIX_TIMESTAMP(MIN(usage_start_time))) / 60.0, 2) AS duration_minutes,
    ROUND(SUM(usage_quantity), 2) AS total_dbus,
    ROUND(SUM(usage_quantity * LP.pricing.default), 2) AS list_cost_usd
FROM system.billing.usage U
LEFT JOIN system.access.workspaces_latest W ON U.workspace_id = W.workspace_id
INNER JOIN system.billing.list_prices LP 
    ON U.cloud = LP.cloud
    AND U.sku_name = LP.sku_name
    AND U.usage_start_time >= LP.price_start_time
    AND (U.usage_end_time <= LP.price_end_time OR LP.price_end_time IS NULL)
WHERE 
    U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND (W.workspace_name = 'USNPCDP003ADB02' OR U.workspace_id = '5244115429641560')
    AND U.billing_origin_product = 'JOBS'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY
    workspace_name,
    product_features.is_serverless,
    usage_metadata.job_id,
    usage_metadata.job_name,
    usage_metadata.job_run_id,
    usage_metadata.notebook_path,
    usage_metadata.cluster_id,
    usage_metadata.node_type,
    identity_metadata.run_as
ORDER BY list_cost_usd DESC
LIMIT 10000;
*/


-- ============================================================================
-- NOTEBOOK RUNS ON ALL-PURPOSE CLUSTERS - Detail View
-- ============================================================================
/*
SELECT
    W.workspace_name,
    'NOTEBOOK' AS workload_type,
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
    END AS compute_size,
    U.usage_metadata.cluster_id AS cluster_id,
    U.usage_metadata.notebook_path AS notebook_path,
    U.usage_metadata.node_type AS node_type,
    U.identity_metadata.run_as AS run_as_user,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * LP.pricing.default), 2) AS list_cost_usd
FROM system.billing.usage U
LEFT JOIN system.access.workspaces_latest W ON U.workspace_id = W.workspace_id
INNER JOIN system.billing.list_prices LP 
    ON U.cloud = LP.cloud
    AND U.sku_name = LP.sku_name
    AND U.usage_start_time >= LP.price_start_time
    AND (U.usage_end_time <= LP.price_end_time OR LP.price_end_time IS NULL)
WHERE 
    U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND (W.workspace_name = 'USNPCDP003ADB02' OR U.workspace_id = '5244115429641560')
    AND (U.billing_origin_product = 'ALL_PURPOSE' OR U.sku_name LIKE '%ALL_PURPOSE%')
GROUP BY
    W.workspace_name,
    U.product_features.is_serverless,
    U.usage_metadata.cluster_id,
    U.usage_metadata.notebook_path,
    U.usage_metadata.node_type,
    U.identity_metadata.run_as
ORDER BY list_cost_usd DESC
LIMIT 10000;
*/


-- ============================================================================
-- SQL WAREHOUSE QUERIES - Detail View
-- ============================================================================
/*
SELECT
    W.workspace_name,
    'SQL_WAREHOUSE' AS workload_type,
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    'SQL_WAREHOUSE' AS compute_size,
    U.usage_metadata.warehouse_id AS warehouse_id,
    U.identity_metadata.run_as AS run_as_user,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
    COUNT(DISTINCT U.usage_date) AS days_active,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * LP.pricing.default), 2) AS list_cost_usd
FROM system.billing.usage U
LEFT JOIN system.access.workspaces_latest W ON U.workspace_id = W.workspace_id
INNER JOIN system.billing.list_prices LP 
    ON U.cloud = LP.cloud
    AND U.sku_name = LP.sku_name
    AND U.usage_start_time >= LP.price_start_time
    AND (U.usage_end_time <= LP.price_end_time OR LP.price_end_time IS NULL)
WHERE 
    U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND (W.workspace_name = 'USNPCDP003ADB02' OR U.workspace_id = '5244115429641560')
    AND U.billing_origin_product = 'SQL'
    AND U.usage_metadata.warehouse_id IS NOT NULL
    AND U.usage_metadata.dlt_pipeline_id IS NULL  -- Exclude DLT using SQL
GROUP BY
    W.workspace_name,
    U.product_features.is_serverless,
    U.usage_metadata.warehouse_id,
    U.identity_metadata.run_as
ORDER BY list_cost_usd DESC
LIMIT 10000;
*/
