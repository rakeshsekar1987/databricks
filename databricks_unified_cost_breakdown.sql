-- ============================================================================
-- UNIFIED COST BREAKDOWN - ALL WORKLOADS IN SINGLE QUERY
-- Workspace ID: 5244115429641560 | Year: 2025
-- ============================================================================
-- This query combines:
-- 1. Jobs (Classic + Serverless)
-- 2. Notebook runs on Personal/All-Purpose Clusters
-- 3. SQL Queries (Pro + Serverless)
-- 4. DLT Pipelines
-- ============================================================================

WITH billing_with_prices AS (
    -- Base: Join billing usage with prices
    SELECT 
        U.workspace_id,
        U.sku_name,
        U.usage_date,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        U.usage_metadata.job_id,
        U.usage_metadata.job_run_id,
        U.usage_metadata.cluster_id,
        U.usage_metadata.warehouse_id,
        U.usage_metadata.notebook_path,
        U.usage_metadata.node_type,
        U.usage_metadata.dlt_pipeline_id,
        U.usage_metadata.dlt_update_id,
        P.pricing.effective_list.default AS unit_price,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01'
        AND U.usage_date <= '2025-12-31'
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
        B.job_id AS job_id,
        J.name AS job_name,
        B.job_run_id AS run_id,
        B.cluster_id AS cluster_id,
        C.cluster_name AS cluster_name,
        B.warehouse_id AS warehouse_id,
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
        B.usage_start_time,
        B.usage_end_time,
        B.usage_quantity,
        B.cost
    FROM billing_with_prices B
    LEFT JOIN system.lakeflow.jobs J 
        ON B.job_id = J.job_id 
        AND B.workspace_id = J.workspace_id
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
        CAST(NULL AS STRING) AS job_name,
        CAST(NULL AS STRING) AS run_id,
        B.cluster_id AS cluster_id,
        C.cluster_name AS cluster_name,
        B.warehouse_id AS warehouse_id,
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
        B.dlt_pipeline_id,
        B.usage_start_time,
        B.usage_end_time,
        B.usage_quantity,
        B.cost
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
        CAST(NULL AS STRING) AS job_name,
        CAST(NULL AS STRING) AS run_id,
        CAST(NULL AS STRING) AS cluster_id,
        CAST(NULL AS STRING) AS cluster_name,
        B.warehouse_id AS warehouse_id,
        W.warehouse_name AS warehouse_name,
        CAST(NULL AS STRING) AS notebook_path,
        CAST(NULL AS STRING) AS node_type,
        -- SQL Warehouse size from name or default
        CASE 
            WHEN B.sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
            WHEN LOWER(W.warehouse_name) LIKE '%2x-small%' OR LOWER(W.warehouse_name) LIKE '%2xs%' THEN '2XS'
            WHEN LOWER(W.warehouse_name) LIKE '%x-small%' OR LOWER(W.warehouse_name) LIKE '%xs%' THEN 'XS'
            WHEN LOWER(W.warehouse_name) LIKE '%small%' AND LOWER(W.warehouse_name) NOT LIKE '%x-small%' THEN 'S'
            WHEN LOWER(W.warehouse_name) LIKE '%medium%' THEN 'M'
            WHEN LOWER(W.warehouse_name) LIKE '%x-large%' OR LOWER(W.warehouse_name) LIKE '%xl%' THEN 'XL'
            WHEN LOWER(W.warehouse_name) LIKE '%2x-large%' OR LOWER(W.warehouse_name) LIKE '%2xl%' THEN '2XL'
            WHEN LOWER(W.warehouse_name) LIKE '%3x-large%' OR LOWER(W.warehouse_name) LIKE '%3xl%' THEN '3XL'
            WHEN LOWER(W.warehouse_name) LIKE '%4x-large%' OR LOWER(W.warehouse_name) LIKE '%4xl%' THEN '4XL'
            WHEN LOWER(W.warehouse_name) LIKE '%large%' THEN 'L'
            ELSE 'CHECK_CONFIG'
        END AS compute_size,
        CAST(NULL AS STRING) AS dlt_pipeline_id,
        B.usage_start_time,
        B.usage_end_time,
        B.usage_quantity,
        B.cost
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
        CAST(NULL AS STRING) AS job_name,
        B.dlt_update_id AS run_id,
        B.cluster_id AS cluster_id,
        C.cluster_name AS cluster_name,
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
        B.usage_start_time,
        B.usage_end_time,
        B.usage_quantity,
        B.cost
    FROM billing_with_prices B
    LEFT JOIN system.compute.clusters C 
        ON B.cluster_id = C.cluster_id 
        AND B.workspace_id = C.workspace_id
    WHERE (B.sku_name LIKE '%DLT%' OR B.dlt_pipeline_id IS NOT NULL)
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
    job_name,
    run_id,
    cluster_id,
    cluster_name,
    warehouse_id,
    warehouse_name,
    notebook_path,
    node_type,
    dlt_pipeline_id,
    MIN(usage_start_time) AS start_time,
    MAX(usage_end_time) AS end_time,
    ROUND(
        (UNIX_TIMESTAMP(MAX(usage_end_time)) - UNIX_TIMESTAMP(MIN(usage_start_time))) / 60.0, 
        2
    ) AS duration_minutes,
    ROUND(SUM(usage_quantity), 2) AS total_dbus,
    ROUND(SUM(cost), 2) AS cost_usd
FROM all_workloads
GROUP BY 
    workload_type,
    compute_type,
    compute_size,
    job_id,
    job_name,
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
-- ALTERNATIVE: DETAILED ROW-LEVEL VIEW (No Aggregation)
-- Use this if you want to see every billing record individually
-- ============================================================================
/*
WITH billing_with_prices AS (
    SELECT 
        U.workspace_id,
        U.sku_name,
        U.usage_date,
        U.usage_start_time,
        U.usage_end_time,
        U.usage_quantity,
        U.usage_metadata.job_id,
        U.usage_metadata.job_run_id,
        U.usage_metadata.cluster_id,
        U.usage_metadata.warehouse_id,
        U.usage_metadata.notebook_path,
        U.usage_metadata.node_type,
        U.usage_metadata.dlt_pipeline_id,
        U.usage_metadata.dlt_update_id,
        P.pricing.effective_list.default AS unit_price,
        P.pricing.effective_list.default * U.usage_quantity AS cost
    FROM system.billing.usage U
    JOIN system.billing.list_prices P 
        ON U.sku_name = P.sku_name
        AND U.usage_end_time >= P.price_start_time
        AND (P.price_end_time IS NULL OR U.usage_end_time < P.price_end_time)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date >= '2025-01-01'
        AND U.usage_date <= '2025-12-31'
)
SELECT 
    -- Workload Type
    CASE 
        WHEN sku_name LIKE '%JOBS%' AND job_id IS NOT NULL THEN 'JOB'
        WHEN sku_name LIKE '%ALL_PURPOSE%' THEN 'NOTEBOOK'
        WHEN sku_name LIKE '%SQL%' THEN 'SQL'
        WHEN sku_name LIKE '%DLT%' OR dlt_pipeline_id IS NOT NULL THEN 'DLT'
        ELSE 'OTHER'
    END AS workload_type,
    
    -- Compute Type
    CASE 
        WHEN sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    
    -- Compute Size
    CASE 
        WHEN sku_name LIKE '%SERVERLESS%' THEN 'SERVERLESS'
        WHEN node_type LIKE '%Standard_E4%' OR node_type LIKE '%DS3%' THEN 'M'
        WHEN node_type LIKE '%Standard_E8%' OR node_type LIKE '%DS4%' THEN 'L'
        WHEN node_type LIKE '%Standard_E16%' OR node_type LIKE '%DS5%' THEN 'XL'
        WHEN node_type LIKE '%Standard_E32%' OR node_type LIKE '%DS12%' THEN '2XL'
        WHEN node_type LIKE '%Standard_E48%' OR node_type LIKE '%DS13%' THEN '3XL'
        WHEN node_type LIKE '%Standard_E64%' OR node_type LIKE '%DS14%' THEN '4XL'
        ELSE COALESCE(node_type, 'UNKNOWN')
    END AS compute_size,
    
    sku_name,
    job_id,
    job_run_id AS run_id,
    cluster_id,
    warehouse_id,
    notebook_path,
    node_type,
    dlt_pipeline_id,
    dlt_update_id,
    usage_start_time AS start_time,
    usage_end_time AS end_time,
    ROUND((UNIX_TIMESTAMP(usage_end_time) - UNIX_TIMESTAMP(usage_start_time)) / 60.0, 2) AS duration_minutes,
    ROUND(usage_quantity, 4) AS dbus,
    ROUND(cost, 4) AS cost_usd
FROM billing_with_prices
WHERE 
    -- Filter to relevant workloads
    (sku_name LIKE '%JOBS%' AND job_id IS NOT NULL)
    OR sku_name LIKE '%ALL_PURPOSE%'
    OR (sku_name LIKE '%SQL%' AND warehouse_id IS NOT NULL)
    OR sku_name LIKE '%DLT%'
    OR dlt_pipeline_id IS NOT NULL
ORDER BY usage_start_time DESC;
*/
