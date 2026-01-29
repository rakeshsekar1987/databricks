# SQL Query Analysis: Missing Data Investigation

## Overview

This document analyzes why data might be missing from the "Current Query" compared to the "Reference Query".

---

## Key Issues Identified

### 1. **Missing `usage_final` CTE Definition**

**Critical Issue**: Your current query references `FROM usage_final u` but the CTE definition is not shown. This is the most likely source of missing data.

The reference query explicitly defines how usage data is filtered:

```sql
usage_with_restrictions AS (
  SELECT * FROM (
    SELECT t1.*,
      concat_ws(" ",
        CASE WHEN product_features.is_serverless THEN "SERVERLESS" ELSE "" END,
        CASE WHEN billing_origin_product = "JOBS" THEN "JOB" ELSE "PIPELINE" END
      ) as entity_type
    FROM system.billing.usage t1 
    LEFT JOIN system.access.workspaces_latest t2 USING (workspace_id)
    WHERE (
      billing_origin_product IN ("JOBS", "DLT", "LAKEFLOW_CONNECT")
      OR (billing_origin_product = "SQL" AND usage_metadata.dlt_pipeline_id IS NOT NULL)
    )
    -- ... other filters
  )
)
```

**Action Required**: Ensure your `usage_final` CTE includes ALL the same source products:
- `JOBS`
- `DLT`
- `LAKEFLOW_CONNECT`
- `SQL` (when `usage_metadata.dlt_pipeline_id IS NOT NULL`)

---

### 2. **LAKEFLOW_CONNECT Product Missing**

The reference query explicitly includes:
```sql
billing_origin_product IN ("JOBS", "DLT", "LAKEFLOW_CONNECT")
```

**Question**: Does your `usage_final` CTE include `LAKEFLOW_CONNECT`? This is a separate product for Lakeflow data pipelines and connections.

---

### 3. **SQL + DLT Pipeline Data Missing**

The reference query includes a special case:
```sql
OR (billing_origin_product = "SQL" AND usage_metadata.dlt_pipeline_id IS NOT NULL)
```

This captures SQL warehouse usage that's associated with DLT pipelines. If your `usage_final` CTE doesn't include this condition, you'll miss this data.

---

### 4. **Job ID Type Casting Issue**

**Reference Query Join:**
```sql
LEFT JOIN most_recent_jobs t2 ON (
  t1.entity_type LIKE "%JOB%"
  AND t1.workspace_id = t2.workspace_id
  AND t1.entity_id = t2.job_id
)
```

**Current Query Join:**
```sql
LEFT JOIN most_recent_jobs j
  ON u.job_id IS NOT NULL
  AND u.job_id = CAST(j.job_id AS STRING)
```

**Issues:**
1. **Missing `workspace_id` join condition**: The reference query joins on `workspace_id`, which ensures you're matching jobs within the same workspace. Your current query doesn't include this, which could cause:
   - Incorrect matches across workspaces
   - Missing matches if job IDs are workspace-scoped

2. **Type casting direction**: You're casting `j.job_id` to STRING. If `u.job_id` contains values that don't exactly match the string representation (e.g., leading zeros, different formats), joins will fail.

---

### 5. **Pipeline ID Join Missing Workspace Scope**

**Reference Query:**
```sql
LEFT JOIN most_recent_pipelines t3 ON (
  t1.entity_type LIKE "%PIPELINE%"
  AND t1.workspace_id = t3.workspace_id
  AND t1.entity_id = t3.pipeline_id
)
```

**Current Query:**
```sql
LEFT JOIN most_recent_pipelines p
  ON u.dlt_pipeline_id IS NOT NULL
  AND u.dlt_pipeline_id = p.pipeline_id
```

**Missing**: The `workspace_id` join condition. Pipelines should be matched within the same workspace.

---

### 6. **INNER JOIN vs LEFT JOIN for List Prices**

The reference query uses an **INNER JOIN** with `system.billing.list_prices`:

```sql
INNER JOIN system.billing.list_prices list_prices 
  ON t1.cloud = list_prices.cloud
  AND t1.sku_name = list_prices.sku_name
  AND t1.usage_start_time >= list_prices.price_start_time
  AND (t1.usage_end_time <= list_prices.price_end_time OR list_prices.price_end_time IS NULL)
```

This could **exclude** usage records that don't have matching price entries. However, if your current query already has cost data in `usage_final`, this might not apply.

---

