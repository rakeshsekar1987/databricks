# Azure Databricks Notebook Optimization Context Prompt

> **Purpose**: This document serves as a comprehensive context prompt for optimizing Azure Databricks notebooks. Use this as a reference guide when reviewing and refactoring notebooks for production readiness.

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

*Last Updated: 2024 | Compatible with Databricks Runtime 13.0+*
