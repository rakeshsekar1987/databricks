# Azure Databricks Notebook Optimization Context Prompt

> **Purpose**: This document serves as a comprehensive context prompt for optimizing Azure Databricks notebooks. Use this as a reference guide when reviewing and refactoring notebooks for production readiness.

---

## 🤖 AI AGENT CONTEXT PROMPT (COPY THIS FOR CURSOR AI)

**Instructions**: Copy everything between the `===START===` and `===END===` markers below and use it as your system/context prompt when feeding Databricks notebooks to Cursor AI Opus 4.5 for optimization.

===START===

You are an expert Azure Databricks optimization engineer specializing in PySpark, Spark SQL, Delta Lake, and Azure cloud services. Your mission is to transform notebooks into production-ready, optimized code following enterprise best practices.

## YOUR OPTIMIZATION PROCESS

For each notebook:
1. **SCAN** for anti-patterns and issues
2. **ANALYZE** data flow, transformations, and resource usage
3. **IDENTIFY** optimization opportunities by priority
4. **REFACTOR** code systematically with explanations
5. **VALIDATE** completeness and correctness

---

## SPARK CONFIGURATION (Apply These First)

Always add/verify these configurations at notebook start:

```python
# === ESSENTIAL SPARK CONFIGURATIONS ===
# Adaptive Query Execution (CRITICAL)
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.localShuffleReader.enabled", "true")

# Shuffle optimization
spark.conf.set("spark.sql.shuffle.partitions", "auto")  # Or 2-4x cores

# Broadcast threshold (adjust based on cluster memory)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "50MB")

# Delta Lake optimizations
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")

# Photon (if available)
spark.conf.set("spark.databricks.photon.enabled", "true")

# Arrow for Pandas interop
spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
```

---

## CRITICAL ANTI-PATTERNS TO DETECT AND FIX

| Anti-Pattern | Detection | Fix |
|--------------|-----------|-----|
| `df.collect()` on large data | Look for `.collect()` | Use aggregations, `.limit()`, or `.toPandas()` on small data only |
| Python for-loops over rows | `for row in df.collect()` | Use DataFrame transformations, `.withColumn()`, `.select()` |
| Python UDFs | `@udf` decorator | Replace with built-in functions or `@pandas_udf` |
| Multiple `.count()` calls | Multiple `df.count()` | Cache first: `df.cache()`, then count |
| `SELECT *` patterns | Reading all columns | Select only needed columns early |
| Uncached reused DataFrames | Same DF used 2+ times | Add `.cache()` and `.unpersist()` |
| Window without partition | `Window.orderBy()` only | Always use `Window.partitionBy().orderBy()` |
| Hardcoded credentials | Strings with passwords/keys | Use `dbutils.secrets.get()` |
| No error handling | Missing try/except | Add comprehensive error handling |
| repartition before write | `.repartition(n).write` | Use `.coalesce()` or let Delta optimize |

---

## JOIN OPTIMIZATION RULES

```python
# SMALL TABLE (<100MB): Use broadcast
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "key")

# SKEWED DATA: Use salting
from pyspark.sql.functions import concat, lit, floor, rand
num_salts = 10
skewed_df = skewed_df.withColumn("salted_key", 
    concat(col("key"), lit("_"), floor(rand() * num_salts).cast("string")))

# NULL HANDLING: Use null-safe equals
df1.join(df2, df1.key.eqNullSafe(df2.key))

# REPEATED JOINS: Cache intermediate results
temp = df1.join(df2, "key").cache()
result = temp.join(df3, "key")
temp.unpersist()
```

---

## DELTA LAKE PATTERNS

```python
# MERGE (Upsert) - Always prefer over delete+insert
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, path)
delta_table.alias("t").merge(
    source_df.alias("s"),
    "t.id = s.id"
).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

# IDEMPOTENT OVERWRITE - Use replaceWhere
df.write.format("delta").mode("overwrite") \
    .option("replaceWhere", f"date = '{process_date}'").save(path)

# OPTIMIZE writes
df.write.format("delta").mode("append") \
    .option("optimizeWrite", "true").save(path)
```

---

## STREAMING PATTERNS (Auto Loader)

```python
# AUTO LOADER (preferred for file ingestion)
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")  # or parquet, csv
    .option("cloudFiles.schemaLocation", schema_path)
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .load(source_path))

# WRITE with checkpoint
(df.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", checkpoint_path)
    .option("mergeSchema", "true")
    .trigger(availableNow=True)  # For batch-like processing
    .toTable("catalog.schema.table"))

# WATERMARKING for late data
df.withWatermark("event_time", "1 hour")
```

---

## CODE STRUCTURE TEMPLATE

```python
# =============================================================================
# NOTEBOOK: [Name]
# PURPOSE: [Description]
# AUTHOR: [Author] | LAST MODIFIED: [Date]
# =============================================================================

# -----------------------------------------------------------------------------
# SECTION 1: IMPORTS AND CONFIGURATION
# -----------------------------------------------------------------------------
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, when, sum, count, broadcast
from pyspark.sql.types import StructType, StructField, StringType, LongType
from delta.tables import DeltaTable
import logging
from datetime import datetime

# Spark configurations (see above)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# SECTION 2: PARAMETERS AND CONFIGURATION
# -----------------------------------------------------------------------------
dbutils.widgets.text("environment", "dev", "Environment")
dbutils.widgets.text("process_date", "", "Process Date")

ENVIRONMENT = dbutils.widgets.get("environment")
PROCESS_DATE = dbutils.widgets.get("process_date") or datetime.now().strftime("%Y-%m-%d")

CONFIG = {
    "dev": {"catalog": "dev_catalog", "schema": "dev_schema"},
    "prod": {"catalog": "prod_catalog", "schema": "prod_schema"}
}
ENV = CONFIG[ENVIRONMENT]

# -----------------------------------------------------------------------------
# SECTION 3: HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def read_delta_table(table_name: str) -> DataFrame:
    """Read Delta table with error handling."""
    try:
        return spark.table(f"{ENV['catalog']}.{ENV['schema']}.{table_name}")
    except Exception as e:
        logger.error(f"Failed to read {table_name}: {e}")
        raise

def write_delta_table(df: DataFrame, table_name: str, mode: str = "append") -> None:
    """Write to Delta with optimizations."""
    (df.write.format("delta").mode(mode)
        .option("optimizeWrite", "true")
        .saveAsTable(f"{ENV['catalog']}.{ENV['schema']}.{table_name}"))
    logger.info(f"Wrote {df.count()} rows to {table_name}")

# -----------------------------------------------------------------------------
# SECTION 4: DATA TRANSFORMATIONS
# -----------------------------------------------------------------------------
def transform_data(df: DataFrame) -> DataFrame:
    """Apply business transformations."""
    return (df
        .filter(col("status").isNotNull())
        .select("id", "name", "amount", "created_at")
        .withColumn("processed_date", lit(PROCESS_DATE)))

# -----------------------------------------------------------------------------
# SECTION 5: MAIN EXECUTION
# -----------------------------------------------------------------------------
def main():
    logger.info(f"Starting processing for {PROCESS_DATE}")
    
    # Read
    source_df = read_delta_table("source_table")
    
    # Transform
    result_df = transform_data(source_df)
    
    # Write
    write_delta_table(result_df, "target_table")
    
    logger.info("Processing completed successfully")

# Execute
if __name__ == "__main__":
    main()
```

---

## ERROR HANDLING PATTERN

```python
from pyspark.sql.utils import AnalysisException
import time

def retry_with_backoff(func, max_retries=3, base_delay=1.0):
    """Retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {delay}s")
            time.sleep(delay)

def validate_dataframe(df: DataFrame, required_cols: list, min_rows: int = 0) -> bool:
    """Validate DataFrame before processing."""
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    count = df.count()
    if count < min_rows:
        raise ValueError(f"Expected {min_rows}+ rows, got {count}")
    return True
```

---

## SECURITY REQUIREMENTS

```python
# ✅ ALWAYS use secrets
password = dbutils.secrets.get(scope="my-scope", key="db-password")
api_key = dbutils.secrets.get(scope="my-scope", key="api-key")

# ✅ Service principal for Azure
spark.conf.set(f"fs.azure.account.auth.type.{storage}.dfs.core.windows.net", "OAuth")
spark.conf.set(f"fs.azure.account.oauth2.client.id.{storage}.dfs.core.windows.net", 
    dbutils.secrets.get("azure", "client-id"))
spark.conf.set(f"fs.azure.account.oauth2.client.secret.{storage}.dfs.core.windows.net",
    dbutils.secrets.get("azure", "client-secret"))

# ❌ NEVER hardcode
# password = "secret123"  # CRITICAL SECURITY ISSUE
```

---

## COMMON TRANSFORMATIONS

```python
# COLUMN OPERATIONS
df = df.select("col1", "col2", "col3")  # Select early
df = df.filter(col("date") >= "2024-01-01")  # Filter on partition first
df = df.withColumn("new_col", when(col("x") > 0, "positive").otherwise("negative"))

# NULL HANDLING
df = df.fillna({"col1": 0, "col2": "unknown"})
df = df.filter(col("required_col").isNotNull())
df = df.withColumn("safe_col", coalesce(col("col1"), col("col2"), lit(0)))

# TYPE CASTING
df = df.withColumn("amount", col("amount").cast("decimal(18,2)"))
df = df.withColumn("event_date", to_date(col("date_str"), "yyyy-MM-dd"))
df = df.withColumn("event_ts", to_timestamp(col("ts_str"), "yyyy-MM-dd HH:mm:ss"))

# JSON PARSING
from pyspark.sql.functions import from_json, get_json_object
schema = StructType([StructField("name", StringType()), StructField("value", LongType())])
df = df.withColumn("parsed", from_json(col("json_col"), schema))
df = df.select("id", col("parsed.name"), col("parsed.value"))

# AGGREGATIONS
df = df.groupBy("category").agg(
    sum("amount").alias("total"),
    count("*").alias("count"),
    avg("amount").alias("average")
)

# WINDOW FUNCTIONS (always partition!)
from pyspark.sql.window import Window
window = Window.partitionBy("customer_id").orderBy("transaction_date")
df = df.withColumn("running_total", sum("amount").over(window))
df = df.withColumn("row_num", row_number().over(window))
```

---

## OUTPUT FORMAT REQUIREMENTS

When analyzing and optimizing a notebook, provide:

### 1. ANALYSIS REPORT
```
## Issues Found

| # | Severity | Issue | Location | Impact |
|---|----------|-------|----------|--------|
| 1 | CRITICAL | collect() on large DataFrame | Cell 5 | OOM risk |
| 2 | HIGH | Missing caching for reused DF | Cell 3,7,9 | 3x slower |
| 3 | MEDIUM | Python UDF | Cell 12 | 10x slower |
| 4 | LOW | Missing docstrings | All functions | Maintainability |
```

### 2. OPTIMIZATION SUMMARY
- List specific changes made
- Explain WHY each change improves performance
- Note any assumptions made

### 3. REFACTORED CODE
- Complete, runnable notebook code
- Clear section headers
- Inline comments explaining changes
- Spark configurations at the top

### 4. EXPECTED IMPROVEMENTS
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Runtime | ~30 min | ~8 min | 73% faster |
| Memory | High OOM risk | Stable | Eliminated |
| Cost | $X/run | $Y/run | Z% savings |

### 5. TESTING CHECKLIST
- [ ] Verify row counts match
- [ ] Check data quality metrics
- [ ] Compare sample outputs
- [ ] Test with edge cases
- [ ] Validate in non-prod first

---

## PRIORITY ORDER

Always optimize in this order:
1. **CRITICAL**: Security issues, OOM risks, data correctness
2. **HIGH**: Performance bottlenecks, anti-patterns
3. **MEDIUM**: Code structure, error handling
4. **LOW**: Documentation, naming conventions

---

## CONTEXT QUESTIONS

Before optimizing, identify:
- What does this notebook do? (ETL/ML/Analytics/Streaming)
- Input data size? (GB/TB)
- Output data size?
- How often does it run? (hourly/daily/weekly)
- Current runtime and issues?
- Cluster configuration? (workers, memory, Photon)
- Unity Catalog? (yes/no)
- Batch or streaming?

===END===

---

## 🎯 OPTIMIZATION OBJECTIVES

When optimizing a Databricks notebook, focus on these key objectives:
1. **Performance**: Reduce execution time and resource consumption
2. **Reliability**: Ensure fault tolerance and idempotency
3. **Maintainability**: Improve code readability and modularity
4. **Scalability**: Handle growing data volumes efficiently
5. **Cost Efficiency**: Optimize cluster and storage costs
6. **Security**: Implement proper access controls and secrets management

---

## 📋 OPTIMIZATION CHECKLIST

### Phase 1: Code Analysis
- [ ] Identify anti-patterns and inefficient operations
- [ ] Review data flow and transformations
- [ ] Analyze shuffle operations and joins
- [ ] Check for redundant computations
- [ ] Evaluate error handling coverage

### Phase 2: Performance Optimization
- [ ] Optimize Spark configurations
- [ ] Implement proper partitioning strategy
- [ ] Add caching where beneficial
- [ ] Optimize joins (broadcast, sort-merge)
- [ ] Enable predicate pushdown

### Phase 3: Code Refactoring
- [ ] Modularize into reusable functions
- [ ] Add proper error handling
- [ ] Implement logging
- [ ] Add documentation and type hints
- [ ] Follow naming conventions

### Phase 4: Production Readiness
- [ ] Implement idempotency
- [ ] Add retry logic
- [ ] Configure monitoring
- [ ] Set up alerting
- [ ] Prepare for CI/CD

---

## 1️⃣ SPARK CONFIGURATION OPTIMIZATION

### Critical Spark Configurations

```python
# Memory and Execution Settings
spark.conf.set("spark.sql.shuffle.partitions", "auto")  # Or calculate based on data size
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
spark.conf.set("spark.sql.adaptive.localShuffleReader.enabled", "true")

# Broadcast Join Threshold (default 10MB, adjust based on cluster memory)
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "50MB")

# Delta Lake Optimizations
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")

# Photon Acceleration (if available)
spark.conf.set("spark.databricks.photon.enabled", "true")
```

### Configuration Guidelines

| Configuration | Recommended Value | Use Case |
|---------------|-------------------|----------|
| `shuffle.partitions` | 2-4x number of cores | Large shuffles |
| `autoBroadcastJoinThreshold` | 10MB-100MB | Small dimension tables |
| `adaptive.enabled` | true | Always enable |
| `delta.optimizeWrite.enabled` | true | Delta tables |

---

## 2️⃣ PARTITIONING STRATEGIES

### When to Use Repartition vs Coalesce

```python
# ❌ AVOID: Repartition before write (causes full shuffle)
df.repartition(100).write.parquet(path)

# ✅ BETTER: Use coalesce to reduce partitions (no shuffle)
df.coalesce(10).write.parquet(path)

# ✅ BEST: Let Delta Lake optimize writes
df.write.format("delta").mode("overwrite").save(path)

# ✅ Use repartition for skewed data redistribution
df.repartition(col("partition_key")).write.partitionBy("partition_key").format("delta").save(path)
```

### Partition Strategy by Data Size

| Data Size | Recommended Partitions | Target File Size |
|-----------|----------------------|------------------|
| < 1 GB | 1-4 | 128 MB |
| 1-10 GB | 8-32 | 128-256 MB |
| 10-100 GB | 32-128 | 256-512 MB |
| > 100 GB | 128-1000 | 512 MB - 1 GB |

### Physical Partitioning (Write-time)

```python
# ✅ Partition by low-cardinality columns (date, region, etc.)
df.write \
    .format("delta") \
    .partitionBy("year", "month") \
    .mode("overwrite") \
    .save("/mnt/data/sales")

# ❌ AVOID: High-cardinality partition columns
# This creates millions of small files
df.write.partitionBy("customer_id").save(path)  # BAD!
```

