# Critical Fix: CartesianProduct (Cross Join) Issue

## Problem Identified

The DAG shows **CartesianProduct** operations which are causing the extreme slowdown. These are caused by:

### 1. LIKE-based joins in DMS function (line 268):
```python
joincond = "i.auditsecondaryinternalfilename like concat('%',f.auditsecondaryinternalfilename,'%')"
```

### 2. .contains() joins in RRMS function (line 528):
```python
validation_df.auditsecondaryinternalfilename.contains(fil_inv_sftp_audit_df.auditsecondaryinternalfilename)
```

## Why This Causes CartesianProduct

Spark cannot optimize joins with:
- `LIKE '%value%'` patterns
- `.contains()` operations
- Any non-equality predicates

Instead of using hash-based or sort-merge joins, Spark must do a **nested loop join** (CartesianProduct), comparing every row in table A with every row in table B.

**Math:**
- Table A: 10,000 rows
- Table B: 100,000 rows  
- CartesianProduct: 1,000,000,000 comparisons!

## Solution Options

### Option 1: Pre-compute Join Keys (Recommended)

Create a derived column that can be used for equality joins:

```python
# Instead of LIKE join, extract a join key
# If auditsecondaryinternalfilename always contains the other as a substring,
# we can extract a normalized key

# Example: Extract base filename without path/extensions
from pyspark.sql.functions import regexp_extract

# Create normalized keys on both sides
df1 = df1.withColumn("join_key", regexp_extract(col("auditsecondaryinternalfilename"), r'([^/]+)$', 1))
df2 = df2.withColumn("join_key", regexp_extract(col("auditsecondaryinternalfilename"), r'([^/]+)$', 1))

# Now use equality join
result = df1.join(df2, on="join_key", how="left")
```

### Option 2: Use Broadcast Join for Smaller Table

If one side is small (< 100MB), broadcast it:

```python
from pyspark.sql.functions import broadcast

# Broadcast the smaller table to avoid shuffle
fil_inv_sftp_audit_validation_df = files_received_df.alias('f').join(
    broadcast(audit_validation_df_sub.alias('i')),  # Force broadcast
    expr(joincond),
    how="left"
)
```

**Note:** This still does CartesianProduct but on each executor, reducing network overhead.

### Option 3: Two-Phase Join (Best Performance)

1. First, do an equality join on a common column (like `audittablename`)
2. Then, filter with the LIKE condition

```python
# Phase 1: Equality join on common column (fast, uses hash join)
temp_df = files_received_df.alias('f').join(
    audit_validation_df_sub.alias('i'),
    col("f.audittablename") == col("i.audittablename"),  # Equality!
    how="left"
)

# Phase 2: Filter with LIKE condition (much smaller dataset now)
result = temp_df.filter(
    col("i.auditsecondaryinternalfilename").like(
        concat(lit("%"), col("f.auditsecondaryinternalfilename"), lit("%"))
    )
)
```

### Option 4: Explode and Match (For Complex Patterns)

If the relationship is known (e.g., one field contains multiple values):

```python
# Split the field that contains multiple values
exploded = df.withColumn("file_part", explode(split(col("auditsecondaryinternalfilename"), "/")))

# Now join on exact match
result = df1.join(exploded, df1.auditsecondaryinternalfilename == exploded.file_part)
```

## Additional Issue: Only Driver Executing

The stage shows ALL tasks running on `driver` only:
```
Executor ID: driver
Total Tasks: 9421
```

This suggests the cluster is not properly configured or data is not distributed.

### Fix: Check Cluster Configuration

```python
# Check number of executors
print(f"Executors: {spark.sparkContext.getExecutorMemoryStatus}")

# Force repartition to distribute data
df = df.repartition(200)
```

## Recommended Implementation

```python
# In dms_exception_table_gen function, replace:
# OLD (causes CartesianProduct):
joincond = "i.auditsecondaryinternalfilename like concat('%',f.auditsecondaryinternalfilename,'%')"
fil_inv_sftp_audit_validation_df = files_received_df.alias('f').join(
    audit_validation_df_sub.alias('i'), 
    expr(joincond),
    how="left"
)

# NEW (two-phase join):
# Phase 1: Equality join on audittablename (if exists in both) or use broadcast
temp_df = files_received_df.alias('f').join(
    broadcast(audit_validation_df_sub.alias('i')),
    how="cross"  # Explicit cross since we need LIKE
).filter(
    col("i.auditsecondaryinternalfilename").like(
        concat(lit("%"), col("f.auditsecondaryinternalfilename"), lit("%"))
    )
)
```

## Expected Improvement

| Metric | Before (CartesianProduct) | After (Optimized Join) |
|--------|--------------------------|----------------------|
| Stage 75 Time | 5.8 hours | ~10-30 minutes |
| Tasks | 9,420 sequential | Parallel across executors |
| Join Type | Nested Loop | Hash/Broadcast |
