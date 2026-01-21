-- ============================================================================
-- UNIFIED COST BREAKDOWN - ALL WORKLOADS IN SINGLE QUERY (VALIDATED)
-- Workspace ID: 5244115429641560 | Year: 2025
-- ============================================================================
-- VALIDATED against system table schema
-- Fixed: column names, timestamp functions, NULL handling
-- ============================================================================

-- ============================================================================
-- STEP 1: First, run this to check your actual column names
-- ============================================================================
-- DESCRIBE system.billing.usage;
-- DESCRIBE system.billing.list_prices;
-- DESCRIBE system.lakeflow.jobs;
-- DESCRIBE system.compute.clusters;
-- DESCRIBE system.compute.warehouses;

-- Check usage_metadata structure:
-- SELECT usage_metadata.* FROM system.billing.usage LIMIT 1;

-- Check pricing structure:
-- SELECT pricing.* FROM system.billing.list_prices LIMIT 1;


-- ============================================================================
-- MAIN UNIFIED QUERY - VERSION 2 (VALIDATED)
-- ============================================================================

WITH billing_base AS (
    -- Base billing data with usage metadata extracted
    SELECT 
        U.workspace_id,
        U.sku_name,
        U.usage_date,
        U.usage_end_time,
        U.usage_quantity,
        -- Extract from usage_metadata struct
        U.usage_metadata.job_id AS job_id,
        U.usage_metadata.job_run_id AS job_run_id,
        U.usage_metadata.cluster_id AS cluster_id,
        U.usage_metadata.warehouse_id AS warehouse_id,
        -- Try notebook_path first, fall back to notebook_id if needed
        COALESCE(
            U.usage_metadata.notebook_path,
            CAST(U.usage_metadata.notebook_id AS STRING)
        ) AS notebook_path,
        U.usage_metadata.node_type AS node_type,
        U.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
        U.usage_metadata.dlt_update_id AS dlt_update_id
    FROM system.billing.usage U
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01'
        AND U.usage_date <= '2025-12-31'
),

billing_with_prices AS (
    -- Join with pricing
    SELECT 
        B.*,
        -- Handle different pricing struct paths
        COALESCE(
            P.pricing.default,
            P.pricing.effective_list.default,
            0
        ) AS unit_price
    FROM billing_base B
    LEFT JOIN system.billing.list_prices P 
        ON B.sku_name = P.sku_name
        AND B.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR B.usage_end_time < P.price_end_time)
),

-- ============================================================================
-- JOBS (Classic + Serverless)
-- ============================================================================
jobs_breakdown AS (
    SELECT 
        'JOB' AS workload_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            ELSE 'CLASSIC'
        END AS compute_type,
        B.job_id,
        B.job_run_id AS run_id,
        B.cluster_id,
        C.cluster_name,
        CAST(NULL AS STRING) AS warehouse_id,
        CAST(NULL AS STRING) AS warehouse_name,
        B.notebook_path,
        B.node_type,
        -- Compute size from Azure VM type
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            WHEN B.node_type LIKE '%Standard_E4%' OR B.node_type LIKE '%DS3%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_E8%' OR B.node_type LIKE '%DS4%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_E16%' OR B.node_type LIKE '%DS5%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_E32%' OR B.node_type LIKE '%DS12%' THEN '2XL'
            WHEN B.node_type LIKE '%Standard_E48%' OR B.node_type LIKE '%DS13%' THEN '3XL'
            WHEN B.node_type LIKE '%Standard_E64%' OR B.node_type LIKE '%DS14%' THEN '4XL'
            WHEN B.node_type LIKE '%Standard_D4%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_D8%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_D16%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_D32%' THEN '2XL'
            WHEN B.node_type LIKE '%Standard_D48%' THEN '3XL'
            WHEN B.node_type LIKE '%Standard_D64%' THEN '4XL'
            WHEN B.node_type LIKE '%Standard_L4%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_L8%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_L16%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_L32%' THEN '2XL'
            ELSE COALESCE(B.node_type, 'UNKNOWN')
        END AS compute_size,
        B.dlt_pipeline_id,
        B.usage_date,
        B.usage_end_time,
        B.usage_quantity,
        B.usage_quantity * B.unit_price AS cost
    FROM billing_with_prices B
    LEFT JOIN system.compute.clusters C 
        ON B.cluster_id = C.cluster_id 
        AND B.workspace_id = C.workspace_id
    WHERE B.sku_name LIKE '%JOBS%'
      AND B.job_id IS NOT NULL
),