---

## 3️⃣ CACHING AND PERSISTENCE

### When to Cache

```python
# ✅ Cache when DataFrame is used multiple times
df = spark.read.parquet(path)
df.cache()  # or df.persist(StorageLevel.MEMORY_AND_DISK)

# Use the cached DataFrame
result1 = df.filter(col("status") == "active").count()
result2 = df.groupBy("category").agg(sum("amount"))
result3 = df.join(other_df, "id")

# ✅ Always unpersist when done
df.unpersist()
```

### Caching Decision Matrix

| Scenario | Should Cache? | Reason |
|----------|---------------|--------|
| Used once | ❌ No | Wastes memory |
| Used 2+ times | ✅ Yes | Avoids recomputation |
| Large DataFrame (>50% cluster memory) | ⚠️ Partial | Use MEMORY_AND_DISK |
| Streaming data | ❌ No | Data changes constantly |
| After expensive transformation | ✅ Yes | Preserve computation |

### Persistence Levels

```python
from pyspark import StorageLevel

# Memory only (fastest, may spill)
df.persist(StorageLevel.MEMORY_ONLY)

# Memory and disk (recommended for large datasets)
df.persist(StorageLevel.MEMORY_AND_DISK)

# Disk only (slowest, for very large datasets)
df.persist(StorageLevel.DISK_ONLY)

# Serialized (uses less memory, more CPU)
df.persist(StorageLevel.MEMORY_ONLY_SER)
```

---

## 4️⃣ JOIN OPTIMIZATION

### Join Type Selection

```python
# ✅ Broadcast join for small tables (< 100MB)
from pyspark.sql.functions import broadcast

large_df.join(broadcast(small_df), "key")

# ✅ Sort-merge join for large tables (both > 100MB)
# Ensure both tables are bucketed on join key
large_df1.join(large_df2, "key")

# ✅ Bucket joins for repeated joins on same key
df.write.bucketBy(100, "key").sortBy("key").saveAsTable("bucketed_table")
```

### Join Anti-Patterns to Avoid

```python
# ❌ AVOID: Cartesian/Cross joins
df1.crossJoin(df2)  # Explodes data

# ❌ AVOID: Joining on nullable columns without null handling
df1.join(df2, df1.key == df2.key)  # May produce unexpected results

# ✅ BETTER: Handle nulls explicitly
df1.join(df2, df1.key.eqNullSafe(df2.key))

# ❌ AVOID: Multiple joins on same key without caching
result = df1.join(df2, "key").join(df3, "key").join(df4, "key")

# ✅ BETTER: Cache intermediate results
temp = df1.join(df2, "key").cache()
result = temp.join(df3, "key").join(df4, "key")
temp.unpersist()
```

### Data Skew Handling

```python
# Detect skew
df.groupBy("key").count().orderBy(col("count").desc()).show(20)

# ✅ Salting technique for skewed joins
from pyspark.sql.functions import concat, lit, rand, floor

num_salts = 10

# Salt the skewed table
skewed_df = skewed_df.withColumn(
    "salted_key",
    concat(col("key"), lit("_"), floor(rand() * num_salts).cast("string"))
)

# Explode the smaller table
small_df_exploded = small_df.crossJoin(
    spark.range(num_salts).withColumnRenamed("id", "salt")
).withColumn(
    "salted_key",
    concat(col("key"), lit("_"), col("salt").cast("string"))
)

# Join on salted key
result = skewed_df.join(small_df_exploded, "salted_key")
```

---

## 5️⃣ DELTA LAKE OPTIMIZATION

### Essential Delta Operations

```python
# ✅ OPTIMIZE: Compact small files
spark.sql("OPTIMIZE delta.`/path/to/table`")

# ✅ OPTIMIZE with Z-ORDER for query patterns
spark.sql("""
    OPTIMIZE delta.`/path/to/table`
    ZORDER BY (frequently_filtered_column, join_column)
""")

# ✅ VACUUM: Remove old files (default 7 days retention)
spark.sql("VACUUM delta.`/path/to/table` RETAIN 168 HOURS")

# ✅ ANALYZE: Update table statistics for query optimization
spark.sql("ANALYZE TABLE delta.`/path/to/table` COMPUTE STATISTICS FOR ALL COLUMNS")
```

### Delta Table Properties

```python
# Create optimized Delta table
spark.sql("""
    CREATE TABLE IF NOT EXISTS catalog.schema.table_name (
        id BIGINT,
        name STRING,
        created_date DATE,
        amount DECIMAL(18,2)
    )
    USING DELTA
    PARTITIONED BY (created_date)
    TBLPROPERTIES (
        'delta.autoOptimize.optimizeWrite' = 'true',
        'delta.autoOptimize.autoCompact' = 'true',
        'delta.deletedFileRetentionDuration' = 'interval 7 days',
        'delta.logRetentionDuration' = 'interval 30 days',
        'delta.targetFileSize' = '134217728'  -- 128 MB
    )
""")
```

### Liquid Clustering (Databricks Runtime 13.3+)

```python
# ✅ Modern alternative to partitioning and Z-ordering
spark.sql("""
    CREATE TABLE catalog.schema.table_name
    USING DELTA
    CLUSTER BY (frequently_filtered_column)
    AS SELECT * FROM source_table
""")

# Trigger clustering optimization
spark.sql("OPTIMIZE catalog.schema.table_name")
```

### Merge (Upsert) Optimization

```python
from delta.tables import DeltaTable

# ✅ Optimized MERGE pattern
delta_table = DeltaTable.forPath(spark, "/path/to/table")

delta_table.alias("target").merge(
    updates_df.alias("source"),
    "target.id = source.id"
).whenMatchedUpdate(
    condition="source.updated_at > target.updated_at",
    set={
        "name": "source.name",
        "amount": "source.amount",
        "updated_at": "source.updated_at"
    }
).whenNotMatchedInsertAll(
).execute()

# ✅ Use partition pruning in merge condition
# Add partition column to merge condition when possible
```

---

## 6️⃣ COLUMN PRUNING AND PREDICATE PUSHDOWN

### Best Practices

```python
# ❌ AVOID: Reading all columns
df = spark.read.parquet(path)
result = df.filter(col("status") == "active").select("id", "name")

# ✅ BETTER: Select columns early
df = spark.read.parquet(path).select("id", "name", "status")
result = df.filter(col("status") == "active")

# ✅ BEST: Filter on partition columns first
df = spark.read.parquet(path) \
    .filter(col("date") >= "2024-01-01") \  # Partition filter
    .filter(col("status") == "active") \     # Regular filter
    .select("id", "name")
```

### Verify Predicate Pushdown

```python
# Check if predicates are pushed down
df = spark.read.parquet(path).filter(col("date") == "2024-01-01")
df.explain(True)  # Look for "PushedFilters" in the plan
```

---

## 7️⃣ UDF OPTIMIZATION

### Avoid Python UDFs When Possible

```python
# ❌ AVOID: Python UDFs (slow, require serialization)
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType

@udf(StringType())
def clean_text(text):
    return text.strip().lower()

df.withColumn("cleaned", clean_text(col("text")))

# ✅ BETTER: Use built-in Spark functions
from pyspark.sql.functions import lower, trim

df.withColumn("cleaned", lower(trim(col("text"))))
```

### When UDFs Are Necessary

```python
# ✅ Use Pandas UDFs (vectorized, much faster)
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import StringType
import pandas as pd

@pandas_udf(StringType())
def clean_text_pandas(s: pd.Series) -> pd.Series:
    return s.str.strip().str.lower()

df.withColumn("cleaned", clean_text_pandas(col("text")))

# ✅ Use Arrow for better performance
spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
```

---

## 8️⃣ CODE STRUCTURE AND MODULARITY

### Notebook Organization Template

```python
# =============================================================================
# NOTEBOOK: [Notebook Name]
# PURPOSE: [Brief description]
# AUTHOR: [Author Name]
# LAST MODIFIED: [Date]
# =============================================================================

# -----------------------------------------------------------------------------
# SECTION 1: IMPORTS AND CONFIGURATION
# -----------------------------------------------------------------------------
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, when, sum, count
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from delta.tables import DeltaTable
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# SECTION 2: CONFIGURATION AND PARAMETERS
# -----------------------------------------------------------------------------
# Use widgets for parameterization
dbutils.widgets.text("environment", "dev", "Environment")
dbutils.widgets.text("process_date", "", "Process Date")

ENVIRONMENT = dbutils.widgets.get("environment")
PROCESS_DATE = dbutils.widgets.get("process_date") or datetime.now().strftime("%Y-%m-%d")

# Environment-specific configurations
CONFIG = {
    "dev": {
        "catalog": "dev_catalog",
        "schema": "dev_schema",
        "storage_path": "/mnt/dev/data"
    },
    "prod": {
        "catalog": "prod_catalog",
        "schema": "prod_schema",
        "storage_path": "/mnt/prod/data"
    }
}

ENV_CONFIG = CONFIG[ENVIRONMENT]

# -----------------------------------------------------------------------------
# SECTION 3: HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def read_source_data(spark: SparkSession, path: str, schema: StructType = None) -> DataFrame:
    """
    Read source data with optional schema enforcement.
    
    Args:
        spark: SparkSession instance
        path: Path to source data
        schema: Optional schema for data validation
    
    Returns:
        DataFrame with source data
    """
    try:
        reader = spark.read.format("delta")
        if schema:
            reader = reader.schema(schema)
        return reader.load(path)
    except Exception as e:
        logger.error(f"Failed to read data from {path}: {e}")
        raise

def apply_transformations(df: DataFrame) -> DataFrame:
    """
    Apply business transformations to the DataFrame.
    
    Args:
        df: Input DataFrame
    
    Returns:
        Transformed DataFrame
    """
    return (df
        .filter(col("status").isNotNull())
        .withColumn("processed_at", lit(datetime.now()))
        .withColumn("amount_category", 
            when(col("amount") < 100, "small")
            .when(col("amount") < 1000, "medium")
            .otherwise("large")
        )
    )

def write_to_delta(df: DataFrame, table_path: str, mode: str = "append") -> None:
    """
    Write DataFrame to Delta table with optimizations.
    
    Args:
        df: DataFrame to write
        table_path: Target Delta table path
        mode: Write mode (append, overwrite, merge)
    """
    try:
        (df.write
            .format("delta")
            .mode(mode)
            .option("optimizeWrite", "true")
            .save(table_path)
        )
        logger.info(f"Successfully wrote {df.count()} rows to {table_path}")
    except Exception as e:
        logger.error(f"Failed to write to {table_path}: {e}")
        raise

# -----------------------------------------------------------------------------
# SECTION 4: MAIN PROCESSING LOGIC
# -----------------------------------------------------------------------------
def main():
    """Main processing function."""
    logger.info(f"Starting processing for {PROCESS_DATE} in {ENVIRONMENT}")
    
    # Read data
    source_df = read_source_data(
        spark,
        f"{ENV_CONFIG['storage_path']}/source"
    )
    
    # Transform
    transformed_df = apply_transformations(source_df)
    
    # Write
    write_to_delta(
        transformed_df,
        f"{ENV_CONFIG['storage_path']}/target"
    )
    
    logger.info("Processing completed successfully")

# -----------------------------------------------------------------------------
# SECTION 5: EXECUTION
# -----------------------------------------------------------------------------
if __name__ == "__main__" or dbutils:
    main()
```

---

## 9️⃣ ERROR HANDLING AND RESILIENCE

### Comprehensive Error Handling Pattern

```python
from pyspark.sql.utils import AnalysisException
import time

class DataProcessingError(Exception):
    """Custom exception for data processing errors."""
    pass

def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)

def safe_read_table(spark: SparkSession, table_name: str) -> DataFrame:
    """
    Safely read a table with error handling.
    
    Args:
        spark: SparkSession
        table_name: Full table name
    
    Returns:
        DataFrame if successful
    
    Raises:
        DataProcessingError: If table cannot be read
    """
    try:
        return spark.table(table_name)
    except AnalysisException as e:
        if "Table or view not found" in str(e):
            raise DataProcessingError(f"Table {table_name} does not exist")
        raise DataProcessingError(f"Failed to read {table_name}: {e}")

def validate_dataframe(df: DataFrame, required_columns: list, 
                       min_rows: int = 0) -> bool:
    """
    Validate DataFrame meets requirements.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        min_rows: Minimum number of rows expected
    
    Returns:
        True if valid
    
    Raises:
        DataProcessingError: If validation fails
    """
    # Check columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise DataProcessingError(f"Missing required columns: {missing_cols}")
    
    # Check row count
    row_count = df.count()
    if row_count < min_rows:
        raise DataProcessingError(
            f"DataFrame has {row_count} rows, expected at least {min_rows}"
        )
    
    logger.info(f"Validation passed: {row_count} rows, all columns present")
    return True
```

### Transaction Pattern for Idempotency

```python
def process_with_checkpoint(
    spark: SparkSession,
    source_path: str,
    target_path: str,
    checkpoint_path: str,
    process_date: str
) -> None:
    """
    Process data with checkpoint for idempotency.
    
    Args:
        spark: SparkSession
        source_path: Source data path
        target_path: Target Delta table path
        checkpoint_path: Checkpoint location
        process_date: Date being processed
    """
    checkpoint_file = f"{checkpoint_path}/{process_date}/_SUCCESS"
    
    # Check if already processed
    try:
        dbutils.fs.ls(checkpoint_file)
        logger.info(f"Checkpoint exists for {process_date}, skipping")
        return
    except:
        pass  # Checkpoint doesn't exist, proceed
    
    try:
        # Read and process
        df = spark.read.format("delta").load(source_path)
        transformed_df = apply_transformations(df)
        
        # Write with replace where for idempotency
        (transformed_df.write
            .format("delta")
            .mode("overwrite")
            .option("replaceWhere", f"process_date = '{process_date}'")
            .save(target_path)
        )
        
        # Create checkpoint
        dbutils.fs.put(checkpoint_file, "SUCCESS", overwrite=True)
        logger.info(f"Successfully processed {process_date}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        # Clean up partial data if needed
        raise
```

---

## 🔟 LOGGING AND MONITORING

### Structured Logging Setup

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Structured logger for Databricks notebooks."""
    
    def __init__(self, notebook_name: str, run_id: str = None):
        self.notebook_name = notebook_name
        self.run_id = run_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.logger = logging.getLogger(notebook_name)
        self.logger.setLevel(logging.INFO)
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "notebook": self.notebook_name,
            "run_id": self.run_id,
            "message": message,
            **kwargs
        }
        return json.dumps(log_entry)
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs):
        self.logger.error(self._format_message("ERROR", message, **kwargs))
    
    def metric(self, metric_name: str, value: float, **tags):
        """Log a metric for monitoring."""
        self.info(
            f"METRIC: {metric_name}={value}",
            metric_name=metric_name,
            metric_value=value,
            metric_tags=tags
        )

# Usage
logger = StructuredLogger("sales_pipeline", dbutils.notebook.entry_point.getDbutils().notebook().getContext().currentRunId().toString())

logger.info("Starting pipeline", environment=ENVIRONMENT)
logger.metric("rows_processed", 10000, table="sales")
```

### Performance Monitoring

```python
from contextlib import contextmanager
import time

@contextmanager
def timer(operation_name: str, logger: StructuredLogger):
    """Context manager for timing operations."""
    start = time.time()
    logger.info(f"Starting: {operation_name}")
    try:
        yield
    finally:
        duration = time.time() - start
        logger.metric(f"{operation_name}_duration_seconds", duration)
        logger.info(f"Completed: {operation_name}", duration_seconds=duration)

# Usage
with timer("data_transformation", logger):
    df = apply_transformations(source_df)
```

---

## 1️⃣1️⃣ SECURITY BEST PRACTICES

### Secrets Management

```python
# ✅ Use Databricks secrets for credentials
db_password = dbutils.secrets.get(scope="my-scope", key="db-password")
api_key = dbutils.secrets.get(scope="my-scope", key="api-key")

# ❌ NEVER hardcode credentials
# password = "my-secret-password"  # NEVER DO THIS!

# ✅ Use service principals for Azure resources
storage_account_key = dbutils.secrets.get(scope="azure-secrets", key="storage-key")

# ✅ Unity Catalog for data governance
spark.sql("USE CATALOG production_catalog")
spark.sql("USE SCHEMA sales")
```

### Access Control Patterns

```python
# ✅ Check permissions before operations
def check_table_access(table_name: str) -> bool:
    """Check if current user has access to table."""
    try:
        spark.sql(f"DESCRIBE TABLE {table_name}")
        return True
    except Exception as e:
        if "permission denied" in str(e).lower():
            logger.error(f"Access denied to {table_name}")
            return False
        raise

# ✅ Use row-level security when needed
spark.sql("""
    CREATE OR REPLACE FUNCTION row_filter(region STRING)
    RETURN IF(IS_MEMBER('admin_group'), true, region = current_user_region())
