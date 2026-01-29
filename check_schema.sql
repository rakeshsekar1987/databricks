-- =====================================================================================
-- DIAGNOSTIC QUERIES: Run these to check actual column names in your environment
-- Run each query separately to see the schema of each system table
-- =====================================================================================

-- 1. Check system.lakeflow.jobs columns
DESCRIBE system.lakeflow.jobs;

-- 2. Check system.lakeflow.pipelines columns  
DESCRIBE system.lakeflow.pipelines;

-- 3. Check system.compute.clusters columns
DESCRIBE system.compute.clusters;

-- 4. Check system.compute.warehouses columns
DESCRIBE system.compute.warehouses;

-- 5. Check system.compute.node_types columns
DESCRIBE system.compute.node_types;

-- 6. Check system.billing.usage columns
DESCRIBE system.billing.usage;

-- 7. Check system.billing.list_prices columns
DESCRIBE system.billing.list_prices;

-- 8. Check system.access.workspaces_latest columns
DESCRIBE system.access.workspaces_latest;


-- =====================================================================================
-- SAMPLE DATA QUERIES: Run these to see actual data and column values
-- =====================================================================================

-- Sample jobs data
SELECT * FROM system.lakeflow.jobs 
WHERE workspace_id = 5244115429641560 
LIMIT 5;

-- Sample pipelines data
SELECT * FROM system.lakeflow.pipelines 
WHERE workspace_id = 5244115429641560 
LIMIT 5;

-- Sample clusters data
SELECT * FROM system.compute.clusters 
WHERE workspace_id = 5244115429641560 
LIMIT 5;

-- Sample warehouses data
SELECT * FROM system.compute.warehouses 
WHERE workspace_id = 5244115429641560 
LIMIT 5;

-- Sample node types data
SELECT * FROM system.compute.node_types 
LIMIT 5;

-- Sample usage data for your filters
SELECT * FROM system.billing.usage
WHERE workspace_id = 5244115429641560
  AND usage_date BETWEEN '2025-01-01' AND '2026-01-28'
  AND (
    billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
    OR (billing_origin_product = 'SQL' AND usage_metadata.dlt_pipeline_id IS NOT NULL)
  )
LIMIT 5;
