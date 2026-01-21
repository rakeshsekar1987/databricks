-- ============================================================================
-- AZURE DATABRICKS COST BREAKDOWN ANALYSIS - WORKSPACE ID: 5244115429641560
-- Year: 2025
-- ============================================================================
-- This file contains queries to extract detailed cost breakdown for:
-- 1. Jobs (Classic + Serverless)
-- 2. SQL Warehouse (Pro + Serverless)
-- 3. DLT Pipelines
-- 4. Interactive/Notebook runs on All-Purpose Compute
-- 
-- Each query includes: compute type, size, start/end time, duration, cost
-- ============================================================================

-- Set your workspace ID as a variable (optional - Databricks SQL supports this)
-- SET workspace_filter = '5244115429641560';

-- ============================================================================
-- QUERY 0: OVERVIEW - Cost Summary by Workload Type and Compute Type
-- ============================================================================
SELECT 
    CASE 
        WHEN U.sku_name LIKE '%JOBS%' THEN 'JOBS'
        WHEN U.sku_name LIKE '%SQL%' THEN 'SQL_WAREHOUSE'
        WHEN U.sku_name LIKE '%DLT%' THEN 'DLT'
        WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'INTERACTIVE'
        WHEN U.sku_name LIKE '%INFERENCE%' THEN 'MODEL_SERVING'
        ELSE 'OTHER'
    END AS workload_type,
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.sku_name,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS total_cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
GROUP BY 1, 2, 3
ORDER BY total_cost_usd DESC;


-- ============================================================================
-- QUERY 1: JOBS COST BREAKDOWN (Classic Compute)
-- Shows each job run with timing, duration, compute size, and cost
-- ============================================================================
SELECT 
    'CLASSIC' AS compute_type,
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_run_id AS job_run_id,
    J.name AS job_name,
    U.usage_metadata.cluster_id AS cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type AS node_type,
    -- Extract compute size from node_type (e.g., Standard_DS3_v2 -> parse size)
    CASE 
        WHEN U.usage_metadata.node_type LIKE '%_XS%' OR U.usage_metadata.node_type LIKE '%Extra_Small%' THEN 'XS'
        WHEN U.usage_metadata.node_type LIKE '%_S_%' OR U.usage_metadata.node_type LIKE '%Small%' THEN 'S'
        WHEN U.usage_metadata.node_type LIKE '%_M_%' OR U.usage_metadata.node_type LIKE '%Medium%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%_L_%' OR U.usage_metadata.node_type LIKE '%Large%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%_XL%' OR U.usage_metadata.node_type LIKE '%Extra_Large%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%2XL%' OR U.usage_metadata.node_type LIKE '%XXL%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%4XL%' THEN '4XL'
        -- Azure VM Size parsing (DS, E, F series)
        WHEN U.usage_metadata.node_type LIKE '%DS3%' OR U.usage_metadata.node_type LIKE '%E4%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%DS4%' OR U.usage_metadata.node_type LIKE '%E8%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%DS5%' OR U.usage_metadata.node_type LIKE '%E16%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%DS12%' OR U.usage_metadata.node_type LIKE '%E32%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%DS13%' OR U.usage_metadata.node_type LIKE '%E48%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%DS14%' OR U.usage_metadata.node_type LIKE '%E64%' THEN '4XL'
        ELSE 'UNKNOWN'
    END AS compute_size,
    U.usage_metadata.notebook_path AS notebook_path,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, MIN(U.usage_start_time), MAX(U.usage_end_time)), 2) AS duration_minutes,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.lakeflow.jobs J 
    ON U.usage_metadata.job_id = J.job_id 
    AND U.workspace_id = J.workspace_id