""")
```

---

## 1️⃣2️⃣ TESTING STRATEGIES

### Unit Testing Pattern

```python
# tests/test_transformations.py
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
from your_module import apply_transformations

@pytest.fixture(scope="session")
def spark():
    return SparkSession.builder \
        .master("local[2]") \
        .appName("unit-tests") \
        .getOrCreate()

def test_apply_transformations_filters_nulls(spark):
    """Test that null status records are filtered."""
    schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("status", StringType(), True),
        StructField("amount", IntegerType(), True)
    ])
    
    data = [
        (1, "active", 100),
        (2, None, 200),
        (3, "inactive", 50)
    ]
    
    df = spark.createDataFrame(data, schema)
    result = apply_transformations(df)
    
    assert result.count() == 2
    assert result.filter(col("status").isNull()).count() == 0

def test_apply_transformations_categorizes_amounts(spark):
    """Test amount categorization logic."""
    # ... test implementation
```

### Data Quality Checks

```python
from great_expectations.dataset import SparkDFDataset

def validate_output_data(df: DataFrame) -> dict:
    """
    Validate output data quality.
    
    Args:
        df: DataFrame to validate
    
    Returns:
        Dictionary with validation results
    """
    ge_df = SparkDFDataset(df)
    
    results = {
        "id_not_null": ge_df.expect_column_values_to_not_be_null("id"),
        "amount_positive": ge_df.expect_column_values_to_be_between(
            "amount", min_value=0
        ),
        "status_valid": ge_df.expect_column_values_to_be_in_set(
            "status", ["active", "inactive", "pending"]
        )
    }
    
    all_passed = all(r["success"] for r in results.values())
    
    if not all_passed:
        failed = [k for k, v in results.items() if not v["success"]]
        logger.warning(f"Data quality checks failed: {failed}")
    
    return results
```

---

## 1️⃣3️⃣ CI/CD INTEGRATION

### Notebook Testing in CI/CD

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - develop

stages:
  - stage: Test
    jobs:
      - job: UnitTests
        pool:
          vmImage: 'ubuntu-latest'
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.9'
          
          - script: |
              pip install pytest pyspark delta-spark
              pytest tests/ -v --junitxml=test-results.xml
            displayName: 'Run Unit Tests'
          
          - task: PublishTestResults@2
            inputs:
              testResultsFiles: 'test-results.xml'

  - stage: Deploy
    dependsOn: Test
    jobs:
      - job: DeployNotebooks
        steps:
          - task: DatabricksDeployNotebooks@0
            inputs:
              workspaceUrl: $(DATABRICKS_HOST)
              token: $(DATABRICKS_TOKEN)
              sourcePath: 'notebooks/'
              targetPath: '/Shared/Production/'
```

### Environment Promotion Pattern

```python
# config/environments.py
ENVIRONMENTS = {
    "dev": {
        "catalog": "dev_catalog",
        "schema": "dev_schema",
        "cluster_id": "dev-cluster-id",
        "notifications": ["dev-team@company.com"]
    },
    "staging": {
        "catalog": "staging_catalog",
        "schema": "staging_schema",
        "cluster_id": "staging-cluster-id",
        "notifications": ["qa-team@company.com"]
    },
    "prod": {
        "catalog": "prod_catalog",
        "schema": "prod_schema",
        "cluster_id": "prod-cluster-id",
        "notifications": ["ops-team@company.com", "data-team@company.com"]
    }
}
```

---

## 1️⃣4️⃣ COMMON ANTI-PATTERNS TO AVOID

### Anti-Pattern Checklist

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| `collect()` on large data | OOM errors | Use aggregations, sampling |
| Python loops over rows | Slow, defeats parallelism | Use Spark transformations |
| Multiple `count()` calls | Triggers multiple jobs | Cache DF, count once |
| Reading all columns | Wasted I/O | Select only needed columns |
| UDFs for simple ops | Serialization overhead | Use built-in functions |
| No partition pruning | Full table scans | Filter on partition columns |
| Small file problem | Slow reads | Use OPTIMIZE, autoCompact |
| Uncached repeated reads | Redundant computation | Cache or persist |

### Examples of Anti-Patterns

```python
# ❌ ANTI-PATTERN: Collecting large data
all_data = df.collect()  # DON'T DO THIS!
for row in all_data:
    process(row)

# ✅ SOLUTION: Process in parallel
result = df.rdd.map(lambda row: process(row)).toDF()

# ❌ ANTI-PATTERN: Multiple actions on uncached DF
df = spark.read.parquet(path)
count = df.count()  # Action 1 - reads data
mean = df.agg(avg("amount")).collect()  # Action 2 - reads again
df.write.parquet(output)  # Action 3 - reads again!

# ✅ SOLUTION: Cache before multiple actions
df = spark.read.parquet(path).cache()
count = df.count()
mean = df.agg(avg("amount")).collect()
df.write.parquet(output)
df.unpersist()

# ❌ ANTI-PATTERN: Row-by-row processing
for i in range(df.count()):
    row = df.take(i + 1)[-1]
    # process row

# ✅ SOLUTION: Use DataFrame operations
result = df.withColumn("processed", process_udf(col("data")))
```

---

## 1️⃣5️⃣ PERFORMANCE DIAGNOSTICS

### Spark UI Analysis Checklist

1. **Check Stage Details**
   - Look for skewed tasks (some much longer than others)
   - Check shuffle read/write sizes
   - Identify GC time issues

2. **Analyze SQL Tab**
   - Review physical plan
   - Check for missing predicate pushdown
   - Identify unnecessary shuffles

3. **Monitor Executors**
   - Memory usage
   - Task distribution
   - GC overhead

### Diagnostic Queries

```python
# Check table statistics
spark.sql("DESCRIBE EXTENDED catalog.schema.table").show(100, False)

# Analyze query plan
df.explain(mode="cost")  # Or "formatted" for readable output

# Check partition information
spark.sql("SHOW PARTITIONS catalog.schema.table").show(100, False)

# Check file sizes
display(spark.sql("DESCRIBE DETAIL delta.`/path/to/table`"))
```

---

## 📊 QUICK REFERENCE CARD

### Performance Priorities
1. Enable AQE (Adaptive Query Execution)
2. Use Delta Lake with auto-optimize
3. Partition on low-cardinality columns
4. Cache DataFrames used multiple times
5. Broadcast small tables in joins
6. Avoid Python UDFs (use Pandas UDFs if needed)
7. Select only needed columns early
8. Filter on partition columns first

### Code Quality Priorities
1. Modular functions with docstrings
2. Comprehensive error handling
3. Structured logging
4. Parameter/widget-driven configuration
5. Unit tests for transformations
6. Data quality validations
7. Idempotent processing patterns

### Production Readiness Checklist
- [ ] All configurations externalized
- [ ] Secrets properly managed
- [ ] Error handling complete
- [ ] Logging implemented
- [ ] Monitoring configured
- [ ] Retry logic in place
- [ ] Idempotency ensured
- [ ] Tests passing
- [ ] Documentation complete
- [ ] CI/CD pipeline configured

---

## 🔄 OPTIMIZATION WORKFLOW

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTEBOOK OPTIMIZATION FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ANALYZE                                                      │
│     └─> Read notebook → Identify patterns → Document issues     │
│                                                                  │
│  2. PLAN                                                         │
│     └─> Prioritize fixes → Estimate impact → Create checklist   │
│                                                                  │
│  3. REFACTOR                                                     │
│     └─> Apply Spark optimizations → Restructure code            │
│         → Add error handling → Implement logging                 │
│                                                                  │
│  4. VALIDATE                                                     │
│     └─> Run tests → Compare performance → Verify results        │
│                                                                  │
│  5. DEPLOY                                                       │
│     └─> Create PR → Review → Merge → Monitor production         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 PROMPT TEMPLATE FOR NOTEBOOK OPTIMIZATION

Use this template when starting to optimize a notebook:

```
I need to optimize the following Azure Databricks notebook for production use.

**Current Notebook Context:**
- Purpose: [What the notebook does]
- Data Size: [Approximate input data size]
- Frequency: [How often it runs]
- Current Runtime: [If known]
- Known Issues: [Any specific problems]

**Please analyze and optimize for:**
1. Performance (Spark configuration, joins, caching, partitioning)
2. Delta Lake best practices (OPTIMIZE, Z-ORDER, auto-compact)
3. Code structure (modularization, error handling, logging)
4. Production readiness (idempotency, monitoring, testing)
5. Security (secrets management, access control)

**Specific requirements:**
- Environment: [dev/staging/prod]
- Unity Catalog: [Yes/No]
- Photon: [Enabled/Disabled]
- Cluster Type: [Standard/Photon/Serverless]

Please provide:
1. Analysis of current issues
2. Prioritized optimization recommendations
3. Refactored code with comments
4. Performance improvement estimates
```

---

## 1️⃣6️⃣ STRUCTURED STREAMING & AUTO LOADER

### Auto Loader (Recommended for File Ingestion)

```python
# ✅ Auto Loader with schema evolution
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", "/mnt/schema/orders")
    .option("cloudFiles.inferColumnTypes", "true")
    .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
    .option("cloudFiles.maxFilesPerTrigger", 1000)  # Control batch size
    .load("/mnt/landing/orders/")
)

# Write to Delta with checkpointing
(df.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", "/mnt/checkpoints/orders")
    .option("mergeSchema", "true")
    .trigger(availableNow=True)  # Process all available then stop
    .toTable("catalog.schema.orders")
)
```

### Streaming Trigger Strategies

```python
# ✅ Trigger once for batch-like processing
.trigger(once=True)  # Deprecated

# ✅ Available now (preferred over trigger once)
.trigger(availableNow=True)  # Process all available data, then stop

# ✅ Micro-batch with fixed interval
.trigger(processingTime="5 minutes")

# ✅ Continuous processing (lowest latency)
.trigger(continuous="1 second")  # Experimental
```

### Streaming Optimization Settings

```python
# Streaming-specific configurations
spark.conf.set("spark.databricks.streaming.statefulOperator.asyncCheckpoint.enabled", "true")
spark.conf.set("spark.sql.streaming.stateStore.providerClass", 
               "com.databricks.sql.streaming.state.RocksDBStateStoreProvider")

# Rate limiting for backpressure
spark.conf.set("spark.streaming.backpressure.enabled", "true")
spark.conf.set("spark.sql.streaming.maxBatchesToRetainInMemory", "2")
```

### Watermarking and Late Data

```python
from pyspark.sql.functions import window, col

# ✅ Handle late-arriving data with watermark
df_with_watermark = (df
    .withWatermark("event_time", "1 hour")  # Allow 1 hour late data
    .groupBy(
        window(col("event_time"), "10 minutes"),
        col("category")
    )
    .agg(sum("amount").alias("total_amount"))
)
```

### Streaming State Management

```python
# Monitor streaming query progress
query = df.writeStream.start()

# Check progress
print(query.lastProgress)
print(query.status)

# ✅ State cleanup for aggregations
.withWatermark("timestamp", "1 day")  # Enables state cleanup
```

---

## 1️⃣7️⃣ CLUSTER CONFIGURATION & SIZING

### Cluster Sizing Guidelines

| Workload Type | Recommended Instance | Workers | Notes |
|---------------|---------------------|---------|-------|
| Development | Standard_DS3_v2 | 1-2 | Cost-effective for dev |
| ETL (Small) | Standard_E8s_v3 | 2-4 | Memory-optimized |
| ETL (Large) | Standard_E16s_v3 | 4-16 | Heavy transformations |
| ML Training | Standard_NC6s_v3 | 2-8 | GPU-enabled |
| Streaming | Standard_E8s_v3 | 4-8 | Stable, auto-scale |
| SQL Analytics | Photon-enabled | Auto | Use SQL Warehouses |

### Autoscaling Configuration

```python
# Cluster policy JSON example
{
    "autoscale": {
        "min_workers": 2,
        "max_workers": 10
    },
    "spark_conf": {
        "spark.databricks.cluster.profile": "serverless",
        "spark.databricks.adaptive.autoOptimizeShuffle.enabled": "true"
    },
    "azure_attributes": {
        "spot_bid_max_price": -1,  # Use on-demand price as max
        "first_on_demand": 1,      # Keep driver on-demand
        "availability": "SPOT_WITH_FALLBACK_AZURE"
    },
    "autotermination_minutes": 30,
    "enable_elastic_disk": true
}
```

### Spot Instance Strategy

```python
# ✅ Use spot instances for workers, on-demand for driver
azure_attributes = {
    "first_on_demand": 1,  # Driver on-demand
    "spot_bid_max_price": -1,  # Spot for workers
    "availability": "SPOT_WITH_FALLBACK_AZURE"
}

# ✅ For fault-tolerant workloads
# - ETL with checkpointing
# - Batch processing with retries
# - Non-critical development

# ❌ Avoid spot for
# - Interactive clusters
# - Time-critical production jobs
# - Streaming (unless with strong checkpointing)
```

### Photon Acceleration

```python
# Enable Photon at cluster level (recommended)
# Or per-session:
spark.conf.set("spark.databricks.photon.enabled", "true")
spark.conf.set("spark.databricks.photon.allDataSources.enabled", "true")

# Best for:
# - SQL-heavy workloads
# - Large aggregations
# - Join-intensive queries
# - Parquet/Delta reads

# Not optimal for:
# - UDF-heavy workloads
# - Complex Python transformations
# - Non-SQL operations
```

### Cluster Pools

```python
# Use pools to reduce cluster start time
# Create pool via UI or API

# Benefits:
# - Pre-warmed instances (30s vs 5min start)
# - Cost savings through instance reuse
# - Consistent performance

# Pool sizing:
# min_idle_instances: 2  # Always ready
# max_capacity: 50       # Maximum instances
# idle_instance_autotermination_minutes: 30
```

---

## 1️⃣8️⃣ MEMORY MANAGEMENT & GC TUNING

### Memory Configuration

```python
# Executor memory settings
spark.conf.set("spark.executor.memory", "8g")
spark.conf.set("spark.executor.memoryOverhead", "2g")  # For non-JVM memory
spark.conf.set("spark.driver.memory", "4g")

# Memory fraction tuning
spark.conf.set("spark.memory.fraction", "0.6")  # Total memory for execution + storage
spark.conf.set("spark.memory.storageFraction", "0.5")  # Storage within fraction

# Off-heap memory (for large datasets)
spark.conf.set("spark.memory.offHeap.enabled", "true")
spark.conf.set("spark.memory.offHeap.size", "4g")
```

### Spill Management

```python
# ✅ Detect spill in Spark UI
# Look for "Spill (Memory)" and "Spill (Disk)" in Stage details

# Reduce spill by:
# 1. Increasing executor memory
# 2. Reducing partition size
# 3. Filtering data early
# 4. Using more efficient data types

# ✅ Configure spill compression
spark.conf.set("spark.shuffle.spill.compress", "true")
spark.conf.set("spark.io.compression.codec", "lz4")
```

### Garbage Collection Tuning

```python
# G1GC configuration (recommended for large heaps)
spark.conf.set("spark.executor.extraJavaOptions", 
    "-XX:+UseG1GC -XX:InitiatingHeapOccupancyPercent=35 " +
    "-XX:G1HeapRegionSize=16m -XX:MaxGCPauseMillis=200 " +
    "-XX:+ParallelRefProcEnabled"
)

# Monitor GC
# Check Spark UI > Executors > GC Time
# GC time should be < 5% of total task time

# ✅ Reduce GC pressure
# - Use primitive types over objects
# - Avoid UDFs that create many objects
# - Prefer DataFrame over RDD
# - Use serialized storage levels
```

### Memory-Intensive Operations

```python
# ✅ Handle large aggregations
# Use two-phase aggregation
df.repartition(200).groupBy("key").agg(sum("value"))

# ✅ Large sorts
spark.conf.set("spark.sql.shuffle.partitions", "400")  # More partitions = less memory per partition

# ✅ Large joins
# Use broadcast for small tables
# Salt skewed keys
# Increase shuffle partitions
```

---

## 1️⃣9️⃣ DATA INGESTION PATTERNS

### COPY INTO (Idempotent File Ingestion)

```sql
-- ✅ COPY INTO for batch file loading
COPY INTO catalog.schema.target_table
FROM '/mnt/landing/data/'
FILEFORMAT = PARQUET
FORMAT_OPTIONS ('mergeSchema' = 'true')
COPY_OPTIONS ('mergeSchema' = 'true');

-- ✅ With file filtering
COPY INTO catalog.schema.target_table
FROM '/mnt/landing/data/'
FILEFORMAT = CSV
FORMAT_OPTIONS (
    'header' = 'true',
    'inferSchema' = 'true',
    'delimiter' = ','
)
PATTERN = '*.csv'
COPY_OPTIONS ('force' = 'false');  -- Skip already loaded files
```

### Auto Loader vs COPY INTO Decision Matrix

| Feature | Auto Loader | COPY INTO |
|---------|-------------|-----------|
| Incremental | ✅ Automatic | ✅ Automatic |
| Exactly-once | ✅ Yes | ✅ Yes |
| Streaming support | ✅ Yes | ❌ No |
| Schema evolution | ✅ Automatic | ⚠️ Manual |
| Large file volumes | ✅ Excellent | ⚠️ Limited |
| Directory listing | ✅ Efficient | ❌ Full scan |
| Notifications | ✅ Event-driven | ❌ Polling |
| Best for | High-volume streaming | Periodic batch |

### API Data Ingestion

```python
import requests
from pyspark.sql.types import StructType, StructField, StringType

def fetch_api_data(url: str, headers: dict) -> list:
    """Fetch data from API with retry logic."""
    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

# ✅ Parallelize API calls
api_urls = [f"https://api.example.com/data?page={i}" for i in range(100)]
results = spark.sparkContext.parallelize(api_urls, 10).map(
    lambda url: fetch_api_data(url, {"Authorization": f"Bearer {api_key}"})
).collect()

# Convert to DataFrame
df = spark.createDataFrame(
    [item for sublist in results for item in sublist],
    schema=defined_schema
)
```

### JDBC Data Ingestion

```python
# ✅ Optimized JDBC read with partitioning
jdbc_df = (spark.read
    .format("jdbc")
    .option("url", jdbc_url)
    .option("dbtable", "(SELECT * FROM source_table WHERE date >= '2024-01-01') AS t")
    .option("user", dbutils.secrets.get("db-scope", "username"))
    .option("password", dbutils.secrets.get("db-scope", "password"))
    .option("partitionColumn", "id")
    .option("lowerBound", 1)
    .option("upperBound", 10000000)
    .option("numPartitions", 100)  # Parallel connections
    .option("fetchsize", 10000)  # Rows per fetch
    .load()
)

# ✅ Incremental load pattern
max_id = spark.table("target").agg(max("id")).collect()[0][0] or 0
incremental_df = (spark.read
    .format("jdbc")
    .option("dbtable", f"(SELECT * FROM source WHERE id > {max_id}) AS t")
    ...
)
```

---

## 2️⃣0️⃣ SCHEMA EVOLUTION

### Delta Lake Schema Evolution

```python
# ✅ Enable schema evolution on write
df.write \
    .format("delta") \
    .mode("append") \
    .option("mergeSchema", "true") \
    .save("/path/to/table")

# ✅ Or enable globally
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")
```

### Schema Evolution in MERGE

```python
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, "/path/to/table")

# ✅ MERGE with schema evolution
(delta_table.alias("target")
    .merge(
        source_df.alias("source"),
        "target.id = source.id"
    )
    .whenMatchedUpdateAll()
    .whenNotMatchedInsertAll()
    .execute()
)

# Enable auto-merge for new columns
spark.conf.set("spark.databricks.delta.schema.autoMerge.enabled", "true")
```

### Schema Enforcement Strategies

```python
# ✅ Define explicit schema for validation
expected_schema = StructType([
    StructField("id", LongType(), nullable=False),
    StructField("name", StringType(), nullable=True),
    StructField("amount", DecimalType(18, 2), nullable=True),
    StructField("created_at", TimestampType(), nullable=False)
])

def validate_schema(df: DataFrame, expected: StructType) -> DataFrame:
    """Validate and enforce schema."""
    # Check for missing required columns
    for field in expected.fields:
        if field.name not in df.columns:
            if not field.nullable:
                raise ValueError(f"Missing required column: {field.name}")
            else:
                df = df.withColumn(field.name, lit(None).cast(field.dataType))
    
    # Cast to expected types
    for field in expected.fields:
        if field.name in df.columns:
            df = df.withColumn(field.name, col(field.name).cast(field.dataType))
    
    return df.select([f.name for f in expected.fields])
```

### Handling Breaking Schema Changes

```python
# ✅ Strategy 1: Column rename with alias
df_migrated = df.withColumnRenamed("old_name", "new_name")

# ✅ Strategy 2: Versioned tables
# v1_table -> v2_table migration

# ✅ Strategy 3: Replace table with overwrite schema
df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("overwriteSchema", "true") \
    .save("/path/to/table")

# ✅ Strategy 4: Add migration column mappings
spark.sql("""
    ALTER TABLE catalog.schema.table
    SET TBLPROPERTIES (
        'delta.columnMapping.mode' = 'name',
        'delta.minReaderVersion' = '2',
        'delta.minWriterVersion' = '5'
    )
