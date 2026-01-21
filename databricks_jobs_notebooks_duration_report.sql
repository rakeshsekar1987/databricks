-- ============================================================================
-- JOBS & NOTEBOOKS DURATION REPORT - OPTIMIZED
-- Workspace: 5244115429641560 | Year: 2025
-- ============================================================================
-- Goal: Find all jobs/notebooks that ran, how long they took, notebook path
-- Optimized for performance and accuracy
-- ============================================================================


-- ============================================================================
-- QUERY 1: ALL JOB RUNS WITH DURATION AND NOTEBOOK PATH
-- Each job run as a separate row with accurate timing
-- ============================================================================
SELECT
    -- Identifiers
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_run_id AS job_run_id,
    COALESCE(U.usage_metadata.job_name, J.name) AS job_name,
    
    -- Notebook path (if job uses a notebook task)
    U.usage_metadata.notebook_path AS notebook_path,
    
    -- Compute details
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.usage_metadata.cluster_id AS cluster_id,
    U.usage_metadata.node_type AS node_type,
    
    -- Compute size
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%E48%' OR U.usage_metadata.node_type LIKE '%DS13%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%E64%' OR U.usage_metadata.node_type LIKE '%DS14%' THEN '4XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
    END AS compute_size,
    
    -- User who ran it
    U.identity_metadata.run_as AS run_as_user,
    
    -- Timing
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    
    -- Duration in minutes
    ROUND(
        (UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0,
        2
    ) AS duration_minutes,
    
    -- Duration in hours (for long running jobs)
    ROUND(
        (UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 3600.0,
        2
    ) AS duration_hours,
    
    -- Cost
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd

FROM system.billing.usage U
INNER JOIN system.billing.list_prices P 
    ON U.cloud = P.cloud
    AND U.sku_name = P.sku_name
    AND U.usage_start_time >= P.price_start_time
    AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
LEFT JOIN system.lakeflow.jobs J
    ON U.usage_metadata.job_id = J.job_id
    AND U.workspace_id = J.workspace_id
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND U.billing_origin_product = 'JOBS'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY
    U.usage_metadata.job_id,
    U.usage_metadata.job_run_id,
    U.usage_metadata.job_name,
    J.name,
    U.usage_metadata.notebook_path,
    U.product_features.is_serverless,
    U.usage_metadata.cluster_id,
    U.usage_metadata.node_type,
    U.identity_metadata.run_as
ORDER BY duration_minutes DESC
LIMIT 10000;


-- ============================================================================
-- QUERY 2: NOTEBOOK RUNS ON ALL-PURPOSE/PERSONAL CLUSTERS WITH DURATION
-- Interactive notebook usage
-- ============================================================================
SELECT
    -- Notebook path
    U.usage_metadata.notebook_path AS notebook_path,
    
    -- Cluster details
    U.usage_metadata.cluster_id AS cluster_id,
    
    -- Compute details
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        ELSE 'CLASSIC'
    END AS compute_type,
    U.usage_metadata.node_type AS node_type,
    
    -- Compute size
    CASE
        WHEN U.product_features.is_serverless = TRUE THEN 'SERVERLESS'
        WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
        WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
        WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
        WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
        WHEN U.usage_metadata.node_type LIKE '%E48%' OR U.usage_metadata.node_type LIKE '%DS13%' THEN '3XL'
        WHEN U.usage_metadata.node_type LIKE '%E64%' OR U.usage_metadata.node_type LIKE '%DS14%' THEN '4XL'
        ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
    END AS compute_size,
    
    -- User
    U.identity_metadata.run_as AS run_as_user,
    
    -- Timing
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    
    -- Duration
    ROUND(
        (UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0,
        2
    ) AS duration_minutes,
    
    ROUND(
        (UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 3600.0,
        2
    ) AS duration_hours,
    
    -- Usage count (number of billing records)
    COUNT(*) AS usage_records,
    
    -- Cost
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd

FROM system.billing.usage U
INNER JOIN system.billing.list_prices P 
    ON U.cloud = P.cloud
    AND U.sku_name = P.sku_name
    AND U.usage_start_time >= P.price_start_time
    AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND (U.billing_origin_product = 'ALL_PURPOSE' OR U.sku_name LIKE '%ALL_PURPOSE%')
GROUP BY
    U.usage_metadata.notebook_path,
    U.usage_metadata.cluster_id,
    U.product_features.is_serverless,
    U.usage_metadata.node_type,
    U.identity_metadata.run_as
ORDER BY duration_minutes DESC
LIMIT 10000;


-- ============================================================================
-- QUERY 3: COMBINED - JOBS + NOTEBOOKS IN ONE VIEW (UNION)
-- Single query for all workloads with duration
-- ============================================================================
SELECT
    workload_type,
    entity_name,
    job_id,
    job_run_id,
    notebook_path,
    cluster_id,
    compute_type,
    compute_size,
    node_type,
    run_as_user,
    start_time,
    end_time,
    duration_minutes,
    duration_hours,
    total_dbus,
    cost_usd
FROM (
    -- JOBS
    SELECT
        'JOB' AS workload_type,
        COALESCE(U.usage_metadata.job_name, CAST(U.usage_metadata.job_id AS STRING)) AS entity_name,
        U.usage_metadata.job_id AS job_id,
        U.usage_metadata.job_run_id AS job_run_id,
        U.usage_metadata.notebook_path AS notebook_path,
        U.usage_metadata.cluster_id AS cluster_id,
        CASE WHEN U.product_features.is_serverless THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        CASE
            WHEN U.product_features.is_serverless THEN 'SERVERLESS'
            WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
            WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
            WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
            WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
            WHEN U.usage_metadata.node_type LIKE '%E48%' THEN '3XL'
            WHEN U.usage_metadata.node_type LIKE '%E64%' THEN '4XL'
            ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
        END AS compute_size,
        U.usage_metadata.node_type AS node_type,
        U.identity_metadata.run_as AS run_as_user,
        MIN(U.usage_start_time) AS start_time,
        MAX(U.usage_end_time) AS end_time,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 3600.0, 2) AS duration_hours,
        ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
        ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd
    FROM system.billing.usage U
    INNER JOIN system.billing.list_prices P 
        ON U.cloud = P.cloud AND U.sku_name = P.sku_name
        AND U.usage_start_time >= P.price_start_time
        AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
        AND U.billing_origin_product = 'JOBS'
        AND U.usage_metadata.job_id IS NOT NULL
    GROUP BY
        U.usage_metadata.job_id,
        U.usage_metadata.job_run_id,
        U.usage_metadata.job_name,
        U.usage_metadata.notebook_path,
        U.usage_metadata.cluster_id,
        U.product_features.is_serverless,
        U.usage_metadata.node_type,
        U.identity_metadata.run_as

    UNION ALL

    -- NOTEBOOKS (All-Purpose)
    SELECT
        'NOTEBOOK' AS workload_type,
        COALESCE(U.usage_metadata.notebook_path, 'Unknown Notebook') AS entity_name,
        NULL AS job_id,
        NULL AS job_run_id,
        U.usage_metadata.notebook_path AS notebook_path,
        U.usage_metadata.cluster_id AS cluster_id,
        CASE WHEN U.product_features.is_serverless THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        CASE
            WHEN U.product_features.is_serverless THEN 'SERVERLESS'
            WHEN U.usage_metadata.node_type LIKE '%E4%' OR U.usage_metadata.node_type LIKE '%DS3%' THEN 'M'
            WHEN U.usage_metadata.node_type LIKE '%E8%' OR U.usage_metadata.node_type LIKE '%DS4%' THEN 'L'
            WHEN U.usage_metadata.node_type LIKE '%E16%' OR U.usage_metadata.node_type LIKE '%DS5%' THEN 'XL'
            WHEN U.usage_metadata.node_type LIKE '%E32%' OR U.usage_metadata.node_type LIKE '%DS12%' THEN '2XL'
            WHEN U.usage_metadata.node_type LIKE '%E48%' THEN '3XL'
            WHEN U.usage_metadata.node_type LIKE '%E64%' THEN '4XL'
            ELSE COALESCE(U.usage_metadata.node_type, 'UNKNOWN')
        END AS compute_size,
        U.usage_metadata.node_type AS node_type,
        U.identity_metadata.run_as AS run_as_user,
        MIN(U.usage_start_time) AS start_time,
        MAX(U.usage_end_time) AS end_time,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 3600.0, 2) AS duration_hours,
        ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
        ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd
    FROM system.billing.usage U
    INNER JOIN system.billing.list_prices P 
        ON U.cloud = P.cloud AND U.sku_name = P.sku_name
        AND U.usage_start_time >= P.price_start_time
        AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
        AND (U.billing_origin_product = 'ALL_PURPOSE' OR U.sku_name LIKE '%ALL_PURPOSE%')
    GROUP BY
        U.usage_metadata.notebook_path,
        U.usage_metadata.cluster_id,
        U.product_features.is_serverless,
        U.usage_metadata.node_type,
        U.identity_metadata.run_as
) combined
ORDER BY duration_minutes DESC
LIMIT 10000;


-- ============================================================================
-- QUERY 4: LONG RUNNING JOBS (> 1 hour)
-- Find jobs that took more than 60 minutes
-- ============================================================================
SELECT
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_run_id AS job_run_id,
    U.usage_metadata.job_name AS job_name,
    U.usage_metadata.notebook_path AS notebook_path,
    U.usage_metadata.cluster_id AS cluster_id,
    CASE WHEN U.product_features.is_serverless THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
    U.usage_metadata.node_type AS node_type,
    U.identity_metadata.run_as AS run_as_user,
    MIN(U.usage_start_time) AS start_time,
    MAX(U.usage_end_time) AS end_time,
    ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
    ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 3600.0, 2) AS duration_hours,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd
FROM system.billing.usage U
INNER JOIN system.billing.list_prices P 
    ON U.cloud = P.cloud AND U.sku_name = P.sku_name
    AND U.usage_start_time >= P.price_start_time
    AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND U.billing_origin_product = 'JOBS'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY
    U.usage_metadata.job_id,
    U.usage_metadata.job_run_id,
    U.usage_metadata.job_name,
    U.usage_metadata.notebook_path,
    U.usage_metadata.cluster_id,
    U.product_features.is_serverless,
    U.usage_metadata.node_type,
    U.identity_metadata.run_as
HAVING 
    (UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0 > 60
ORDER BY duration_minutes DESC;


-- ============================================================================
-- QUERY 5: TOP EXPENSIVE JOBS BY COST
-- Jobs sorted by cost
-- ============================================================================
SELECT
    U.usage_metadata.job_id AS job_id,
    U.usage_metadata.job_name AS job_name,
    COUNT(DISTINCT U.usage_metadata.job_run_id) AS total_runs,
    U.usage_metadata.notebook_path AS notebook_path,
    CASE WHEN MAX(CASE WHEN U.product_features.is_serverless THEN 1 ELSE 0 END) = 1 THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
    MIN(U.usage_start_time) AS first_run,
    MAX(U.usage_end_time) AS last_run,
    ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
    ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS total_cost_usd,
    ROUND(SUM(U.usage_quantity * P.pricing.default) / COUNT(DISTINCT U.usage_metadata.job_run_id), 2) AS avg_cost_per_run
FROM system.billing.usage U
INNER JOIN system.billing.list_prices P 
    ON U.cloud = P.cloud AND U.sku_name = P.sku_name
    AND U.usage_start_time >= P.price_start_time
    AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
WHERE 
    U.workspace_id = '5244115429641560'
    AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND U.billing_origin_product = 'JOBS'
    AND U.usage_metadata.job_id IS NOT NULL
GROUP BY
    U.usage_metadata.job_id,
    U.usage_metadata.job_name,
    U.usage_metadata.notebook_path
ORDER BY total_cost_usd DESC
LIMIT 100;


-- ============================================================================
-- QUERY 6: SUMMARY - JOBS VS NOTEBOOKS COST COMPARISON
-- ============================================================================
SELECT
    workload_type,
    compute_type,
    COUNT(DISTINCT entity_id) AS unique_entities,
    COUNT(*) AS total_runs,
    ROUND(SUM(total_dbus), 2) AS total_dbus,
    ROUND(SUM(cost_usd), 2) AS total_cost_usd,
    ROUND(AVG(duration_minutes), 2) AS avg_duration_minutes
FROM (
    -- Jobs
    SELECT
        'JOB' AS workload_type,
        CASE WHEN U.product_features.is_serverless THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.job_id AS entity_id,
        U.usage_metadata.job_run_id AS run_id,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
        ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
        ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd
    FROM system.billing.usage U
    INNER JOIN system.billing.list_prices P 
        ON U.cloud = P.cloud AND U.sku_name = P.sku_name
        AND U.usage_start_time >= P.price_start_time
        AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
        AND U.billing_origin_product = 'JOBS'
    GROUP BY U.usage_metadata.job_id, U.usage_metadata.job_run_id, U.product_features.is_serverless

    UNION ALL

    -- Notebooks
    SELECT
        'NOTEBOOK' AS workload_type,
        CASE WHEN U.product_features.is_serverless THEN 'SERVERLESS' ELSE 'CLASSIC' END AS compute_type,
        U.usage_metadata.cluster_id AS entity_id,
        CAST(U.usage_date AS STRING) AS run_id,
        ROUND((UNIX_TIMESTAMP(MAX(U.usage_end_time)) - UNIX_TIMESTAMP(MIN(U.usage_start_time))) / 60.0, 2) AS duration_minutes,
        ROUND(SUM(U.usage_quantity), 2) AS total_dbus,
        ROUND(SUM(U.usage_quantity * P.pricing.default), 2) AS cost_usd
    FROM system.billing.usage U
    INNER JOIN system.billing.list_prices P 
        ON U.cloud = P.cloud AND U.sku_name = P.sku_name
        AND U.usage_start_time >= P.price_start_time
        AND (U.usage_end_time <= P.price_end_time OR P.price_end_time IS NULL)
    WHERE 
        U.workspace_id = '5244115429641560'
        AND U.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
        AND (U.billing_origin_product = 'ALL_PURPOSE' OR U.sku_name LIKE '%ALL_PURPOSE%')
    GROUP BY U.usage_metadata.cluster_id, U.usage_date, U.product_features.is_serverless
) summary
GROUP BY workload_type, compute_type
ORDER BY total_cost_usd DESC;