LEFT JOIN system.compute.clusters C 
    ON U.usage_metadata.cluster_id = C.cluster_id 
    AND U.workspace_id = C.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.sku_name = 'PREMIUM_JOBS_COMPUTE'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY 
    U.usage_metadata.job_id,
    U.usage_metadata.job_run_id,
    J.name,
    U.usage_metadata.cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type,
    U.usage_metadata.notebook_path
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 2: JOBS COST BREAKDOWN (Serverless Compute)
-- ============================================================================
SELECT 
    'SERVERLESS' AS compute_type,
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_run_id AS job_run_id,
    J.name AS job_name,
    U.usage_metadata.notebook_path AS notebook_path,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, MIN(U.usage_start_time), MAX(U.usage_end_time)), 2) AS duration_minutes,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.lakeflow.jobs J 
    ON U.usage_metadata.job_id = J.job_id 
    AND U.workspace_id = J.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.sku_name LIKE '%JOBS_SERVERLESS%'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY 
    U.usage_metadata.job_id,
    U.usage_metadata.job_run_id,
    J.name,
    U.usage_metadata.notebook_path
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 3: SQL WAREHOUSE COST BREAKDOWN (Pro - Classic)
-- Shows warehouse usage with size and cost
-- ============================================================================
SELECT 
    'SQL_PRO' AS compute_type,
    U.usage_metadata.warehouse_id AS warehouse_id,
    W.warehouse_name,
    -- Warehouse size is typically in the name or we derive from cluster_count
    CASE 
        WHEN LOWER(W.warehouse_name) LIKE '%2x-small%' OR LOWER(W.warehouse_name) LIKE '%2xs%' THEN '2XS'
        WHEN LOWER(W.warehouse_name) LIKE '%x-small%' OR LOWER(W.warehouse_name) LIKE '%xs%' THEN 'XS'
        WHEN LOWER(W.warehouse_name) LIKE '%small%' THEN 'S'
        WHEN LOWER(W.warehouse_name) LIKE '%medium%' THEN 'M'
        WHEN LOWER(W.warehouse_name) LIKE '%large%' AND LOWER(W.warehouse_name) NOT LIKE '%x-large%' THEN 'L'
        WHEN LOWER(W.warehouse_name) LIKE '%x-large%' OR LOWER(W.warehouse_name) LIKE '%xl%' THEN 'XL'
        WHEN LOWER(W.warehouse_name) LIKE '%2x-large%' OR LOWER(W.warehouse_name) LIKE '%2xl%' THEN '2XL'
        WHEN LOWER(W.warehouse_name) LIKE '%3x-large%' OR LOWER(W.warehouse_name) LIKE '%3xl%' THEN '3XL'
        WHEN LOWER(W.warehouse_name) LIKE '%4x-large%' OR LOWER(W.warehouse_name) LIKE '%4xl%' THEN '4XL'
        ELSE 'CHECK_CONFIG'
    END AS warehouse_size,
    DATE(MIN(U.usage_start_time)) AS first_usage_date,
    DATE(MAX(U.usage_end_time)) AS last_usage_date,
    COUNT(DISTINCT DATE(U.usage_date)) AS days_active,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.compute.warehouses W 
    ON U.usage_metadata.warehouse_id = W.warehouse_id 
    AND U.workspace_id = W.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.sku_name LIKE '%SQL_PRO%'
    AND U.usage_metadata.warehouse_id IS NOT NULL
GROUP BY 
    U.usage_metadata.warehouse_id,
    W.warehouse_name
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 4: SQL WAREHOUSE COST BREAKDOWN (Serverless)
-- ============================================================================
SELECT 
    'SERVERLESS_SQL' AS compute_type,
    U.usage_metadata.warehouse_id AS warehouse_id,
    W.warehouse_name,
    'SERVERLESS' AS warehouse_size,
    DATE(MIN(U.usage_start_time)) AS first_usage_date,
    DATE(MAX(U.usage_end_time)) AS last_usage_date,
    COUNT(DISTINCT DATE(U.usage_date)) AS days_active,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.compute.warehouses W 
    ON U.usage_metadata.warehouse_id = W.warehouse_id 
    AND U.workspace_id = W.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.sku_name LIKE '%SERVERLESS_SQL%'
    AND U.usage_metadata.warehouse_id IS NOT NULL