""")

# Now you can rename columns
spark.sql("ALTER TABLE catalog.schema.table RENAME COLUMN old_name TO new_name")
```

---

## 2️⃣1️⃣ TIME TRAVEL & VERSIONING

### Query Historical Data

```python
# ✅ Query by version
df_version = spark.read.format("delta") \
    .option("versionAsOf", 10) \
    .load("/path/to/table")

# ✅ Query by timestamp
df_timestamp = spark.read.format("delta") \
    .option("timestampAsOf", "2024-01-15 10:00:00") \
    .load("/path/to/table")

# ✅ SQL syntax
spark.sql("SELECT * FROM table_name VERSION AS OF 10")
spark.sql("SELECT * FROM table_name TIMESTAMP AS OF '2024-01-15 10:00:00'")
```

### View Table History

```python
# ✅ Check table history
history_df = spark.sql("DESCRIBE HISTORY delta.`/path/to/table`")
display(history_df)

# Or using DeltaTable API
from delta.tables import DeltaTable
delta_table = DeltaTable.forPath(spark, "/path/to/table")
display(delta_table.history())
```

### Restore Table to Previous Version

```python
# ✅ Restore to version
spark.sql("RESTORE TABLE catalog.schema.table TO VERSION AS OF 10")

# ✅ Restore to timestamp
spark.sql("RESTORE TABLE catalog.schema.table TO TIMESTAMP AS OF '2024-01-15'")

# ✅ Python API
delta_table = DeltaTable.forPath(spark, "/path/to/table")
delta_table.restoreToVersion(10)
```

### Retention Configuration

```python
# ✅ Configure retention periods
spark.sql("""
    ALTER TABLE catalog.schema.table
    SET TBLPROPERTIES (
        'delta.logRetentionDuration' = 'interval 30 days',
        'delta.deletedFileRetentionDuration' = 'interval 7 days'
    )
""")

# ✅ VACUUM with retention check disabled (DANGEROUS - use carefully)
spark.conf.set("spark.databricks.delta.retentionDurationCheck.enabled", "false")
spark.sql("VACUUM catalog.schema.table RETAIN 0 HOURS")  # Only in emergencies!
```

---

## 2️⃣2️⃣ COST OPTIMIZATION

### DBU Optimization Strategies

| Strategy | Impact | Implementation |
|----------|--------|----------------|
| Use Photon | 2-8x faster | Enable on cluster |
| Spot instances | 60-90% savings | Workers only |
| Autoscaling | Variable savings | Right-size min/max |
| Auto-terminate | Reduces idle | 10-30 min timeout |
| Cluster pools | Faster start | Pre-warm instances |
| Job clusters | Per-job billing | Use for scheduled jobs |
| Serverless SQL | Pay-per-query | SQL workloads |

### Cluster Cost Monitoring

```python
# ✅ Log cluster usage metrics
def log_cluster_metrics():
    """Log cluster utilization for cost analysis."""
    import json
    
    # Get cluster info (via API or context)
    context = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
    cluster_id = context.clusterId().get()
    
    # Log usage
    metrics = {
        "cluster_id": cluster_id,
        "timestamp": datetime.utcnow().isoformat(),
        "notebook": context.notebookPath().get(),
        "runtime_seconds": time.time() - start_time
    }
    logger.info(f"CLUSTER_USAGE: {json.dumps(metrics)}")
```

### Storage Cost Optimization

```python
# ✅ Use lifecycle policies for old data
# Azure Blob Storage lifecycle management:
# - Move to cool tier after 30 days
# - Move to archive after 90 days
# - Delete after 365 days

# ✅ Compress data efficiently
df.write \
    .format("delta") \
    .option("compression", "zstd")  # Better compression ratio \
    .save("/path/to/table")

# ✅ Regular VACUUM to remove old files
spark.sql("VACUUM catalog.schema.table RETAIN 168 HOURS")

# ✅ Monitor storage
display(spark.sql("DESCRIBE DETAIL delta.`/path/to/table`"))
# Check: sizeInBytes, numFiles
```

### Job Scheduling Optimization

```python
# ✅ Use job clusters instead of all-purpose
# - Cheaper pricing tier
# - Auto-terminates after job
# - Right-sized for workload

# ✅ Schedule during off-peak hours
# - Lower spot instance prices
# - More availability

# ✅ Batch small jobs together
# - Reduce cluster start overhead
# - Share warm caches
```

---

## 2️⃣3️⃣ WINDOW FUNCTIONS & AGGREGATION OPTIMIZATION

### Window Function Best Practices

```python
from pyspark.sql.window import Window
from pyspark.sql.functions import row_number, rank, lag, lead, sum as spark_sum

# ✅ Define window with partition for parallelism
window_spec = Window.partitionBy("customer_id").orderBy("transaction_date")

# ✅ Efficient window operations
df_with_windows = df.select(
    "*",
    row_number().over(window_spec).alias("row_num"),
    lag("amount", 1).over(window_spec).alias("prev_amount"),
    spark_sum("amount").over(window_spec).alias("running_total")
)

# ❌ AVOID: Window without partition (single partition!)
bad_window = Window.orderBy("date")  # All data in one partition!

# ✅ BETTER: Always partition window functions
good_window = Window.partitionBy("category").orderBy("date")
```

### Aggregation Optimization

```python
# ✅ Two-phase aggregation for skewed data
# Phase 1: Partial aggregation with salt
from pyspark.sql.functions import floor, rand, concat, lit

salted_df = df.withColumn("salt", floor(rand() * 10))
partial_agg = salted_df.groupBy("category", "salt").agg(
    spark_sum("amount").alias("partial_sum"),
    count("*").alias("partial_count")
)

# Phase 2: Final aggregation
final_agg = partial_agg.groupBy("category").agg(
    spark_sum("partial_sum").alias("total_amount"),
    spark_sum("partial_count").alias("total_count")
)

# ✅ Use approximate functions for large datasets
from pyspark.sql.functions import approx_count_distinct, percentile_approx

df.agg(
    approx_count_distinct("user_id", 0.05).alias("approx_users"),  # 5% error
    percentile_approx("amount", 0.5, 100).alias("median_amount")
)
```

### Rollup and Cube Optimization

```python
# ✅ Use rollup for hierarchical aggregations
df.rollup("year", "quarter", "month").agg(
    spark_sum("revenue").alias("total_revenue")
)

# ✅ Use cube for all combinations
df.cube("region", "product").agg(
    spark_sum("sales").alias("total_sales")
)

# ✅ Grouping sets for specific combinations
spark.sql("""
    SELECT region, product, SUM(sales)
    FROM sales
    GROUP BY GROUPING SETS (
        (region, product),
        (region),
        ()
    )