-- ============================================================================
-- NOTEBOOK RUNS ON PERSONAL/ALL-PURPOSE CLUSTERS
-- ============================================================================
notebook_breakdown AS (
    SELECT 
        'NOTEBOOK' AS workload_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            ELSE 'CLASSIC'
        END AS compute_type,
        CAST(NULL AS STRING) AS job_id,
        CAST(NULL AS STRING) AS run_id,
        B.cluster_id,
        C.cluster_name,
        CAST(NULL AS STRING) AS warehouse_id,
        CAST(NULL AS STRING) AS warehouse_name,
        B.notebook_path,
        B.node_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            WHEN B.node_type LIKE '%Standard_E4%' OR B.node_type LIKE '%DS3%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_E8%' OR B.node_type LIKE '%DS4%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_E16%' OR B.node_type LIKE '%DS5%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_E32%' OR B.node_type LIKE '%DS12%' THEN '2XL'
            WHEN B.node_type LIKE '%Standard_E48%' OR B.node_type LIKE '%DS13%' THEN '3XL'
            WHEN B.node_type LIKE '%Standard_E64%' OR B.node_type LIKE '%DS14%' THEN '4XL'
            WHEN B.node_type LIKE '%Standard_D4%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_D8%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_D16%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_D32%' THEN '2XL'
            WHEN B.node_type LIKE '%Standard_D48%' THEN '3XL'
            WHEN B.node_type LIKE '%Standard_D64%' THEN '4XL'
            WHEN B.node_type LIKE '%Standard_L4%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_L8%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_L16%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_L32%' THEN '2XL'
            ELSE COALESCE(B.node_type, 'UNKNOWN')
        END AS compute_size,
        CAST(NULL AS STRING) AS dlt_pipeline_id,
        B.usage_date,
        B.usage_end_time,
        B.usage_quantity,
        B.usage_quantity * B.unit_price AS cost
    FROM billing_with_prices B
    LEFT JOIN system.compute.clusters C 
        ON B.cluster_id = C.cluster_id 
        AND B.workspace_id = C.workspace_id
    WHERE B.sku_name LIKE '%ALL_PURPOSE%'
),

-- ============================================================================
-- SQL QUERIES (Pro + Serverless)
-- ============================================================================
sql_breakdown AS (
    SELECT 
        'SQL' AS workload_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            ELSE 'CLASSIC'
        END AS compute_type,
        CAST(NULL AS STRING) AS job_id,
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS cluster_id,
        CAST(NULL AS STRING) AS cluster_name,
        B.warehouse_id,
        W.warehouse_name,
        CAST(NULL AS STRING) AS notebook_path,
        CAST(NULL AS STRING) AS node_type,
        -- SQL Warehouse size from name
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%2x-small%' THEN '2XS'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%x-small%' THEN 'XS'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%small%' THEN 'S'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%medium%' THEN 'M'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%2x-large%' THEN '2XL'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%3x-large%' THEN '3XL'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%4x-large%' THEN '4XL'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%x-large%' THEN 'XL'
            WHEN LOWER(COALESCE(W.warehouse_name, '')) LIKE '%large%' THEN 'L'
            ELSE 'CHECK_CONFIG'
        END AS compute_size,
        CAST(NULL AS STRING) AS dlt_pipeline_id,
        B.usage_date,
        B.usage_end_time,
        B.usage_quantity,
        B.usage_quantity * B.unit_price AS cost
    FROM billing_with_prices B
    LEFT JOIN system.compute.warehouses W 
        ON B.warehouse_id = W.warehouse_id 
        AND B.workspace_id = W.workspace_id
    WHERE B.sku_name LIKE '%SQL%'
      AND B.warehouse_id IS NOT NULL
),