GROUP BY 
    U.usage_metadata.warehouse_id,
    W.warehouse_name
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 5: SQL QUERY HISTORY - Detailed Query-Level Breakdown
-- Shows individual queries with timing and cost attribution
-- ============================================================================
SELECT 
    Q.statement_id,
    Q.executed_by_user_id AS user_id,
    Q.compute.warehouse_id AS warehouse_id,
    W.warehouse_name,
    CASE 
        WHEN Q.query_source.job_info.job_id IS NOT NULL THEN 'JOB_TRIGGERED'
        ELSE 'INTERACTIVE'
    END AS query_source_type,
    Q.query_source.job_info.job_id AS source_job_id,
    Q.start_time,
    Q.end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, Q.start_time, Q.end_time), 2) AS duration_minutes,
    Q.total_duration_ms / 1000.0 AS duration_seconds,
    Q.rows_produced,
    Q.read_bytes / (1024*1024) AS read_mb
FROM system.query.history Q
LEFT JOIN system.compute.warehouses W 
    ON Q.compute.warehouse_id = W.warehouse_id
WHERE 
    Q.workspace_id = '5244115429641560'
    AND Q.start_time >= '2025-01-01'
    AND Q.start_time < '2026-01-01'
ORDER BY Q.start_time DESC
LIMIT 1000;


-- ============================================================================
-- QUERY 6: DLT PIPELINE COST BREAKDOWN
-- ============================================================================
SELECT 
    'DLT' AS workload_type,
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.usage_metadata.dlt_pipeline_id AS pipeline_id,
    U.usage_metadata.dlt_update_id AS update_id,
    U.usage_metadata.dlt_maintenance_id AS maintenance_id,
    U.usage_metadata.cluster_id AS cluster_id,
    U.usage_metadata.node_type AS node_type,
    CASE 
        WHEN U.usage_metadata.node_type LIKE '%DS3%' OR U.usage_metadata.node_type LIKE '%E4%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%DS4%' OR U.usage_metadata.node_type LIKE '%E8%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%DS5%' OR U.usage_metadata.node_type LIKE '%E16%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%DS12%' OR U.usage_metadata.node_type LIKE '%E32%' THEN '2XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'SERVERLESS')
    END AS compute_size,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, MIN(U.usage_start_time), MAX(U.usage_end_time)), 2) AS duration_minutes,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND (U.sku_name LIKE '%DLT%' OR U.usage_metadata.dlt_pipeline_id IS NOT NULL)
GROUP BY 
    U.sku_name,
    U.usage_metadata.dlt_pipeline_id,
    U.usage_metadata.dlt_update_id,
    U.usage_metadata.dlt_maintenance_id,
    U.usage_metadata.cluster_id,
    U.usage_metadata.node_type
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 7: ALL-PURPOSE COMPUTE (Interactive/Notebook) COST BREAKDOWN
-- Shows notebook runs on personal/shared clusters
-- ============================================================================
SELECT 
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.usage_metadata.cluster_id AS cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type AS node_type,
    CASE 
        WHEN U.usage_metadata.node_type LIKE '%DS3%' OR U.usage_metadata.node_type LIKE '%E4%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%DS4%' OR U.usage_metadata.node_type LIKE '%E8%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%DS5%' OR U.usage_metadata.node_type LIKE '%E16%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%DS12%' OR U.usage_metadata.node_type LIKE '%E32%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%DS13%' OR U.usage_metadata.node_type LIKE '%E48%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%DS14%' OR U.usage_metadata.node_type LIKE '%E64%' THEN '4XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'SERVERLESS')
    END AS compute_size,
    U.usage_metadata.notebook_path AS notebook_path,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, MIN(U.usage_start_time), MAX(U.usage_end_time)), 2) AS duration_minutes,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.compute.clusters C 
    ON U.usage_metadata.cluster_id = C.cluster_id 
    AND U.workspace_id = C.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.sku_name LIKE '%ALL_PURPOSE%'
GROUP BY 
    U.sku_name,
    U.usage_metadata.cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type,
    U.usage_metadata.notebook_path
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 8: JOB RUN TIMELINE - Detailed Job Run Timing from Lakeflow Tables
-- Gets exact start/end times for each job run
-- ============================================================================
SELECT 
    JRT.job_id,
    J.name AS job_name,
    JRT.run_id,
    JRT.period_start_time AS start_time,
    JRT.period_end_time AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, JRT.period_start_time, JRT.period_end_time), 2) AS duration_minutes,
    JRT.result_state,
    JRT.termination_code
FROM system.lakeflow.job_run_timeline JRT
LEFT JOIN system.lakeflow.jobs J 
    ON JRT.job_id = J.job_id 
    AND JRT.workspace_id = J.workspace_id