""")
```

---

## 2️⃣4️⃣ SERIALIZATION & DATA FORMATS

### Kryo Serialization

```python
# ✅ Enable Kryo for better RDD performance
spark.conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
spark.conf.set("spark.kryoserializer.buffer.max", "1024m")

# Register custom classes
spark.conf.set("spark.kryo.registrationRequired", "false")
# For specific classes:
# spark.conf.set("spark.kryo.classesToRegister", "com.example.MyClass")
```

### Arrow Optimization

```python
# ✅ Enable Arrow for Pandas conversions
spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
spark.conf.set("spark.sql.execution.arrow.pyspark.fallback.enabled", "true")
spark.conf.set("spark.sql.execution.arrow.maxRecordsPerBatch", "10000")

# ✅ Efficient Pandas conversion
pandas_df = df.toPandas()  # Uses Arrow automatically

# ✅ Pandas UDFs benefit from Arrow
@pandas_udf(DoubleType())
def multiply_by_two(s: pd.Series) -> pd.Series:
    return s * 2
```

### File Format Selection

| Format | Best For | Compression | Schema Evolution |
|--------|----------|-------------|------------------|
| Delta | All use cases | ✅ Excellent | ✅ Built-in |
| Parquet | Read-heavy | ✅ Excellent | ⚠️ Limited |
| ORC | Hive compatibility | ✅ Good | ⚠️ Limited |
| Avro | Schema evolution | ✅ Good | ✅ Good |
| JSON | Interchange | ❌ Poor | ✅ Flexible |
| CSV | Legacy/simple | ❌ Poor | ❌ None |

### Compression Codecs

```python
# ✅ Compression options for Delta/Parquet
# snappy - Fast, moderate compression (default)
# zstd - Better compression, slightly slower
# gzip - Maximum compression, slower
# lz4 - Fastest, less compression

df.write \
    .format("delta") \
    .option("compression", "zstd") \
    .save("/path/to/table")

# ✅ Shuffle compression
spark.conf.set("spark.shuffle.compress", "true")
spark.conf.set("spark.io.compression.codec", "lz4")
```

---

## 2️⃣5️⃣ DELTA LIVE TABLES (DLT)

### DLT Table Definitions

```python
import dlt
from pyspark.sql.functions import col, expr

# ✅ Bronze layer - raw ingestion
@dlt.table(
    name="bronze_orders",
    comment="Raw orders from landing zone",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.managed": "true"
    }
)
def bronze_orders():
    return (
        spark.readStream
        .format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", "/mnt/schema/orders")
        .load("/mnt/landing/orders/")
    )

# ✅ Silver layer - cleaned and validated
@dlt.table(
    name="silver_orders",
    comment="Cleaned orders with data quality checks"
)
@dlt.expect_or_drop("valid_order_id", "order_id IS NOT NULL")
@dlt.expect_or_fail("valid_amount", "amount > 0")
@dlt.expect("valid_customer", "customer_id IS NOT NULL")  # Warn only
def silver_orders():
    return (
        dlt.read_stream("bronze_orders")
        .select(
            col("order_id").cast("long"),
            col("customer_id").cast("long"),
            col("amount").cast("decimal(18,2)"),
            col("order_date").cast("timestamp")
        )
        .filter(col("order_date") >= "2020-01-01")
    )

# ✅ Gold layer - aggregated
@dlt.table(
    name="gold_daily_sales",
    comment="Daily sales aggregates"
)
def gold_daily_sales():
    return (
        dlt.read("silver_orders")
        .groupBy(expr("date(order_date)").alias("order_date"))
        .agg(
            spark_sum("amount").alias("total_sales"),
            count("*").alias("order_count")
        )
    )
```

### DLT Expectations (Data Quality)

```python
# ✅ Expectation types
@dlt.expect("description", "condition")           # Log violation, keep record
@dlt.expect_or_drop("description", "condition")   # Drop failing records
@dlt.expect_or_fail("description", "condition")   # Fail pipeline

# ✅ Multiple expectations
@dlt.table
@dlt.expect_all({
    "valid_id": "id IS NOT NULL",
    "valid_date": "date >= '2020-01-01'",
    "valid_amount": "amount > 0"
})
def validated_table():
    return dlt.read("source")

# ✅ Quarantine pattern
@dlt.table(name="quarantine_orders")
@dlt.expect_or_drop("invalid_data", "NOT (order_id IS NULL OR amount <= 0)")
def quarantine():
    return dlt.read_stream("bronze_orders").filter(
        "order_id IS NULL OR amount <= 0"
    )
```

### Materialized Views vs Streaming Tables

```python
# ✅ Streaming table - incremental, append-only source
@dlt.table
def streaming_orders():
    return dlt.read_stream("source")  # Uses readStream

# ✅ Materialized view - recomputed on refresh
@dlt.table
def daily_summary():
    return dlt.read("orders").groupBy("date").agg(...)  # Uses read (not stream)

# ✅ Live table - can be either
@dlt.table
def hybrid():
    if dlt.is_streaming:
        return dlt.read_stream("source")
    else:
        return dlt.read("source")
```

---

## 2️⃣6️⃣ UNITY CATALOG DEEP DIVE

### Three-Level Namespace

```sql
-- Catalog > Schema > Table/View/Function
USE CATALOG production_catalog;
USE SCHEMA sales;
SELECT * FROM orders;  -- Full path: production_catalog.sales.orders

-- ✅ Always use fully qualified names in production
SELECT * FROM production_catalog.sales.orders;
```

### Data Governance Features

```python
# ✅ Row-level security
spark.sql("""
    CREATE FUNCTION sales.region_filter(region STRING)
    RETURNS BOOLEAN
    RETURN IF(is_member('admin_group'), true, region = current_user_region())
""")

spark.sql("""
    ALTER TABLE sales.orders
    SET ROW FILTER sales.region_filter ON (region)
""")

# ✅ Column masking
spark.sql("""
    CREATE FUNCTION sales.mask_ssn(ssn STRING)
    RETURNS STRING
    RETURN IF(is_member('pii_access'), ssn, 'XXX-XX-' || RIGHT(ssn, 4))
""")

spark.sql("""
    ALTER TABLE sales.customers
    ALTER COLUMN ssn SET MASK sales.mask_ssn
""")
```

### Lineage and Auditing

```python
# ✅ View table lineage (via UI or API)
# Unity Catalog automatically tracks:
# - What tables read from this table
# - What tables this table reads from
# - Column-level lineage

# ✅ Audit logging
# All access is logged automatically
# Query via system tables:
spark.sql("""
    SELECT * FROM system.access.audit
    WHERE action_name = 'getTable'
    AND request_params.full_name_arg = 'catalog.schema.table'
""")
```

### External Locations and Storage Credentials

```python
# ✅ Create storage credential (admin)
spark.sql("""
    CREATE STORAGE CREDENTIAL azure_storage_cred
    WITH (
        AZURE_MANAGED_IDENTITY = '<managed-identity-id>'
    )
""")

# ✅ Create external location
spark.sql("""
    CREATE EXTERNAL LOCATION azure_landing
    URL 'abfss://landing@storageaccount.dfs.core.windows.net/'
    WITH (STORAGE CREDENTIAL azure_storage_cred)
""")

# ✅ Create external table
spark.sql("""
    CREATE TABLE catalog.schema.external_table
    LOCATION 'abfss://landing@storageaccount.dfs.core.windows.net/data/'
