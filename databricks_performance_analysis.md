# Databricks Notebook Performance Analysis

## Executive Summary
The notebook is taking 7+ hours to complete, with two specific operations each consuming ~3 hours 50 minutes:
1. **CDC subtract operation** - Finding delta/new records
2. **Delta table append operation** - Writing new records

## Root Cause Analysis

### Issue #1: The `subtract()` Operation (3+ hours)

```python
exceptions_details_byfiling_df = exceptions_details_byfiling_df.subtract(
    exceptions_details_byfiling_prev_df.select(exceptions_details_byfiling_df.columns)
)
exceptions_details_byfiling_df_count = exceptions_details_byfiling_df.count()
```

**Why this is slow:**
1. **Full Shuffle Required**: `subtract()` requires shuffling ALL data from both DataFrames across the cluster
2. **Row-by-Row Comparison**: Compares every single column in every row
3. **No Indexing**: Unlike database operations, there's no index to speed up the comparison
4. **Data Size**: If the previous table has millions of rows, this becomes O(n*m) complexity
5. **The `count()` action**: Forces materialization of the entire subtract operation

### Issue #2: The Append Delta Operation (3+ hours)

```python
append_delta(exceptions_details_byfiling_df, exception_details_table_loc)
```

**Why this is slow:**
1. **Lazy Evaluation Chain**: The entire transformation pipeline is re-executed during write
2. **No Caching**: The DataFrame isn't cached before count() and write, causing double computation
3. **No Partitioning**: Writing without partition optimization
4. **MergeSchema**: The `mergeSchema` option adds overhead

### Additional Performance Issues Found

#### 1. Multiple Expensive Joins in `dms_exception_table_gen()` and `rrms_exception_table_gen()`
- Complex join conditions using `expr()` with regex operations
- No broadcast hints for smaller tables
- Multiple `persist()` calls without strategic `unpersist()`

#### 2. Python UDF Bottleneck
```python
getexceptionrecordid_udf = udf(getexceptionrecordid, StringType())
```
- Python UDFs serialize data row-by-row between JVM and Python
- This is orders of magnitude slower than native Spark functions

#### 3. Inefficient `drop_duplicates()`
```python
exceptions_details_byfiling_df = exceptions_details_byfiling_df.drop_duplicates()
```
- Called on the full DataFrame with all columns
- Requires full shuffle

#### 4. No Partition Pruning
```sql
select * from {}_xform.{}_eyc_exceptions_details
```
- Reads the entire table without any partition filters

#### 5. Chained Window Operations
Multiple `row_number().over(Window.partitionBy(...))` operations without intermediate caching

---

## Recommended Solutions

### Solution 1: Replace `subtract()` with Anti-Join on Key Columns

Instead of comparing ALL columns, identify unique key columns and use a left anti-join:

```python
# Define key columns that uniquely identify a record
key_columns = ["datasetruleid", "ruleexceptionsid", "filenamealias", "auditingts"]

# Use left anti-join instead of subtract
exceptions_details_byfiling_df_new = exceptions_details_byfiling_df.alias("new").join(
    exceptions_details_byfiling_prev_df.select(key_columns).alias("prev"),
    on=key_columns,
    how="left_anti"
)
```

**Expected improvement: 80-90% reduction in time**

### Solution 2: Cache Before Count and Write

```python
# Cache the DataFrame after subtract/anti-join
exceptions_details_byfiling_df_new.cache()

# Now count (triggers caching)
exceptions_details_byfiling_df_count = exceptions_details_byfiling_df_new.count()

# Write uses cached data (no recomputation)
if exceptions_details_byfiling_df_count > 0:
    append_delta(exceptions_details_byfiling_df_new, exception_details_table_loc)

# Unpersist when done
exceptions_details_byfiling_df_new.unpersist()
```

### Solution 3: Replace Python UDF with Native Spark

```python
from pyspark.sql.functions import from_json, transform, sha2, concat_ws, struct, to_json

# Replace the Python UDF with native Spark functions
def get_exception_recordid_native(df):
    return df.withColumn(
        "rulesqlop",
        when(
            col("rulesqlop").isNotNull() & (col("rulesqlop") != "[]"),
            # Use native JSON functions instead of Python
            transform(
                from_json(col("rulesqlop"), ArrayType(MapType(StringType(), StringType()))),
                lambda x: when(
                    x["auditrecordidhash"].isNotNull(),
                    map_concat(
                        x,
                        create_map(
                            lit("auditexceptionrecordid"),
                            sha2(concat_ws("||", col("datasetruleid"), x["auditrecordidhash"]), 256)
                        )
                    )
                ).otherwise(x)
            )
        ).otherwise(col("rulesqlop"))
    )
```

### Solution 4: Add Broadcast Hints for Small Tables

```python
from pyspark.sql.functions import broadcast

# For small lookup tables (< 10MB)
fil_inv_sftp_audit_validation_df = files_received_df.alias('f').join(
    broadcast(audit_validation_df_sub.alias('i')),  # Add broadcast
    joinexpr,
    how="left"
)
```

### Solution 5: Optimize Delta Table with Z-Ordering

```sql
OPTIMIZE {client_nm}_xform.{engagement_nm}_eyc_exceptions_details
ZORDER BY (datasetruleid, auditingts)
```

### Solution 6: Use Incremental Processing with Watermarks

```python
# Only read recent data from the previous table
cutoff_date = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
exceptions_details_byfiling_prev_df = spark.sql(f"""
    SELECT * FROM {client_nm}_xform.{engagement_nm}_eyc_exceptions_details
    WHERE auditingdt >= '{cutoff_date}'
""")
```

### Solution 7: Partition the Target Table

```python
# Write with partitioning
df.write.format('delta')\
    .partitionBy("yearmonth")\
    .mode('append')\
    .save(location)
```

---

## Quick Wins (Implement First)

1. **Add caching before count/write** - Immediate 50% improvement
2. **Replace subtract with anti-join** - 80-90% improvement on CDC
3. **Add partition filter when reading previous data** - Significant I/O reduction

## Implementation Priority

| Priority | Change | Expected Improvement | Effort |
|----------|--------|---------------------|--------|
| 1 | Replace `subtract()` with anti-join | 80-90% | Low |
| 2 | Cache before count/write | 50% | Low |
| 3 | Add date filter to prev_df query | 30-50% | Low |
| 4 | Replace Python UDF | 20-40% | Medium |
| 5 | Add broadcast hints | 10-20% | Low |
| 6 | Optimize Delta table | 10-15% | Low |