WHERE 
    JRT.workspace_id = '5244115429641560'
    AND JRT.period_start_time >= '2025-01-01'
    AND JRT.period_start_time < '2026-01-01'
ORDER BY JRT.period_start_time DESC;


-- ============================================================================
-- QUERY 9: JOB TASK RUN TIMELINE - Task-Level Breakdown with Compute IDs
-- Shows each task within a job with its compute
-- ============================================================================
SELECT 
    JTRT.job_id,
    J.name AS job_name,
    JTRT.job_run_id,
    JTRT.run_id AS task_run_id,
    JTRT.task_key,
    JTRT.period_start_time AS start_time,
    JTRT.period_end_time AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, JTRT.period_start_time, JTRT.period_end_time), 2) AS duration_minutes,
    JTRT.compute_ids AS compute_ids,
    JTRT.result_state
FROM system.lakeflow.job_task_run_timeline JTRT
LEFT JOIN system.lakeflow.jobs J 
    ON JTRT.job_id = J.job_id 
    AND JTRT.workspace_id = J.workspace_id
WHERE 
    JTRT.workspace_id = '5244115429641560'
    AND JTRT.period_start_time >= '2025-01-01'
    AND JTRT.period_start_time < '2026-01-01'
ORDER BY JTRT.period_start_time DESC;


-- ============================================================================
-- QUERY 10: COMPREHENSIVE UNIFIED VIEW - All Workloads Combined
-- Master query combining Jobs, SQL, DLT, and Interactive with all details
-- ============================================================================
WITH jobs_usage AS (
    SELECT 
        'JOBS' AS workload_type,
        CASE WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.job_id AS resource_id,
        J.name AS resource_name,
        U.usage_metadata.job_run_id AS run_id,
        U.usage_metadata.cluster_id AS cluster_id,
        C.cluster_name,
        U.usage_metadata.node_type AS node_type,
        U.usage_metadata.notebook_path AS notebook_path,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    LEFT JOIN system.lakeflow.jobs J ON U.usage_metadata.job_id = J.job_id AND U.workspace_id = J.workspace_id
    LEFT JOIN system.compute.clusters C ON U.usage_metadata.cluster_id = C.cluster_id AND U.workspace_id = C.workspace_id
    WHERE U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01' AND U.usage_date <= '2025-12-31'
        AND U.sku_name LIKE '%JOBS%'
),
sql_usage AS (
    SELECT 
        'SQL' AS workload_type,
        CASE WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.warehouse_id AS resource_id,
        W.warehouse_name AS resource_name,
        NULL AS run_id,
        NULL AS cluster_id,
        NULL AS cluster_name,
        NULL AS node_type,
        NULL AS notebook_path,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    LEFT JOIN system.compute.warehouses W ON U.usage_metadata.warehouse_id = W.warehouse_id AND U.workspace_id = W.workspace_id
    WHERE U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01' AND U.usage_date <= '2025-12-31'
        AND U.sku_name LIKE '%SQL%'
),
dlt_usage AS (
    SELECT 
        'DLT' AS workload_type,
        CASE WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.dlt_pipeline_id AS resource_id,
        CONCAT('Pipeline: ', COALESCE(U.usage_metadata.dlt_pipeline_id, 'Unknown')) AS resource_name,
        U.usage_metadata.dlt_update_id AS run_id,
        U.usage_metadata.cluster_id AS cluster_id,
        NULL AS cluster_name,
        U.usage_metadata.node_type AS node_type,
        NULL AS notebook_path,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    WHERE U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01' AND U.usage_date <= '2025-12-31'
        AND (U.sku_name LIKE '%DLT%' OR U.usage_metadata.dlt_pipeline_id IS NOT NULL)
),
interactive_usage AS (
    SELECT 
        'INTERACTIVE' AS workload_type,
        CASE WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.cluster_id AS resource_id,
        C.cluster_name AS resource_name,
        NULL AS run_id,
        U.usage_metadata.cluster_id AS cluster_id,
        C.cluster_name,
        U.usage_metadata.node_type AS node_type,
        U.usage_metadata.notebook_path AS notebook_path,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    LEFT JOIN system.compute.clusters C ON U.usage_metadata.cluster_id = C.cluster_id AND U.workspace_id = C.workspace_id
    WHERE U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01' AND U.usage_date <= '2025-12-31'
        AND U.sku_name LIKE '%ALL_PURPOSE%'
),
all_usage AS (
    SELECT * FROM jobs_usage
    UNION ALL
    SELECT * FROM sql_usage
    UNION ALL
    SELECT * FROM dlt_usage
    UNION ALL
    SELECT * FROM interactive_usage
)
SELECT 
    workload_type,
    compute_type,
    resource_id,
    resource_name,
    run_id,
    cluster_id,
    cluster_name,
    node_type,
    -- Compute size derivation
    CASE 
        WHEN compute_type = 'SERVERLESS' THEN 'SERVERLESS'
        WHEN node_type LIKE '%DS3%' OR node_type LIKE '%E4%' THEN 'M'
        WHEN node_type LIKE '%DS4%' OR node_type LIKE '%E8%' THEN 'L'
        WHEN node_type LIKE '%DS5%' OR node_type LIKE '%E16%' THEN 'XL'
        WHEN node_type LIKE '%DS12%' OR node_type LIKE '%E32%' THEN '2XL'
        WHEN node_type LIKE '%DS13%' OR node_type LIKE '%E48%' THEN '3XL'
        WHEN node_type LIKE '%DS14%' OR node_type LIKE '%E64%' THEN '4XL'
        ELSE COALESCE(node_type, 'UNKNOWN')
    END AS compute_size,
    notebook_path,
    MIN(usage_start_time) AS start_time,
    MAX(usage_end_time) AS end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, MIN(usage_start_time), MAX(usage_end_time)), 2) AS duration_minutes,
    ROUND(SUM(usage_quantity), 2) AS total_dbus,
    ROUND(SUM(cost), 2) AS cost_usd