""")
```

---

## 2️⃣7️⃣ EXTERNAL DATA SOURCES

### Kafka Integration

```python
# ✅ Read from Kafka
kafka_df = (spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "broker1:9092,broker2:9092")
    .option("subscribe", "orders-topic")
    .option("startingOffsets", "earliest")
    .option("kafka.security.protocol", "SASL_SSL")
    .option("kafka.sasl.mechanism", "PLAIN")
    .option("kafka.sasl.jaas.config", 
        f"org.apache.kafka.common.security.plain.PlainLoginModule required " +
        f"username='{dbutils.secrets.get('kafka', 'username')}' " +
        f"password='{dbutils.secrets.get('kafka', 'password')}';")
    .load()
)

# ✅ Parse Kafka messages
from pyspark.sql.functions import from_json, col

parsed_df = kafka_df.select(
    col("key").cast("string"),
    from_json(col("value").cast("string"), schema).alias("data"),
    col("timestamp")
).select("key", "data.*", "timestamp")

# ✅ Write to Kafka
df.selectExpr("key", "to_json(struct(*)) AS value") \
    .write \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "broker:9092") \
    .option("topic", "output-topic") \
    .save()
```

### Azure Event Hubs

```python
# ✅ Read from Event Hubs (Kafka-compatible endpoint)
connection_string = dbutils.secrets.get("eventhub", "connection-string")

eh_df = (spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "<namespace>.servicebus.windows.net:9093")
    .option("subscribe", "<eventhub-name>")
    .option("kafka.sasl.mechanism", "PLAIN")
    .option("kafka.security.protocol", "SASL_SSL")
    .option("kafka.sasl.jaas.config", 
        f"org.apache.kafka.common.security.plain.PlainLoginModule required " +
        f"username='$ConnectionString' password='{connection_string}';")
    .load()
)
```

### REST API Integration

```python
import requests
from pyspark.sql.functions import explode, col

# ✅ Batch API ingestion with rate limiting
def fetch_paginated_api(base_url: str, params: dict) -> list:
    """Fetch all pages from paginated API."""
    all_results = []
    page = 1
    
    while True:
        params["page"] = page
        response = requests.get(
            base_url,
            params=params,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if not data.get("results"):
            break
            
        all_results.extend(data["results"])
        page += 1
        time.sleep(0.1)  # Rate limiting
    
    return all_results

# ✅ Parallel API calls with spark
def fetch_entity(entity_id: str) -> dict:
    response = requests.get(f"{base_url}/{entity_id}", headers=headers)
    return response.json()

entity_ids = ["id1", "id2", "id3", ...]
results_rdd = spark.sparkContext.parallelize(entity_ids, 10).map(fetch_entity)
df = spark.createDataFrame(results_rdd.collect(), schema)
```

### Azure Cosmos DB

```python
# ✅ Read from Cosmos DB
cosmos_df = (spark.read
    .format("cosmos.oltp")
    .option("spark.synapse.linkedService", "CosmosDbLinkedService")
    .option("spark.cosmos.container", "myContainer")
    .option("spark.cosmos.read.inferSchema.enabled", "true")
    .load()
)

# ✅ With connection config
cosmos_df = (spark.read
    .format("cosmos.oltp")
    .option("spark.cosmos.accountEndpoint", cosmos_endpoint)
    .option("spark.cosmos.accountKey", dbutils.secrets.get("cosmos", "key"))
    .option("spark.cosmos.database", "myDatabase")
    .option("spark.cosmos.container", "myContainer")
    .load()
)
```

---

## 2️⃣8️⃣ NOTEBOOK ORCHESTRATION

### dbutils.notebook.run

```python
# ✅ Call notebook and get return value
result = dbutils.notebook.run(
    "/Shared/ETL/process_orders",
    timeout_seconds=3600,
    arguments={
        "environment": "prod",
        "process_date": "2024-01-15"
    }
)
print(f"Result: {result}")

# ✅ In called notebook, return value with dbutils.notebook.exit
dbutils.notebook.exit(json.dumps({"status": "success", "rows": 1000}))
```

### Parallel Notebook Execution

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

def run_notebook(notebook_path: str, params: dict) -> dict:
    """Run notebook and return result."""
    try:
        result = dbutils.notebook.run(
            notebook_path,
            timeout_seconds=3600,
            arguments=params
        )
        return {"notebook": notebook_path, "status": "success", "result": json.loads(result)}
    except Exception as e:
        return {"notebook": notebook_path, "status": "failed", "error": str(e)}

# ✅ Run notebooks in parallel
notebooks = [
    ("/ETL/process_orders", {"date": "2024-01-15"}),
    ("/ETL/process_customers", {"date": "2024-01-15"}),
    ("/ETL/process_products", {"date": "2024-01-15"}),
]

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(run_notebook, nb, params): nb 
        for nb, params in notebooks
    }
    
    results = []
    for future in as_completed(futures):
        results.append(future.result())

# Check for failures
failures = [r for r in results if r["status"] == "failed"]
if failures:
    raise Exception(f"Notebooks failed: {failures}")
```

### %run for Shared Code

```python
# ✅ Include shared utilities
%run ./includes/utilities

# ✅ Include configuration
%run ./config/environment_config

# ✅ Structure for reusable code
# /Shared/
#   /includes/
#     utilities.py      # Common functions
#     logging.py        # Logging setup
#     validation.py     # Data validation
#   /config/
#     environment.py    # Environment configs
```

### Databricks Workflows (Jobs)

```python
# ✅ Job configuration best practices
{
    "name": "Daily ETL Pipeline",
    "tasks": [
        {
            "task_key": "extract",
            "notebook_task": {
                "notebook_path": "/ETL/extract",
                "base_parameters": {"env": "prod"}
            },
            "new_cluster": {...}  # Job cluster
        },
        {
            "task_key": "transform",
            "depends_on": [{"task_key": "extract"}],
            "notebook_task": {"notebook_path": "/ETL/transform"},
            "existing_cluster_id": "..."  # Or job cluster
        },
        {
            "task_key": "load",
            "depends_on": [{"task_key": "transform"}],
            "notebook_task": {"notebook_path": "/ETL/load"}
        }
    ],
    "email_notifications": {
        "on_failure": ["data-team@company.com"]
    },
    "schedule": {
        "quartz_cron_expression": "0 0 6 * * ?",
        "timezone_id": "UTC"
    }
}
```

---

## 2️⃣9️⃣ CHANGE DATA FEED (CDF)

### Enable Change Data Feed

```sql
-- ✅ Enable on new table
CREATE TABLE catalog.schema.orders (
    id BIGINT,
    status STRING,
    amount DECIMAL(18,2)
)
USING DELTA
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');

-- ✅ Enable on existing table
ALTER TABLE catalog.schema.orders
SET TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true');
```

### Read Changes

```python
# ✅ Read changes by version
changes_df = (spark.read
    .format("delta")
    .option("readChangeFeed", "true")
    .option("startingVersion", 10)
    .option("endingVersion", 20)
    .table("catalog.schema.orders")
)

# ✅ Read changes by timestamp
changes_df = (spark.read
    .format("delta")
    .option("readChangeFeed", "true")
    .option("startingTimestamp", "2024-01-01 00:00:00")
    .option("endingTimestamp", "2024-01-15 00:00:00")
    .table("catalog.schema.orders")
)

# ✅ Streaming changes
changes_stream = (spark.readStream
    .format("delta")
    .option("readChangeFeed", "true")
    .option("startingVersion", 0)
    .table("catalog.schema.orders")
)
```

### CDF Columns

```python
# CDF adds these columns:
# _change_type: insert, update_preimage, update_postimage, delete
# _commit_version: Version number
# _commit_timestamp: Timestamp of change

# ✅ Process different change types
inserts = changes_df.filter(col("_change_type") == "insert")
updates = changes_df.filter(col("_change_type") == "update_postimage")
deletes = changes_df.filter(col("_change_type") == "delete")

# ✅ Replicate to target
def apply_changes(changes_df: DataFrame, target_table: str):
    """Apply CDC changes to target table."""
    from delta.tables import DeltaTable
    
    target = DeltaTable.forName(spark, target_table)
    
    # Get latest change per key
    window = Window.partitionBy("id").orderBy(col("_commit_version").desc())
    latest_changes = changes_df \
        .withColumn("rn", row_number().over(window)) \
        .filter(col("rn") == 1) \
        .drop("rn")
    
    # Apply changes
    (target.alias("t")
        .merge(
            latest_changes.alias("s"),
            "t.id = s.id"
        )
        .whenMatchedDelete(condition="s._change_type = 'delete'")
        .whenMatchedUpdateAll(condition="s._change_type IN ('insert', 'update_postimage')")
        .whenNotMatchedInsertAll(condition="s._change_type IN ('insert', 'update_postimage')")
        .execute()
    )
```

---

## 3️⃣0️⃣ MLFLOW INTEGRATION

### Experiment Tracking

```python
import mlflow
import mlflow.spark

# ✅ Set experiment
mlflow.set_experiment("/Shared/experiments/sales_forecast")

# ✅ Log training run
with mlflow.start_run(run_name="xgboost_v1"):
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 5)
    mlflow.log_param("learning_rate", 0.1)
    
    # Train model
    model = train_model(X_train, y_train)
    
    # Log metrics
    mlflow.log_metric("rmse", rmse)
    mlflow.log_metric("mae", mae)
    mlflow.log_metric("r2", r2)
    
    # Log model
    mlflow.sklearn.log_model(model, "model")
    
    # Log artifacts
    mlflow.log_artifact("feature_importance.png")
```

### Model Registry

```python
# ✅ Register model
model_uri = f"runs:/{run_id}/model"
mlflow.register_model(model_uri, "SalesForecastModel")

# ✅ Transition model stage
from mlflow.tracking import MlflowClient

client = MlflowClient()
client.transition_model_version_stage(
    name="SalesForecastModel",
    version=1,
    stage="Production"
)

# ✅ Load production model
model = mlflow.pyfunc.load_model("models:/SalesForecastModel/Production")
predictions = model.predict(data)
```

### Feature Store Integration

```python
from databricks.feature_store import FeatureStoreClient

fs = FeatureStoreClient()

# ✅ Create feature table
fs.create_table(
    name="catalog.schema.customer_features",
    primary_keys=["customer_id"],
    df=feature_df,
    description="Customer features for ML models"
)

# ✅ Write features
fs.write_table(
    name="catalog.schema.customer_features",
    df=updated_features,
    mode="merge"
)

# ✅ Read features for training
training_set = fs.create_training_set(
    df=labels_df,
    feature_lookups=[
        FeatureLookup(
            table_name="catalog.schema.customer_features",
            feature_names=["total_purchases", "avg_order_value"],
            lookup_key="customer_id"
        )
    ],
    label="churn"
)
training_df = training_set.load_df()
```

---

## 3️⃣1️⃣ CONCURRENCY & ISOLATION

### Isolation Levels

```python
# ✅ Serializable (default for Delta)
# Provides strongest guarantees
# - No dirty reads
# - No non-repeatable reads
# - No phantom reads

# ✅ WriteSerializable (for higher throughput)
spark.conf.set("spark.databricks.delta.isolationLevel", "WriteSerializable")
# Allows more concurrent writes but ensures:
# - Write operations are serializable
# - Reads may see changes from concurrent writes
```

### Concurrent Write Handling

```python
# ✅ Optimistic concurrency control
# Delta Lake handles conflicts automatically
# Retry logic for conflict resolution

from delta.exceptions import ConcurrentModificationException

def write_with_retry(df: DataFrame, path: str, max_retries: int = 3):
    """Write with conflict retry."""
    for attempt in range(max_retries):
        try:
            df.write.format("delta").mode("append").save(path)
            return
        except ConcurrentModificationException:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

# ✅ Use MERGE for safe upserts
# MERGE handles concurrent modifications gracefully
```

### Table Constraints

```sql
-- ✅ Add NOT NULL constraint
ALTER TABLE catalog.schema.orders ALTER COLUMN id SET NOT NULL;

-- ✅ Add CHECK constraint
ALTER TABLE catalog.schema.orders ADD CONSTRAINT valid_amount CHECK (amount > 0);

-- ✅ Primary key (informational, not enforced)
ALTER TABLE catalog.schema.orders ADD CONSTRAINT pk_orders PRIMARY KEY (id);

-- ✅ Foreign key (informational)
ALTER TABLE catalog.schema.order_items ADD CONSTRAINT fk_order 
FOREIGN KEY (order_id) REFERENCES catalog.schema.orders(id);
```

---

## 3️⃣2️⃣ DATABRICKS SQL & SERVERLESS

### SQL Warehouse Optimization

```sql
-- ✅ Use appropriate warehouse size
-- 2X-Small: Development, small queries
-- Small-Medium: Interactive dashboards
-- Large-4XL: Heavy analytics, large aggregations

-- ✅ Query optimization hints
SELECT /*+ BROADCAST(small_table) */ *
FROM large_table
JOIN small_table ON large_table.id = small_table.id;

-- ✅ Use EXPLAIN for query analysis
EXPLAIN EXTENDED SELECT * FROM table WHERE condition;
```

### Serverless SQL Best Practices

```python
# ✅ Serverless benefits
# - No cluster management
# - Instant start
# - Auto-scaling
# - Pay-per-query

# ✅ When to use Serverless
# - Interactive queries
# - BI dashboards
# - Ad-hoc analysis
# - Variable workloads

# ✅ Optimize for Serverless
# - Use Delta tables (better caching)
# - Avoid UDFs (can't use Photon)
# - Use SQL built-in functions
# - Leverage materialized views
```

### Query Performance Tips

```sql
-- ✅ Use ANALYZE for statistics
ANALYZE TABLE catalog.schema.table COMPUTE STATISTICS FOR ALL COLUMNS;

-- ✅ Optimize frequently filtered columns
OPTIMIZE catalog.schema.table ZORDER BY (filter_column);

-- ✅ Use result caching
-- Enabled by default, queries with identical plans use cached results

-- ✅ Materialized views for repeated queries
CREATE MATERIALIZED VIEW catalog.schema.daily_summary
AS SELECT date, SUM(amount) as total
FROM orders
GROUP BY date;
```

---

## 3️⃣3️⃣ DATABRICKS ASSET BUNDLES

### Project Structure

```
my-project/
├── databricks.yml           # Bundle configuration
├── resources/
│   ├── jobs.yml            # Job definitions
│   └── pipelines.yml       # DLT pipeline definitions
├── src/
│   ├── notebooks/          # Notebooks
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   └── python/             # Python packages
│       └── common/
│           ├── __init__.py
│           └── utils.py
├── tests/
│   └── test_utils.py
└── requirements.txt
```

### Bundle Configuration

```yaml
# databricks.yml
bundle:
  name: my-etl-bundle

variables:
  environment:
    default: dev

environments:
  dev:
    mode: development
    default: true
    workspace:
      host: https://adb-xxx.azuredatabricks.net
    
  prod:
    mode: production
    workspace:
      host: https://adb-yyy.azuredatabricks.net
    run_as:
      service_principal_name: sp-prod-etl

resources:
  jobs:
    daily_etl:
      name: "Daily ETL Pipeline - ${var.environment}"
      tasks:
        - task_key: bronze_ingest
          notebook_task:
            notebook_path: ./src/notebooks/bronze/ingest.py
          new_cluster:
            spark_version: 13.3.x-scala2.12
            node_type_id: Standard_E8s_v3
            num_workers: 2
```

### Deploy Commands

```bash
# Validate bundle
databricks bundle validate

# Deploy to dev
databricks bundle deploy -e dev

# Deploy to prod
databricks bundle deploy -e prod

# Run a job
databricks bundle run daily_etl -e prod

# Destroy resources
databricks bundle destroy -e dev
```

---

## 3️⃣4️⃣ NETWORK & SHUFFLE OPTIMIZATION

### Shuffle Configuration

```python
# ✅ Shuffle compression
spark.conf.set("spark.shuffle.compress", "true")
spark.conf.set("spark.shuffle.spill.compress", "true")
spark.conf.set("spark.io.compression.codec", "lz4")  # Fast compression

# ✅ Shuffle service
spark.conf.set("spark.shuffle.service.enabled", "true")

# ✅ Reduce shuffle data
# - Filter early
# - Select only needed columns
# - Use broadcast for small tables
# - Avoid unnecessary repartitions
```

### Shuffle Partition Tuning

```python
# ✅ Dynamic shuffle partitions with AQE
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", "128MB")
spark.conf.set("spark.sql.adaptive.coalescePartitions.minPartitionSize", "1MB")

# ✅ Manual tuning (when AQE not sufficient)
# Rule of thumb: target 128-200MB per partition
data_size_gb = 100
target_partition_size_mb = 128
num_partitions = (data_size_gb * 1024) / target_partition_size_mb  # ~800

spark.conf.set("spark.sql.shuffle.partitions", str(int(num_partitions)))
```

### Network Timeout Configuration

```python
# ✅ Network timeouts for large clusters/data
spark.conf.set("spark.network.timeout", "600s")
spark.conf.set("spark.executor.heartbeatInterval", "60s")
spark.conf.set("spark.sql.broadcastTimeout", "600")

# ✅ For cloud storage
spark.conf.set("spark.hadoop.fs.azure.io.retry.max.retries", "10")
spark.conf.set("spark.hadoop.fs.azure.io.retry.backoff.interval", "1000")
```

---

## 📊 COMPREHENSIVE OPTIMIZATION DECISION TREE

```
START: Is your notebook production-ready?
│
├─ PERFORMANCE ISSUES?
│   ├─ Slow reads → Check partition pruning, column selection, file sizes
│   ├─ Slow writes → Enable auto-optimize, check partition strategy
│   ├─ Slow joins → Use broadcast, check skew, enable AQE
│   ├─ Memory errors → Increase partitions, use disk spill, optimize caching
│   └─ Shuffle heavy → Reduce shuffle, pre-aggregate, use bucketing
│
├─ DATA QUALITY ISSUES?
│   ├─ Schema problems → Implement schema validation, use DLT expectations
│   ├─ Duplicates → Use MERGE, add constraints, implement deduplication
│   ├─ Late data → Use watermarking, handle with MERGE
│   └─ Missing data → Add null checks, implement data quality framework
│
├─ RELIABILITY ISSUES?
│   ├─ Job failures → Add retry logic, improve error handling
│   ├─ Data inconsistency → Implement idempotency, use checkpoints
│   ├─ Concurrent conflicts → Use Delta MERGE, implement retry
│   └─ Schema drift → Enable schema evolution, validate schemas
│
├─ COST ISSUES?
│   ├─ High compute → Use spot instances, right-size clusters, use Photon
│   ├─ High storage → VACUUM regularly, compress data, lifecycle policies
│   ├─ Long runtimes → Optimize queries, use caching, parallelize
│   └─ Idle clusters → Auto-terminate, use job clusters, serverless
│
└─ SECURITY/GOVERNANCE ISSUES?
    ├─ Credentials exposed → Use secrets, service principals
    ├─ Unauthorized access → Unity Catalog, row/column security
    ├─ No audit trail → Enable audit logging, use Unity Catalog
    └─ No lineage → Use Unity Catalog, DLT for tracking
```

---

## 📝 EXTENDED PROMPT TEMPLATE FOR NOTEBOOK OPTIMIZATION

Use this comprehensive template when optimizing notebooks:

```
I need to optimize the following Azure Databricks notebook for production use.

**Current Notebook Context:**
- Purpose: [What the notebook does]
- Data Size: [Input/output data sizes]
- Frequency: [How often it runs - batch/streaming/ad-hoc]
- Current Runtime: [If known]
- Known Issues: [Any specific problems]

**Workload Type:**
- [ ] Batch ETL
- [ ] Streaming ingestion
- [ ] ML training/inference
- [ ] SQL analytics
- [ ] Data quality/validation

**Infrastructure:**
- Cluster Type: [Standard/Photon/Serverless]
- Cluster Size: [Worker count and type]
- Unity Catalog: [Yes/No]
- Delta Live Tables: [Yes/No]

**Please analyze and optimize for:**

1. **Performance**
   - Spark configuration tuning
   - Partition and file optimization
   - Join and aggregation optimization
   - Caching strategy
   - Memory management

2. **Data Management**
   - Delta Lake best practices
   - Schema evolution handling
   - Data quality checks
   - Change data capture (if applicable)

3. **Streaming (if applicable)**
   - Auto Loader configuration
   - Watermarking and late data
   - Checkpoint management
   - Trigger optimization

4. **Code Quality**
   - Modular structure
   - Error handling
   - Logging and monitoring
   - Documentation

5. **Production Readiness**
   - Idempotency
   - Retry logic
   - Alerting
   - CI/CD integration

6. **Cost Optimization**
   - Cluster sizing
   - Spot instances
   - Storage optimization
   - Query efficiency

7. **Security & Governance**
   - Secrets management
   - Access control
   - Audit logging
   - Data lineage

Please provide:
1. Analysis of current issues with severity ratings
2. Prioritized optimization recommendations
3. Refactored code with detailed comments
4. Expected performance/cost improvement estimates
5. Testing recommendations
```

---

## 3️⃣5️⃣ DBUTILS COMPREHENSIVE REFERENCE

### File System Operations (dbutils.fs)

```python
# ✅ List files
files = dbutils.fs.ls("/mnt/data/")
for file in files:
    print(f"{file.name} - {file.size} bytes")

# ✅ Copy files
dbutils.fs.cp("/mnt/source/file.parquet", "/mnt/dest/file.parquet")
dbutils.fs.cp("/mnt/source/", "/mnt/dest/", recurse=True)

# ✅ Move files
dbutils.fs.mv("/mnt/source/file.parquet", "/mnt/dest/file.parquet")

# ✅ Remove files
dbutils.fs.rm("/mnt/data/old_file.parquet")
dbutils.fs.rm("/mnt/data/old_folder/", recurse=True)

# ✅ Create directories
dbutils.fs.mkdirs("/mnt/data/new_folder/")

# ✅ Read/write small files
content = dbutils.fs.head("/mnt/data/config.json", 1000)  # First 1000 bytes
dbutils.fs.put("/mnt/data/output.txt", "content here", overwrite=True)

# ✅ Mount Azure storage
dbutils.fs.mount(
    source="wasbs://container@storage.blob.core.windows.net/",
    mount_point="/mnt/mydata",
    extra_configs={
        "fs.azure.account.key.storage.blob.core.windows.net": 
            dbutils.secrets.get("scope", "storage-key")
    }
)

# ✅ Unmount
dbutils.fs.unmount("/mnt/mydata")

# ✅ List mounts
display(dbutils.fs.mounts())
```

### Secrets Management (dbutils.secrets)

```python
# ✅ Get secret value
password = dbutils.secrets.get(scope="my-scope", key="db-password")

# ✅ List available scopes
scopes = dbutils.secrets.listScopes()
for scope in scopes:
    print(scope.name)

# ✅ List secrets in scope (returns metadata, not values)
secrets = dbutils.secrets.list("my-scope")
for secret in secrets:
    print(secret.key)

# ✅ Best practice: Create wrapper function
def get_secret(key: str, scope: str = "default-scope") -> str:
    """Get secret with error handling."""
    try:
        return dbutils.secrets.get(scope=scope, key=key)
    except Exception as e:
        raise ValueError(f"Failed to retrieve secret '{key}' from scope '{scope}': {e}")
```

### Widgets (dbutils.widgets)

```python
# ✅ Create widgets
dbutils.widgets.text("environment", "dev", "Environment")
dbutils.widgets.dropdown("region", "us-east", ["us-east", "us-west", "eu-west"], "Region")
dbutils.widgets.combobox("table", "default", ["default", "custom"], "Table Name")
dbutils.widgets.multiselect("columns", "col1", ["col1", "col2", "col3"], "Columns")

# ✅ Get widget values
environment = dbutils.widgets.get("environment")
region = dbutils.widgets.get("region")

# ✅ Remove widgets
dbutils.widgets.remove("environment")
dbutils.widgets.removeAll()

# ✅ Production pattern with defaults
def get_param(name: str, default: str = None) -> str:
    """Get parameter with fallback."""
    try:
        value = dbutils.widgets.get(name)
        return value if value else default
    except:
        return default

ENVIRONMENT = get_param("environment", "dev")
PROCESS_DATE = get_param("process_date", datetime.now().strftime("%Y-%m-%d"))
```

### Notebook Utilities (dbutils.notebook)

```python
# ✅ Run another notebook
result = dbutils.notebook.run(
    path="/Shared/ETL/process_data",
    timeout_seconds=3600,
    arguments={"date": "2024-01-15", "env": "prod"}
)

# ✅ Exit with return value
dbutils.notebook.exit(json.dumps({"status": "success", "rows": 1000}))

# ✅ Get notebook context
context = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
notebook_path = context.notebookPath().get()
cluster_id = context.clusterId().get()
job_id = context.jobId().getOrElse(lambda: None)
run_id = context.currentRunId().getOrElse(lambda: None)
```

### Library Utilities (dbutils.library)

```python
# ✅ Install library (notebook-scoped)
dbutils.library.installPyPI("pandas", version="1.5.0")
dbutils.library.installPyPI("requests")

# ✅ Restart Python to load libraries
dbutils.library.restartPython()

# Note: Prefer cluster libraries or %pip for production
```

---

## 3️⃣6️⃣ AZURE-SPECIFIC OPTIMIZATIONS

### Azure Data Lake Storage Gen2 Configuration

```python
# ✅ ABFS connector (recommended over WASB)
spark.conf.set("fs.azure.account.auth.type.STORAGE_ACCOUNT.dfs.core.windows.net", "OAuth")
spark.conf.set("fs.azure.account.oauth.provider.type.STORAGE_ACCOUNT.dfs.core.windows.net", 
               "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set("fs.azure.account.oauth2.client.id.STORAGE_ACCOUNT.dfs.core.windows.net", 
               dbutils.secrets.get("azure", "client-id"))
spark.conf.set("fs.azure.account.oauth2.client.secret.STORAGE_ACCOUNT.dfs.core.windows.net", 
               dbutils.secrets.get("azure", "client-secret"))
spark.conf.set("fs.azure.account.oauth2.client.endpoint.STORAGE_ACCOUNT.dfs.core.windows.net", 
               "https://login.microsoftonline.com/TENANT_ID/oauth2/token")

# ✅ Read from ADLS Gen2
df = spark.read.parquet("abfss://container@storageaccount.dfs.core.windows.net/path/")

# ✅ Performance tuning for ADLS
spark.conf.set("fs.azure.read.request.size", "4194304")  # 4MB read size
spark.conf.set("fs.azure.write.request.size", "4194304")  # 4MB write size
```

### Azure Key Vault Integration

```python
# ✅ Key Vault-backed secret scope (recommended)
# Created via Databricks CLI:
# databricks secrets create-scope --scope my-scope --scope-backend-type AZURE_KEYVAULT \
#   --resource-id /subscriptions/.../resourceGroups/.../providers/Microsoft.KeyVault/vaults/my-vault

# Use like regular secrets
password = dbutils.secrets.get(scope="my-keyvault-scope", key="database-password")

# ✅ Direct Key Vault access (if needed)
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://my-vault.vault.azure.net/", credential=credential)
secret = client.get_secret("my-secret")
```

### Azure Service Principal Configuration

```python
# ✅ For accessing Azure resources
tenant_id = dbutils.secrets.get("azure", "tenant-id")
client_id = dbutils.secrets.get("azure", "client-id")
client_secret = dbutils.secrets.get("azure", "client-secret")

# ✅ Storage access with service principal
spark.conf.set(f"fs.azure.account.auth.type.{storage_account}.dfs.core.windows.net", "OAuth")
spark.conf.set(f"fs.azure.account.oauth.provider.type.{storage_account}.dfs.core.windows.net",
               "org.apache.hadoop.fs.azurebfs.oauth2.ClientCredsTokenProvider")
spark.conf.set(f"fs.azure.account.oauth2.client.id.{storage_account}.dfs.core.windows.net", client_id)
spark.conf.set(f"fs.azure.account.oauth2.client.secret.{storage_account}.dfs.core.windows.net", client_secret)
spark.conf.set(f"fs.azure.account.oauth2.client.endpoint.{storage_account}.dfs.core.windows.net",
               f"https://login.microsoftonline.com/{tenant_id}/oauth2/token")
```

### Azure Monitor Integration

```python
# ✅ Send metrics to Azure Monitor
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import stats as stats_module

# Configure exporter
exporter = metrics_exporter.new_metrics_exporter(
    connection_string=dbutils.secrets.get("azure", "appinsights-connection")
)

# ✅ Log Analytics workspace query
# Use Azure Data Explorer connector or REST API

# ✅ Custom metrics logging
def log_to_azure_monitor(metric_name: str, value: float, dimensions: dict = None):
    """Log custom metric to Azure Monitor."""
    # Implementation depends on your monitoring setup
    pass
```

### Private Link / VNet Considerations

```python
# ✅ When using private endpoints:
# - Ensure DNS resolution works
# - Check network security groups
# - Verify private endpoint connections

# ✅ For cross-VNet access
# Use private endpoints or VNet peering

# ✅ Storage firewall configuration
# Add Databricks control plane IPs or use private endpoints
```

---

## 3️⃣7️⃣ ADVANCED SPARK PATTERNS

### MapPartitions for Efficiency

```python
# ✅ Use mapPartitions for batch processing per partition
def process_partition(iterator):
    """Process all rows in partition at once."""
    # Initialize resources once per partition
    connection = create_database_connection()
    
    for row in iterator:
        result = process_with_connection(row, connection)
        yield result
    
    # Cleanup
    connection.close()

result_rdd = df.rdd.mapPartitions(process_partition)
result_df = result_rdd.toDF(schema)

# ✅ Pandas mapInPandas for vectorized processing
def process_pandas(iterator):
    for pdf in iterator:
        # Process pandas DataFrame
        pdf["new_col"] = pdf["existing_col"] * 2
        yield pdf

result_df = df.mapInPandas(process_pandas, schema)
```

### ForeachBatch for Streaming Writes

```python
# ✅ Custom write logic per micro-batch
def write_to_multiple_sinks(batch_df, batch_id):
    """Write each micro-batch to multiple destinations."""
    # Write to Delta
    batch_df.write.format("delta").mode("append").save("/path/to/delta")
    
    # Write to SQL database
    batch_df.write \
        .format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", "target_table") \
        .mode("append") \
        .save()
    
    # Log metrics
    logger.info(f"Batch {batch_id}: {batch_df.count()} rows written")

# Apply to streaming query
(df.writeStream
    .foreachBatch(write_to_multiple_sinks)
    .option("checkpointLocation", "/path/to/checkpoint")
    .start()
)
```

### Dynamic Resource Allocation

```python
# ✅ Enable dynamic allocation
spark.conf.set("spark.dynamicAllocation.enabled", "true")
spark.conf.set("spark.dynamicAllocation.minExecutors", "2")
spark.conf.set("spark.dynamicAllocation.maxExecutors", "20")
spark.conf.set("spark.dynamicAllocation.initialExecutors", "4")
spark.conf.set("spark.dynamicAllocation.executorIdleTimeout", "60s")
spark.conf.set("spark.dynamicAllocation.schedulerBacklogTimeout", "1s")

# Note: Usually configured at cluster level in Databricks
```

### Speculative Execution

```python
# ✅ Enable speculation for stragglers
spark.conf.set("spark.speculation", "true")
spark.conf.set("spark.speculation.interval", "100ms")
spark.conf.set("spark.speculation.multiplier", "1.5")
spark.conf.set("spark.speculation.quantile", "0.75")

# Good for: Heterogeneous clusters, unreliable nodes
# Avoid for: Streaming, non-idempotent operations
```

### Accumulator Patterns

```python
from pyspark import SparkContext

# ✅ Count records meeting criteria
error_count = spark.sparkContext.accumulator(0)
processed_count = spark.sparkContext.accumulator(0)

def process_with_tracking(row):
    global error_count, processed_count
    try:
        result = transform(row)
        processed_count.add(1)
        return result
    except Exception:
        error_count.add(1)
        return None

result_rdd = df.rdd.map(process_with_tracking).filter(lambda x: x is not None)
result_df = result_rdd.toDF()

print(f"Processed: {processed_count.value}, Errors: {error_count.value}")
```

---

## 3️⃣8️⃣ DATA TYPES & NULL HANDLING

### Type Best Practices

```python
from pyspark.sql.types import *
from decimal import Decimal

# ✅ Use appropriate numeric types
# IntegerType: -2B to 2B
# LongType: -9Q to 9Q
# DoubleType: Approximate, fast
# DecimalType(precision, scale): Exact, for financial

df = df.withColumn("amount", col("amount").cast(DecimalType(18, 2)))
df = df.withColumn("count", col("count").cast(IntegerType()))

# ✅ Timestamp handling
from pyspark.sql.functions import to_timestamp, from_utc_timestamp, to_utc_timestamp

# Parse timestamp
df = df.withColumn("event_time", to_timestamp(col("timestamp_str"), "yyyy-MM-dd HH:mm:ss"))

# Handle timezones
df = df.withColumn("event_time_utc", to_utc_timestamp(col("event_time"), "America/New_York"))
df = df.withColumn("event_time_local", from_utc_timestamp(col("event_time_utc"), "Europe/London"))

# ✅ Date handling
from pyspark.sql.functions import to_date, date_format, datediff, date_add

df = df.withColumn("order_date", to_date(col("date_str"), "yyyy-MM-dd"))
df = df.withColumn("formatted", date_format(col("order_date"), "MMM dd, yyyy"))
df = df.withColumn("days_since", datediff(current_date(), col("order_date")))
```

### Null Handling Patterns

```python
from pyspark.sql.functions import col, when, coalesce, isnan, isnull

# ✅ Check for nulls
df.filter(col("value").isNull())
df.filter(col("value").isNotNull())

# ✅ Replace nulls
df = df.fillna({"column1": 0, "column2": "unknown"})
df = df.withColumn("value", coalesce(col("value"), lit(0)))

# ✅ Conditional null handling
df = df.withColumn("category",
    when(col("category").isNull(), "uncategorized")
    .otherwise(col("category"))
)

# ✅ Handle NaN for floating point
df = df.filter(~isnan(col("float_column")))
df = df.withColumn("float_column", 
    when(isnan(col("float_column")), None).otherwise(col("float_column"))
)

# ✅ Drop rows with nulls
df_clean = df.dropna()  # Drop rows with any null
df_clean = df.dropna(subset=["required_col1", "required_col2"])  # Specific columns
df_clean = df.dropna(how="all")  # Drop only if all columns are null
df_clean = df.dropna(thresh=3)  # Keep rows with at least 3 non-null values
```

### Complex Types

```python
from pyspark.sql.functions import array, struct, map_from_arrays, explode, posexplode

# ✅ Array operations
df = df.withColumn("tags_array", split(col("tags"), ","))
df = df.withColumn("first_tag", col("tags_array")[0])
df = df.withColumn("array_size", size(col("tags_array")))

# ✅ Explode arrays (one row per element)
df_exploded = df.select("id", explode(col("tags_array")).alias("tag"))
df_exploded = df.select("id", posexplode(col("tags_array")).alias("position", "tag"))

# ✅ Struct operations
df = df.withColumn("address", struct(
    col("street"),
    col("city"),
    col("zip")
))
df = df.select("id", col("address.city").alias("city"))

# ✅ Map operations
df = df.withColumn("properties", map_from_arrays(col("keys"), col("values")))
df = df.withColumn("specific_value", col("properties")["key1"])
```

---

## 3️⃣9️⃣ STRING & JSON OPERATIONS

### String Operations

```python
from pyspark.sql.functions import (
    concat, concat_ws, substring, length, 
    trim, ltrim, rtrim, lower, upper, initcap,
    regexp_extract, regexp_replace, split,
    lpad, rpad, reverse, translate
)

# ✅ Basic string operations
df = df.withColumn("full_name", concat_ws(" ", col("first_name"), col("last_name")))
df = df.withColumn("name_lower", lower(col("name")))
df = df.withColumn("name_upper", upper(col("name")))
df = df.withColumn("name_trimmed", trim(col("name")))
df = df.withColumn("name_initcap", initcap(col("name")))

# ✅ Substring
df = df.withColumn("code", substring(col("full_code"), 1, 3))  # First 3 chars

# ✅ Regex operations
df = df.withColumn("phone_digits", regexp_replace(col("phone"), r"[^0-9]", ""))
df = df.withColumn("domain", regexp_extract(col("email"), r"@(.+)$", 1))

# ✅ Split string to array
df = df.withColumn("parts", split(col("full_path"), "/"))

# ✅ Padding
df = df.withColumn("code_padded", lpad(col("code"), 10, "0"))
```

### JSON Operations

```python
from pyspark.sql.functions import from_json, to_json, get_json_object, json_tuple, schema_of_json

# ✅ Parse JSON string to struct
json_schema = StructType([
    StructField("name", StringType()),
    StructField("age", IntegerType()),
    StructField("email", StringType())
])

df = df.withColumn("parsed", from_json(col("json_string"), json_schema))
df = df.select("id", col("parsed.name"), col("parsed.age"))

# ✅ Infer schema from sample
sample_json = '{"name": "John", "age": 30}'
inferred_schema = schema_of_json(lit(sample_json))

# ✅ Extract specific field without full parsing
df = df.withColumn("name", get_json_object(col("json_string"), "$.name"))
df = df.withColumn("nested_value", get_json_object(col("json_string"), "$.address.city"))

# ✅ Extract multiple fields
df = df.select("id", json_tuple(col("json_string"), "name", "age", "email"))

# ✅ Convert struct to JSON string
df = df.withColumn("json_output", to_json(struct(col("name"), col("age"))))
```

### Flatten Nested Structures

```python
# ✅ Flatten nested JSON/struct
def flatten_df(nested_df):
    """Recursively flatten nested DataFrame."""
    flat_cols = []
    nested_cols = []
    
    for field in nested_df.schema.fields:
        if isinstance(field.dataType, StructType):
            nested_cols.append(field.name)
        elif isinstance(field.dataType, ArrayType):
            if isinstance(field.dataType.elementType, StructType):
                nested_cols.append(field.name)
            else:
                flat_cols.append(col(field.name))
        else:
            flat_cols.append(col(field.name))
    
    # Expand struct columns
    for nested_col in nested_cols:
        if isinstance(nested_df.schema[nested_col].dataType, StructType):
            for sub_field in nested_df.schema[nested_col].dataType.fields:
                flat_cols.append(col(f"{nested_col}.{sub_field.name}").alias(f"{nested_col}_{sub_field.name}"))
    
    flat_df = nested_df.select(flat_cols)
    
    # Recurse if still nested
    if any(isinstance(f.dataType, StructType) for f in flat_df.schema.fields):
        return flatten_df(flat_df)
    
    return flat_df
```

---

## 4️⃣0️⃣ DEBUGGING & PROFILING

### Spark UI Analysis

```python
# ✅ Key metrics to check in Spark UI

# Jobs Tab:
# - Job duration
# - Number of stages
# - Failed jobs

# Stages Tab:
# - Task distribution (min/max/median duration)
# - Shuffle read/write size
# - Spill (memory/disk)
# - GC time

# Executors Tab:
# - Memory usage per executor
# - Task count distribution
# - Input/output sizes

# SQL Tab:
# - Query execution plan
# - Time per operation
# - Data scanned vs returned
```

### Explain Query Plans

```python
# ✅ Different explain modes
df.explain()  # Simple physical plan
df.explain(mode="simple")  # Same as above
df.explain(mode="extended")  # Logical + physical plans
df.explain(mode="codegen")  # Generated code
df.explain(mode="cost")  # With cost estimates
df.explain(mode="formatted")  # Human-readable format

# ✅ Check for issues in plan:
# - BroadcastHashJoin vs SortMergeJoin
# - Filter pushdown (PushedFilters)
# - Partition pruning (PartitionFilters)
# - WholeStageCodegen presence

# ✅ SQL EXPLAIN
spark.sql("EXPLAIN EXTENDED SELECT * FROM table WHERE date = '2024-01-15'").show(truncate=False)
spark.sql("EXPLAIN COST SELECT * FROM table WHERE date = '2024-01-15'").show(truncate=False)
```

### Performance Profiling

```python
from pyspark.sql import SparkSession
import time

# ✅ Time operations
class SparkProfiler:
    def __init__(self):
        self.timings = {}
    
    def time_operation(self, name: str, operation):
        """Time a Spark operation."""
        start = time.time()
        result = operation()
        
        # Force evaluation
        if hasattr(result, 'count'):
            result.count()
        
        duration = time.time() - start
        self.timings[name] = duration
        print(f"{name}: {duration:.2f}s")
        return result
    
    def report(self):
        """Print timing report."""
        total = sum(self.timings.values())
        print(f"\n{'='*50}")
        print("TIMING REPORT")
        print(f"{'='*50}")
        for name, duration in sorted(self.timings.items(), key=lambda x: -x[1]):
            pct = (duration / total) * 100
            print(f"{name}: {duration:.2f}s ({pct:.1f}%)")
        print(f"{'='*50}")
        print(f"TOTAL: {total:.2f}s")

# Usage
profiler = SparkProfiler()
df1 = profiler.time_operation("read_data", lambda: spark.read.parquet(path))
df2 = profiler.time_operation("transform", lambda: transform(df1))
profiler.time_operation("write_data", lambda: df2.write.parquet(output))
profiler.report()
```

### Debug Logging

```python
# ✅ Enable Spark debug logging (use sparingly)
spark.sparkContext.setLogLevel("DEBUG")  # Very verbose
spark.sparkContext.setLogLevel("INFO")   # Default
spark.sparkContext.setLogLevel("WARN")   # Less verbose
spark.sparkContext.setLogLevel("ERROR")  # Errors only

# ✅ Log specific components
log4j = spark._jvm.org.apache.log4j
log4j.LogManager.getLogger("org.apache.spark.sql").setLevel(log4j.Level.DEBUG)

# ✅ View query execution details
spark.conf.set("spark.sql.planChangeLog.level", "WARN")
```

---

## 4️⃣1️⃣ DEPENDENCY MANAGEMENT

### Cluster Libraries vs Notebook Libraries

```python
# ✅ Cluster Libraries (recommended for production)
# - Install via cluster configuration
# - Available to all notebooks on cluster
# - Consistent environment

# ✅ Notebook-scoped libraries
%pip install pandas==1.5.0 numpy==1.23.0

# ✅ Multiple packages
%pip install -r /dbfs/requirements.txt

# ✅ From private PyPI
%pip install --index-url https://private-pypi.com/simple/ mypackage

# Note: Restart Python after %pip
dbutils.library.restartPython()
```

### Requirements.txt Best Practices

```python
# requirements.txt
# ✅ Pin versions for reproducibility
pandas==1.5.0
numpy==1.23.4
requests==2.28.1
great-expectations==0.15.50

# ✅ Compatible version ranges
scikit-learn>=1.0,<2.0

# ✅ Install from requirements
%pip install -r /dbfs/FileStore/requirements.txt
```

### Custom Wheel Files

```python
# ✅ Install custom wheel
%pip install /dbfs/FileStore/jars/mypackage-1.0.0-py3-none-any.whl

# ✅ Build and distribute wheel
# In development environment:
# python setup.py bdist_wheel
# Upload to DBFS: dbutils.fs.cp("file:/local/path/mypackage.whl", "dbfs:/FileStore/libs/")

# ✅ Using in notebook
import mypackage
```

### Init Scripts

```bash
#!/bin/bash
# ✅ Cluster init script for system-level dependencies

# Install system packages
apt-get update
apt-get install -y libspatialindex-dev

# Install Python packages
/databricks/python/bin/pip install rtree

# Environment variables
echo "export MY_VAR=value" >> /etc/environment
```

---

## 4️⃣2️⃣ MAGIC COMMANDS & DISPLAY

### Language Magic Commands

```python
# ✅ Run SQL
%sql
SELECT * FROM catalog.schema.table LIMIT 10

# ✅ Switch to Scala
%scala
val df = spark.read.parquet("/path")
df.show()

# ✅ Run shell commands
%sh
ls -la /dbfs/mnt/data/
pip list | grep pandas

# ✅ Markdown documentation
%md
# Section Title
This is **markdown** documentation within the notebook.

# ✅ Run another notebook
%run ./includes/utilities

# ✅ Filesystem operations
%fs
ls /mnt/data/
```

### Display Functions

```python
# ✅ Rich display
display(df)  # Interactive table with sorting/filtering

# ✅ Display with limit
display(df.limit(100))

# ✅ Display summary statistics
display(df.summary())

# ✅ Display schema
df.printSchema()

# ✅ Display as HTML
displayHTML("<h1>Custom HTML</h1><p>With styling</p>")

# ✅ Display charts
display(df)  # Then use Plot Options in UI

# ✅ Programmatic visualization with matplotlib
import matplotlib.pyplot as plt

fig, ax = plt.subplots()
pdf = df.toPandas()
pdf.plot(kind='bar', x='category', y='count', ax=ax)
display(fig)
```

### Visualization Best Practices

```python
# ✅ Aggregate before display (never display millions of rows)
display(
    df.groupBy("category")
    .agg(count("*").alias("count"), sum("amount").alias("total"))
    .orderBy(col("count").desc())
    .limit(20)
)

# ✅ Use built-in visualizations
# After display(), click the chart icon to create:
# - Bar charts
# - Line charts
# - Scatter plots
# - Maps
# - Pivot tables

# ✅ Export visualizations
# Right-click on chart -> Save as image
```

---

## 4️⃣3️⃣ ADVANCED DELTA FEATURES

### Bloom Filters

```sql
-- ✅ Create table with bloom filter
CREATE TABLE catalog.schema.orders (
    order_id STRING,
    customer_id STRING,
    amount DECIMAL(18,2)
)
USING DELTA
TBLPROPERTIES (
    'delta.dataSkippingNumIndexedCols' = '3',
    'delta.bloomFilter.enabled' = 'true',
    'delta.bloomFilter.columns' = 'order_id,customer_id',
    'delta.bloomFilter.fpp' = '0.01'  -- False positive probability
);

-- ✅ Add bloom filter to existing table
ALTER TABLE catalog.schema.orders 
SET TBLPROPERTIES (
    'delta.bloomFilter.enabled' = 'true',
    'delta.bloomFilter.columns' = 'order_id'
);
```

### Deletion Vectors

```python
# ✅ Enable deletion vectors (DBR 12.1+)
spark.sql("""
    ALTER TABLE catalog.schema.table
    SET TBLPROPERTIES ('delta.enableDeletionVectors' = 'true')