### 7. **Entity Type Logic Differences**

**Reference Query** uses a computed `entity_type` field:
```sql
concat_ws(" ",
  CASE WHEN product_features.is_serverless THEN "SERVERLESS" ELSE "" END,
  CASE WHEN billing_origin_product = "JOBS" THEN "JOB" ELSE "PIPELINE" END
) as entity_type
```

Then uses pattern matching for joins:
```sql
t1.entity_type LIKE "%JOB%"
t1.entity_type LIKE "%PIPELINE%"
```

**Current Query** uses separate ID null checks:
```sql
u.job_id IS NOT NULL
u.dlt_pipeline_id IS NOT NULL
```

**Potential Issue**: Some records might have both `job_id` AND `dlt_pipeline_id` (or neither), causing different join behavior.

---

## Recommended Fixes

### Fix 1: Add Workspace ID to Joins

```sql
LEFT JOIN most_recent_jobs j
  ON u.job_id IS NOT NULL
  AND u.workspace_id = j.workspace_id  -- ADD THIS
  AND u.job_id = CAST(j.job_id AS STRING)

LEFT JOIN most_recent_pipelines p
  ON u.dlt_pipeline_id IS NOT NULL
  AND u.workspace_id = p.workspace_id  -- ADD THIS
  AND u.dlt_pipeline_id = p.pipeline_id
```

### Fix 2: Verify `usage_final` CTE Includes All Products

Ensure your CTE definition includes:
```sql
WHERE billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
   OR (billing_origin_product = 'SQL' AND usage_metadata.dlt_pipeline_id IS NOT NULL)
```

### Fix 3: Verify Type Compatibility

Check that `job_id` types are consistent:
```sql
-- Debug query to check types
SELECT 
  typeof(u.job_id) as usage_job_id_type,
  typeof(j.job_id) as jobs_job_id_type,
  u.job_id,
  j.job_id,
  CAST(j.job_id AS STRING) as casted_job_id
FROM usage_final u
LEFT JOIN most_recent_jobs j ON u.workspace_id = j.workspace_id
LIMIT 10;
```

### Fix 4: Add Cluster/Warehouse Join Conditions for Workspace

```sql
LEFT JOIN most_recent_clusters c 
  ON u.cluster_id = c.cluster_id
  AND u.workspace_id = c.workspace_id  -- ADD if clusters are workspace-scoped

LEFT JOIN warehouse_info wh
  ON u.warehouse_id IS NOT NULL
  AND u.warehouse_id = wh.warehouse_id
  AND u.workspace_id = wh.workspace_id  -- ADD if warehouses are workspace-scoped
```

---

## Debugging Queries

### Count Comparison by Product Type

Run this against your `usage_final` to compare with reference:

```sql
-- What products are in your usage_final?
SELECT 
  billing_origin_product,
  COUNT(*) as record_count
FROM usage_final
GROUP BY billing_origin_product
ORDER BY record_count DESC;

-- Compare with source data
SELECT 
  billing_origin_product,
  COUNT(*) as record_count
FROM system.billing.usage
WHERE usage_date BETWEEN :start_date AND :end_date
  AND (
    billing_origin_product IN ('JOBS', 'DLT', 'LAKEFLOW_CONNECT')
    OR (billing_origin_product = 'SQL' AND usage_metadata.dlt_pipeline_id IS NOT NULL)
  )
GROUP BY billing_origin_product
ORDER BY record_count DESC;
```

### Find Orphaned Records (Jobs without matches)

```sql
SELECT 
  u.job_id,
  u.workspace_id,
  j.job_id as matched_job_id
FROM usage_final u
LEFT JOIN most_recent_jobs j
  ON u.job_id = CAST(j.job_id AS STRING)
WHERE u.job_id IS NOT NULL
  AND j.job_id IS NULL;
```

---

## Summary of Most Likely Causes

| Priority | Issue | Impact |
|----------|-------|--------|
| 1 | Missing `LAKEFLOW_CONNECT` in usage_final | Missing entire product category |
| 2 | Missing `SQL` + DLT condition | Missing SQL warehouse DLT usage |
| 3 | Missing `workspace_id` in joins | Wrong or missing job/pipeline matches |
| 4 | Type casting issues on job_id | Failed joins for some records |

---

## Next Steps

1. Share the `usage_final` CTE definition so I can verify the filtering logic
2. Run the debugging queries above to quantify the missing data
3. Apply the recommended fixes to the join conditions