FROM all_usage
GROUP BY 
    workload_type,
    compute_type,
    resource_id,
    resource_name,
    run_id,
    cluster_id,
    cluster_name,
    node_type,
    notebook_path
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 11: TOP NOTEBOOKS BY COST
-- Identifies most expensive notebooks across all compute types
-- ============================================================================
SELECT 
    U.usage_metadata.notebook_path AS notebook_path,
    CASE 
        WHEN U.sku_name LIKE '%JOBS%' THEN 'JOBS'
        WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'INTERACTIVE'
        ELSE 'OTHER'
    END AS workload_type,
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.usage_metadata.cluster_id AS cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type AS node_type,
    COUNT(DISTINCT U.usage_metadata.job_run_id) AS run_count,
    MIN(U.usage_start_time) AS first_run,
    MAX(U.usage_end_time) AS last_run,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.compute.clusters C 
    ON U.usage_metadata.cluster_id = C.cluster_id 
    AND U.workspace_id = C.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.usage_metadata.notebook_path IS NOT NULL
GROUP BY 
    U.usage_metadata.notebook_path,
    U.sku_name,
    U.usage_metadata.cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type
ORDER BY cost_usd DESC
LIMIT 100;


-- ============================================================================
-- QUERY 12: CLUSTER UTILIZATION SUMMARY
-- Shows all clusters used with their costs and utilization
-- ============================================================================
SELECT 
    U.usage_metadata.cluster_id AS cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type AS node_type,
    CASE 
        WHEN U.usage_metadata.node_type LIKE '%DS3%' OR U.usage_metadata.node_type LIKE '%E4%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%DS4%' OR U.usage_metadata.node_type LIKE '%E8%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%DS5%' OR U.usage_metadata.node_type LIKE '%E16%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%DS12%' OR U.usage_metadata.node_type LIKE '%E32%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%DS13%' OR U.usage_metadata.node_type LIKE '%E48%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%DS14%' OR U.usage_metadata.node_type LIKE '%E64%' THEN '4XL'
        ELSE 'UNKNOWN'
    END AS compute_size,
    CASE 
        WHEN U.sku_name LIKE '%JOBS%' THEN 'JOBS'
        WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'INTERACTIVE'
        WHEN U.sku_name LIKE '%DLT%' THEN 'DLT'
        ELSE 'OTHER'
    END AS primary_workload,
    COUNT(DISTINCT U.usage_metadata.job_id) AS jobs_count,
    COUNT(DISTINCT U.usage_metadata.notebook_path) AS notebooks_count,
    COUNT(DISTINCT DATE(U.usage_date)) AS days_active,
    MIN(U.usage_start_time) AS first_usage,
    MAX(U.usage_end_time) AS last_usage,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