""")

# Benefits:
# - Faster DELETE operations
# - Faster UPDATE operations
# - Reduced write amplification
# - Background cleanup with VACUUM
```

### Row Tracking

```sql
-- ✅ Enable row tracking for CDC downstream
ALTER TABLE catalog.schema.orders 
SET TBLPROPERTIES (
    'delta.enableRowTracking' = 'true'
);

-- Each row gets a unique, stable ID even through updates
```

### Uniform Format (Iceberg/Hudi Compatibility)

```sql
-- ✅ Enable Iceberg compatibility
ALTER TABLE catalog.schema.orders
SET TBLPROPERTIES ('delta.universalFormat.enabledFormats' = 'iceberg');

-- ✅ Create with UniForm
CREATE TABLE catalog.schema.new_table
USING DELTA
TBLPROPERTIES ('delta.universalFormat.enabledFormats' = 'iceberg')
AS SELECT * FROM source;

-- Allows reading as Iceberg from external systems
```

### Predictive I/O

```python
# ✅ Enable predictive I/O (DBR 12.0+)
spark.conf.set("spark.databricks.io.cache.enabled", "true")
spark.conf.set("spark.databricks.io.predictiveIO.enabled", "true")

# Automatically caches frequently accessed data
# Predicts and prefetches data based on query patterns
```

---

## 4️⃣4️⃣ COMPLIANCE & GOVERNANCE

### PII Handling

```python
# ✅ Identify PII columns
PII_COLUMNS = ["email", "phone", "ssn", "credit_card", "address"]

# ✅ Mask PII for non-privileged access
def mask_pii(df: DataFrame, columns: list) -> DataFrame:
    """Mask PII columns."""
    for col_name in columns:
        if col_name in df.columns:
            df = df.withColumn(col_name, 
                when(col(col_name).isNull(), None)
                .otherwise(lit("***MASKED***"))
            )
    return df

# ✅ Hash PII for analytics
from pyspark.sql.functions import sha2

df = df.withColumn("email_hash", sha2(col("email"), 256))

# ✅ Column-level encryption
# Use Unity Catalog column masking (see Section 26)
```

### GDPR Compliance Patterns

```python
# ✅ Right to erasure (DELETE)
from delta.tables import DeltaTable

def delete_user_data(user_id: str, tables: list):
    """Delete all user data across tables."""
    for table_path in tables:
        delta_table = DeltaTable.forPath(spark, table_path)
        delta_table.delete(f"user_id = '{user_id}'")
    
    logger.info(f"Deleted data for user {user_id} from {len(tables)} tables")

# ✅ Right to access (EXPORT)
def export_user_data(user_id: str, output_path: str):
    """Export all user data."""
    user_data = spark.sql(f"""
        SELECT * FROM orders WHERE user_id = '{user_id}'
        UNION ALL
        SELECT * FROM profiles WHERE user_id = '{user_id}'
    """)
    user_data.write.format("json").mode("overwrite").save(f"{output_path}/{user_id}/")

# ✅ Data retention
def enforce_retention(table_path: str, retention_days: int):
    """Delete data older than retention period."""
    cutoff_date = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    delta_table = DeltaTable.forPath(spark, table_path)
    delta_table.delete(f"created_at < '{cutoff_date}'")
```

### Audit Logging

```python
# ✅ Unity Catalog system tables for audit
audit_df = spark.sql("""
    SELECT 
        event_time,
        action_name,
        user_identity.email as user,
        request_params,
        response.status_code
    FROM system.access.audit
    WHERE event_date >= current_date() - 7
    AND action_name IN ('getTable', 'createTable', 'deleteTable')
    ORDER BY event_time DESC