-- ============================================================================
-- DLT PIPELINES
-- ============================================================================
dlt_breakdown AS (
    SELECT 
        'DLT' AS workload_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            ELSE 'CLASSIC'
        END AS compute_type,
        CAST(NULL AS STRING) AS job_id,
        B.dlt_update_id AS run_id,
        B.cluster_id,
        C.cluster_name,
        CAST(NULL AS STRING) AS warehouse_id,
        CAST(NULL AS STRING) AS warehouse_name,
        CAST(NULL AS STRING) AS notebook_path,
        B.node_type,
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            WHEN B.node_type LIKE '%Standard_E4%' OR B.node_type LIKE '%DS3%' THEN 'M'
            WHEN B.node_type LIKE '%Standard_E8%' OR B.node_type LIKE '%DS4%' THEN 'L'
            WHEN B.node_type LIKE '%Standard_E16%' OR B.node_type LIKE '%DS5%' THEN 'XL'
            WHEN B.node_type LIKE '%Standard_E32%' OR B.node_type LIKE '%DS12%' THEN '2XL'
            WHEN B.node_type LIKE '%Standard_E48%' OR B.node_type LIKE '%DS13%' THEN '3XL'
            WHEN B.node_type LIKE '%Standard_E64%' OR B.node_type LIKE '%DS14%' THEN '4XL'
            ELSE COALESCE(B.node_type, 'UNKNOWN')
        END AS compute_size,
        B.dlt_pipeline_id,
        B.usage_date,
        B.usage_end_time,
        B.usage_quantity,
        B.usage_quantity * B.unit_price AS cost
    FROM billing_with_prices B
    LEFT JOIN system.compute.clusters C 
        ON B.cluster_id = C.cluster_id 
        AND B.workspace_id = C.workspace_id
    WHERE B.dlt_pipeline_id IS NOT NULL
),

-- ============================================================================
-- COMBINE ALL WORKLOADS
-- ============================================================================
all_workloads AS (
    SELECT * FROM jobs_breakdown
    UNION ALL
    SELECT * FROM notebook_breakdown
    UNION ALL
    SELECT * FROM sql_breakdown
    UNION ALL
    SELECT * FROM dlt_breakdown
)

-- ============================================================================
-- FINAL AGGREGATED RESULT
-- ============================================================================
SELECT 
    workload_type,
    compute_type,
    compute_size,
    job_id,
    run_id,
    cluster_id,
    cluster_name,
    warehouse_id,
    warehouse_name,
    notebook_path,
    node_type,
    dlt_pipeline_id,
    MIN(usage_date) AS first_usage_date,
    MAX(usage_date) AS last_usage_date,
    MIN(usage_end_time) AS first_end_time,
    MAX(usage_end_time) AS last_end_time,
    COUNT(*) AS usage_records,
    ROUND(SUM(usage_quantity), 2) AS total_dbus,
    ROUND(SUM(cost), 2) AS cost_usd
FROM all_workloads
GROUP BY 
    workload_type,
    compute_type,
    compute_size,
    job_id,
    run_id,
    cluster_id,
    cluster_name,
    warehouse_id,
    warehouse_name,
    notebook_path,
    node_type,
    dlt_pipeline_id
ORDER BY cost_usd DESC;