LEFT JOIN system.compute.clusters C 
    ON U.usage_metadata.cluster_id = C.cluster_id 
    AND U.workspace_id = C.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND U.usage_metadata.cluster_id IS NOT NULL
GROUP BY 
    U.usage_metadata.cluster_id,
    C.cluster_name,
    U.usage_metadata.node_type,
    U.sku_name
ORDER BY cost_usd DESC;


-- ============================================================================
-- QUERY 13: MONTHLY COST TREND BY WORKLOAD TYPE
-- Shows cost progression over months
-- ============================================================================
SELECT 
    DATE_TRUNC('month', U.usage_date) AS month,
    CASE 
        WHEN U.sku_name LIKE '%JOBS%' THEN 'JOBS'
        WHEN U.sku_name LIKE '%SQL%' THEN 'SQL_WAREHOUSE'
        WHEN U.sku_name LIKE '%DLT%' THEN 'DLT'
        WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'INTERACTIVE'
        ELSE 'OTHER'
    END AS workload_type,
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS cost_usd
FROM system.billing.usage U
JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
GROUP BY 1, 2, 3
ORDER BY month, cost_usd DESC;


-- ============================================================================
-- QUERY 14: NODE TIMELINE - Detailed Compute Node Usage
-- Shows actual node-level usage with timing from system.compute.node_timeline
-- ============================================================================
SELECT 
    NT.cluster_id,
    C.cluster_name,
    NT.instance_id,
    NT.node_type,
    -- Derive compute size from Azure VM type
    CASE 
        WHEN NT.node_type LIKE '%DS3%' OR NT.node_type LIKE '%E4%' THEN 'M'
        WHEN NT.node_type LIKE '%DS4%' OR NT.node_type LIKE '%E8%' THEN 'L'
        WHEN NT.node_type LIKE '%DS5%' OR NT.node_type LIKE '%E16%' THEN 'XL'
        WHEN NT.node_type LIKE '%DS12%' OR NT.node_type LIKE '%E32%' THEN '2XL'
        WHEN NT.node_type LIKE '%DS13%' OR NT.node_type LIKE '%E48%' THEN '3XL'
        WHEN NT.node_type LIKE '%DS14%' OR NT.node_type LIKE '%E64%' THEN '4XL'
        ELSE NT.node_type
    END AS compute_size,
    NT.start_time,
    NT.end_time,
    ROUND(TIMESTAMPDIFF(MINUTE, NT.start_time, NT.end_time), 2) AS duration_minutes
FROM system.compute.node_timeline NT
LEFT JOIN system.compute.clusters C 
    ON NT.cluster_id = C.cluster_id 
    AND NT.workspace_id = C.workspace_id
WHERE 
    NT.workspace_id = '5244115429641560'
    AND NT.start_time >= '2025-01-01'
    AND NT.start_time < '2026-01-01'
ORDER BY NT.start_time DESC;


-- ============================================================================
-- END OF QUERIES
-- ============================================================================
-- Summary of what each query provides:
-- 
-- Query 0:  High-level cost summary by workload and compute type
-- Query 1:  Jobs on Classic compute with timing and cost
-- Query 2:  Jobs on Serverless compute with timing and cost
-- Query 3:  SQL Warehouse Pro (classic) usage and cost
-- Query 4:  SQL Warehouse Serverless usage and cost
-- Query 5:  Individual SQL query history with timing
-- Query 6:  DLT Pipeline costs with update details
-- Query 7:  Interactive/Notebook usage on All-Purpose compute
-- Query 8:  Job run timeline with exact start/end times
-- Query 9:  Task-level job run details with compute IDs
-- Query 10: Unified view combining all workloads
-- Query 11: Top notebooks by cost
-- Query 12: Cluster utilization summary
-- Query 13: Monthly cost trends
-- Query 14: Node-level compute timeline
-- ============================================================================