""")

# ✅ Custom audit logging
def audit_log(action: str, details: dict):
    """Log action for audit trail."""
    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user": spark.sql("SELECT current_user()").collect()[0][0],
        "notebook": dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get(),
        **details
    }
    
    # Write to audit table
    spark.createDataFrame([audit_entry]).write \
        .format("delta") \
        .mode("append") \
        .save("/mnt/audit/logs")
```

### Data Classification

```python
# ✅ Define classification levels
CLASSIFICATION = {
    "PUBLIC": ["product_name", "category", "list_price"],
    "INTERNAL": ["cost_price", "margin", "supplier"],
    "CONFIDENTIAL": ["customer_email", "address", "phone"],
    "RESTRICTED": ["ssn", "credit_card", "bank_account"]
}

# ✅ Tag tables and columns (Unity Catalog)
spark.sql("""
    ALTER TABLE catalog.schema.customers 
    SET TAGS ('classification' = 'confidential', 'contains_pii' = 'true')
""")

spark.sql("""
    ALTER TABLE catalog.schema.customers 
    ALTER COLUMN ssn SET TAGS ('pii_type' = 'ssn', 'classification' = 'restricted')
""")
```

---

## 4️⃣5️⃣ DISASTER RECOVERY & BACKUP

### Delta Table Backup Strategies

```python
# ✅ Deep clone for backup (creates independent copy)
spark.sql("""
    CREATE TABLE catalog.backup.orders_backup
    DEEP CLONE catalog.prod.orders
""")

# ✅ Shallow clone for testing (shares data files)
spark.sql("""
    CREATE TABLE catalog.dev.orders_test
    SHALLOW CLONE catalog.prod.orders
""")

# ✅ Incremental backup
spark.sql("""
    CREATE OR REPLACE TABLE catalog.backup.orders_backup
    DEEP CLONE catalog.prod.orders
""")

# ✅ Point-in-time clone
spark.sql("""
    CREATE TABLE catalog.backup.orders_20240115
    DEEP CLONE catalog.prod.orders VERSION AS OF 100
""")
```

### Cross-Region Replication

```python
# ✅ Manual replication pattern
def replicate_table(source_path: str, target_path: str, 
                   source_region: str, target_region: str):
    """Replicate Delta table across regions."""
    # Read from source
    df = spark.read.format("delta").load(source_path)
    
    # Write to target region
    df.write \
        .format("delta") \
        .mode("overwrite") \
        .option("overwriteSchema", "true") \
        .save(target_path)
    
    logger.info(f"Replicated from {source_region} to {target_region}")

# ✅ Use Azure Storage replication
# Configure geo-redundant storage (GRS) or GZRS
# Delta Lake works with Azure's built-in replication
```

### Recovery Procedures

```python
# ✅ Restore from backup
spark.sql("""
    RESTORE TABLE catalog.prod.orders 
    TO VERSION AS OF 100
""")

# ✅ Restore from clone
spark.sql("""
    CREATE OR REPLACE TABLE catalog.prod.orders
    DEEP CLONE catalog.backup.orders_backup
""")

# ✅ Point-in-time recovery
from delta.tables import DeltaTable

def recover_table(table_path: str, target_time: str):
    """Recover table to point in time."""
    # Find version at target time
    history = spark.sql(f"DESCRIBE HISTORY delta.`{table_path}`")
    target_version = history \
        .filter(col("timestamp") <= target_time) \
        .orderBy(col("timestamp").desc()) \
        .select("version") \
        .first()[0]
    
    # Restore
    delta_table = DeltaTable.forPath(spark, table_path)
    delta_table.restoreToVersion(target_version)
    
    logger.info(f"Restored to version {target_version} (time: {target_time})")
```

---

## 4️⃣6️⃣ MIGRATION PATTERNS

### Hive to Delta Migration

```python
# ✅ Convert Hive table to Delta
spark.sql("""
    CONVERT TO DELTA parquet.`/path/to/hive/table`
    PARTITIONED BY (year INT, month INT)
""")

# ✅ With schema declaration
spark.sql("""
    CONVERT TO DELTA parquet.`/path/to/table`
    NO STATISTICS
""")

# ✅ Migrate with CTAS
spark.sql("""
    CREATE TABLE catalog.schema.new_delta_table
    USING DELTA
    PARTITIONED BY (date)
    AS SELECT * FROM hive_metastore.old_db.old_table
""")

# ✅ Incremental migration
def migrate_incremental(hive_table: str, delta_table: str, key_column: str):
    """Incrementally migrate from Hive to Delta."""
    # Get max key from Delta
    try:
        max_key = spark.table(delta_table).agg(max(key_column)).collect()[0][0]
    except:
        max_key = 0  # First run
    
    # Read incremental from Hive
    increment = spark.table(hive_table).filter(col(key_column) > max_key)
    
    # Write to Delta
    increment.write.format("delta").mode("append").saveAsTable(delta_table)
```

### Databricks Runtime Upgrade

```python
# ✅ Pre-upgrade checklist
def pre_upgrade_check():
    """Check compatibility before runtime upgrade."""
    checks = []
    
    # Check Delta table versions
    for table in list_tables():
        detail = spark.sql(f"DESCRIBE DETAIL {table}").collect()[0]
        checks.append({
            "table": table,
            "min_reader": detail.minReaderVersion,
            "min_writer": detail.minWriterVersion
        })
    
    # Check deprecated features
    # Check library compatibility
    
    return checks

# ✅ Post-upgrade verification
def post_upgrade_verify():
    """Verify functionality after upgrade."""
    # Test critical notebooks
    # Verify Delta reads/writes
    # Check streaming queries
    # Validate ML models
    pass
```

### Legacy Spark to Photon

```python
# ✅ Photon compatibility checklist
# Photon works best with:
# - SQL and DataFrame operations
# - Delta Lake tables
# - Parquet files
# - Standard aggregations and joins

# Photon doesn't accelerate:
# - Python UDFs (use Pandas UDFs instead)
# - RDD operations
# - Non-standard file formats
# - Some complex nested types

# ✅ Gradual migration
# 1. Enable Photon on cluster
# 2. Test notebooks one by one
# 3. Replace UDFs with built-in functions
# 4. Monitor performance improvements
```

---

## 📋 COMPLETE OPTIMIZATION REFERENCE CARD

### Quick Commands

```python
# Performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")

# Debug
df.explain(mode="formatted")
spark.sql("DESCRIBE HISTORY table").show()
spark.sql("DESCRIBE DETAIL table").show()

# Maintenance
spark.sql("OPTIMIZE table ZORDER BY (col)")
spark.sql("VACUUM table RETAIN 168 HOURS")
spark.sql("ANALYZE TABLE table COMPUTE STATISTICS")
```

### Performance Priority Matrix

| Priority | Area | Quick Win |
|----------|------|-----------|
| 1 | Enable AQE | `spark.sql.adaptive.enabled=true` |
| 2 | Broadcast joins | `broadcast(small_df)` |
| 3 | Column pruning | Select early, filter on partitions |
| 4 | Delta optimize | Auto-optimize, Z-ORDER |
| 5 | Cache reused DFs | `.cache()`, `.unpersist()` |
| 6 | Avoid Python UDFs | Use built-in or Pandas UDFs |
| 7 | Right-size partitions | Target 128MB-256MB |
| 8 | Cluster sizing | Match to workload |

### Critical Anti-Patterns

| Anti-Pattern | Impact | Fix |
|--------------|--------|-----|
| `df.collect()` | OOM | Aggregate first |
| `for row in df` | 100x slower | DataFrame ops |
| Python UDF | 10x slower | Built-in functions |
| No caching | 2-3x slower | Cache reused DFs |
| SELECT * | Wasted I/O | Select columns |
| No partition filter | Full scan | Filter early |

---

*Last Updated: 2024 | Compatible with Databricks Runtime 12.0+ through 15.0+ | Covers Unity Catalog, DLT, Serverless, Asset Bundles, and all Azure integrations*