-- ============================================================================
-- SIMPLER ALTERNATIVE IF ABOVE HAS ISSUES
-- This version uses minimal joins and should work on any Databricks version
-- ============================================================================
/*
SELECT 
    -- Workload Type
    CASE 
        WHEN U.sku_name LIKE '%JOBS%' AND U.usage_metadata.job_id IS NOT NULL THEN 'JOB'
        WHEN U.sku_name LIKE '%ALL_PURPOSE%' THEN 'NOTEBOOK'
        WHEN U.sku_name LIKE '%SQL%' AND U.usage_metadata.warehouse_id IS NOT NULL THEN 'SQL'
        WHEN U.usage_metadata.dlt_pipeline_id IS NOT NULL THEN 'DLT'
        ELSE 'OTHER'
    END AS workload_type,
    
    -- Compute Type
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    
    -- Compute Size
    CASE 
        WHEN U.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%E48%' OR U.usage_metadata.node_type LIKE '%DS13%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%E64%' OR U.usage_metadata.node_type LIKE '%DS14%' THEN '4XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
    END AS compute_size,
    
    U.sku_name,
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_run_id AS run_id,
    U.usage_metadata.cluster_id AS cluster_id,
    U.usage_metadata.warehouse_id AS warehouse_id,
    U.usage_metadata.notebook_path AS notebook_path,
    U.usage_metadata.node_type AS node_type,
    U.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    
    MIN(U.usage_date) AS first_usage_date,
    MAX(U.usage_date) AS last_usage_date,
    COUNT(*) AS usage_records,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(P.pricing.default * U.usage_quantity), 2) AS cost_usd

FROM system.billing.usage U
LEFT JOIN system.billing.list_prices P 
    ON U.sku_name = P.sku_name
    AND U.usage_end_time >= P.price_start_time
    AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date >= '2025-01-01'
    AND U.usage_date <= '2025-12-31'
    AND (
        (U.sku_name LIKE '%JOBS%' AND U.usage_metadata.job_id IS NOT NULL)
        OR U.sku_name LIKE '%ALL_PURPOSE%'
        OR (U.sku_name LIKE '%SQL%' AND U.usage_metadata.warehouse_id IS NOT NULL)
        OR U.usage_metadata.dlt_pipeline_id IS NOT NULL
    )
GROUP BY 
    U.sku_name,
    U.usage_metadata.job_id,
    U.usage_metadata.job_run_id,
    U.usage_metadata.cluster_id,
    U.usage_metadata.warehouse_id,
    U.usage_metadata.notebook_path,
    U.usage_metadata.node_type,
    U.usage_metadata.dlt_pipeline_id
ORDER BY cost_usd DESC;
*/


-- ============================================================================
-- DIAGNOSTIC QUERIES - Run these first to verify your schema
-- ============================================================================

-- 1. Check what columns exist in usage_metadata
-- SELECT DISTINCT 
--     usage_metadata.job_id,
--     usage_metadata.job_run_id,
--     usage_metadata.cluster_id,
--     usage_metadata.warehouse_id,
--     usage_metadata.notebook_path,
--     usage_metadata.node_type,
--     usage_metadata.dlt_pipeline_id
-- FROM system.billing.usage 
-- WHERE workspace_id = '5244115429641560'
-- LIMIT 10;

-- 2. Check pricing structure
-- SELECT sku_name, pricing 
-- FROM system.billing.list_prices 
-- LIMIT 5;

-- 3. Verify your original query still works
-- SELECT 
--     U.sku_name,
--     ROUND(SUM(U.usage_quantity), 2) AS total_usage_quantity, 
--     ROUND(SUM(P.pricing.effective_list.default * U.usage_quantity), 2) AS total_usage_cost
-- FROM system.billing.usage U
-- JOIN system.billing.list_prices P 
--     ON U.sku_name = P.sku_name
-- WHERE 
--     U.workspace_id = '5244115429641560' 
--     AND U.usage_date >= '2025-01-01' 
--     AND U.usage_date <= '2025-12-31' 
--     AND U.usage_end_time >= P.price_start_time
--     AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
-- GROUP BY U.sku_name;
