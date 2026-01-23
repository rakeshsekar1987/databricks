# Databricks Notebook Optimization Checklist

> Quick-reference checklist for reviewing and optimizing Azure Databricks notebooks

---

## ⚡ PERFORMANCE CHECKLIST

### Spark Configuration
- [ ] AQE (Adaptive Query Execution) enabled
- [ ] Appropriate shuffle partitions configured
- [ ] Broadcast threshold optimized for cluster memory
- [ ] Photon enabled (if available)

### Data Reading
- [ ] Only required columns selected
- [ ] Partition filters applied first
- [ ] Predicate pushdown verified
- [ ] Schema explicitly defined (avoid inference on large data)

### Joins
- [ ] Small tables broadcasted (`broadcast()`)
- [ ] Join keys have compatible types
- [ ] Null handling in join conditions
- [ ] Data skew addressed (salting if needed)

### Caching
- [ ] Multi-use DataFrames cached
- [ ] Appropriate storage level selected
- [ ] Cache unpersisted after use
- [ ] No caching of single-use DataFrames

### Partitioning
- [ ] Partition columns are low-cardinality
- [ ] Partition size targets 128MB-1GB files
- [ ] Coalesce used instead of repartition when reducing
- [ ] No over-partitioning (< 10K partitions)

---

## 🔷 DELTA LAKE CHECKLIST

### Table Configuration
- [ ] Auto-optimize enabled
- [ ] Auto-compact enabled
- [ ] Appropriate file retention configured
- [ ] Target file size set (128MB-256MB)

### Maintenance
- [ ] OPTIMIZE scheduled for frequently queried tables
- [ ] Z-ORDER on frequently filtered columns
- [ ] VACUUM with appropriate retention
- [ ] Statistics computed (ANALYZE TABLE)

### Write Patterns
- [ ] MERGE used for upserts (not delete + insert)
- [ ] Partition pruning in MERGE conditions
- [ ] Replace where for idempotent overwrites
- [ ] Schema evolution handled properly

---

## 📝 CODE QUALITY CHECKLIST

### Structure
- [ ] Notebook has clear section headers
- [ ] Configuration separated from logic
- [ ] Reusable functions defined
- [ ] No code duplication

### Documentation
- [ ] Notebook purpose documented
- [ ] Functions have docstrings
- [ ] Complex logic explained with comments
- [ ] Parameters described

### Error Handling
- [ ] Try/except blocks for external calls
- [ ] Meaningful error messages
- [ ] Retry logic for transient failures
- [ ] Graceful degradation where appropriate

### Logging
- [ ] Processing stages logged
- [ ] Row counts and metrics captured
- [ ] Errors logged with context
- [ ] Structured logging format

---

## 🔒 SECURITY CHECKLIST

- [ ] No hardcoded credentials
- [ ] Secrets from dbutils.secrets
- [ ] Appropriate table/schema permissions
- [ ] Service principals for Azure resources
- [ ] Sensitive data masked in logs

---

## 🚀 PRODUCTION READINESS CHECKLIST

### Idempotency
- [ ] Re-runs produce same result
- [ ] Checkpoint/watermark pattern implemented
- [ ] Replace where or MERGE for updates
- [ ] No duplicates on retry

### Parameterization
- [ ] Environment configurable (dev/staging/prod)
- [ ] Date/time parameters for backfills
- [ ] Widgets defined for interactive runs
- [ ] Default values sensible

### Monitoring
- [ ] Execution duration tracked
- [ ] Row count metrics logged
- [ ] Error rates monitored
- [ ] Alerts configured for failures

### Testing
- [ ] Unit tests for transformation functions
- [ ] Data quality checks implemented
- [ ] Integration tests for pipelines
- [ ] Performance benchmarks established

---

## ❌ ANTI-PATTERNS TO FIND

| Pattern to Find | Severity | Fix |
|-----------------|----------|-----|
| `.collect()` on large data | 🔴 Critical | Use aggregations/sampling |
| `for row in df.collect()` | 🔴 Critical | Use DataFrame operations |
| Multiple `.count()` calls | 🟡 Medium | Cache, count once |
| Python UDFs | 🟡 Medium | Use built-in or Pandas UDFs |
| `df.repartition(n).write` | 🟡 Medium | Use coalesce or Delta auto-optimize |
| `SELECT *` patterns | 🟡 Medium | Select specific columns |
| Hardcoded credentials | 🔴 Critical | Use secrets manager |
| No error handling | 🟡 Medium | Add try/except blocks |
| Missing partition filters | 🟡 Medium | Filter on partition columns |
| Uncached repeated reads | 🟡 Medium | Cache multi-use DataFrames |

---

## 📊 QUICK SCORING GUIDE

Rate each category 1-5 and calculate total:

| Category | Score (1-5) | Weight | Weighted Score |
|----------|-------------|--------|----------------|
| Performance | ___ | x3 | ___ |
| Code Quality | ___ | x2 | ___ |
| Error Handling | ___ | x2 | ___ |
| Security | ___ | x3 | ___ |
| Documentation | ___ | x1 | ___ |
| Testing | ___ | x2 | ___ |
| **TOTAL** | | | ___/65 |

**Score Interpretation:**
- 55-65: Production ready
- 45-54: Minor improvements needed
- 35-44: Significant refactoring required
- <35: Major rewrite recommended

---

## 🔄 OPTIMIZATION PRIORITY MATRIX

```
                    HIGH IMPACT
                         │
    ┌────────────────────┼────────────────────┐
    │  Quick Wins        │   Strategic        │
    │  • Enable AQE      │   • Restructure    │
    │  • Add caching     │     joins          │
    │  • Select columns  │   • Implement      │
    │  • Add broadcast   │     partitioning   │
LOW ├────────────────────┼────────────────────┤ HIGH
EFFORT  Technical Debt   │   Consider Later   │ EFFORT
    │  • Add docstrings  │   • Full rewrite   │
    │  • Improve naming  │   • Change         │
    │  • Add logging     │     architecture   │
    └────────────────────┼────────────────────┘
                         │
                    LOW IMPACT
```

**Start with Quick Wins → Then Strategic → Address Technical Debt → Consider Later only if needed**

---

---

## 🌊 STREAMING CHECKLIST

- [ ] Auto Loader used for file ingestion (not manual listing)
- [ ] Schema location configured for Auto Loader
- [ ] Appropriate trigger strategy selected
- [ ] Checkpointing enabled and configured
- [ ] Watermarking for late data handling
- [ ] State store optimized (RocksDB for large state)
- [ ] Rate limiting configured if needed

---

## 🖥️ CLUSTER CHECKLIST

- [ ] Appropriate cluster size for workload
- [ ] Autoscaling configured with proper min/max
- [ ] Spot instances for workers (on-demand for driver)
- [ ] Auto-termination enabled
- [ ] Photon enabled (if beneficial)
- [ ] Cluster pools for frequently used clusters
- [ ] Job clusters for scheduled workloads

---

## 💾 MEMORY CHECKLIST

- [ ] Executor memory appropriately sized
- [ ] Memory overhead configured for non-JVM memory
- [ ] GC tuning applied (if needed)
- [ ] Spill monitored and minimized
- [ ] Off-heap memory for large datasets
- [ ] No memory leaks from unclosed resources

---

## 📥 DATA INGESTION CHECKLIST

- [ ] Auto Loader or COPY INTO for file ingestion
- [ ] Schema enforcement on ingestion
- [ ] Incremental loading pattern implemented
- [ ] Error handling for bad records
- [ ] Rate limiting for external APIs
- [ ] Connection pooling for JDBC sources

---

## 🔄 SCHEMA EVOLUTION CHECKLIST

- [ ] mergeSchema enabled where needed
- [ ] Schema validation before writes
- [ ] Column mapping mode for renames
- [ ] Breaking changes handled gracefully
- [ ] Schema documented and versioned

---

## ⏱️ TIME TRAVEL CHECKLIST

- [ ] Appropriate log retention configured
- [ ] Deleted file retention set
- [ ] VACUUM scheduled with proper retention
- [ ] History queries optimized
- [ ] Restore procedures documented

---

## 💰 COST OPTIMIZATION CHECKLIST

- [ ] Spot instances utilized
- [ ] Clusters right-sized
- [ ] Auto-termination enabled
- [ ] Job clusters for scheduled work
- [ ] Storage optimized (VACUUM, compression)
- [ ] Unnecessary data archived/deleted
- [ ] Query efficiency monitored

---

## 🔀 WINDOW & AGGREGATION CHECKLIST

- [ ] Window functions partitioned (no full-data windows)
- [ ] Two-phase aggregation for skewed data
- [ ] Approximate functions for estimates
- [ ] Rollup/Cube for hierarchical aggregations
- [ ] Aggregations pushed down where possible

---

## 📊 DELTA LIVE TABLES CHECKLIST

- [ ] Expectations defined for data quality
- [ ] Appropriate table types (streaming vs materialized)
- [ ] Pipeline mode selected (triggered vs continuous)
- [ ] Error handling configured
- [ ] Quarantine pattern for bad records

---

## 🏛️ UNITY CATALOG CHECKLIST

- [ ] Three-level namespace used
- [ ] Fully qualified table names
- [ ] Row-level security where needed
- [ ] Column masking for sensitive data
- [ ] External locations properly configured
- [ ] Audit logging enabled
- [ ] Lineage tracked

---

## 🔗 EXTERNAL SOURCES CHECKLIST

- [ ] Secrets used for credentials
- [ ] Connection pooling enabled
- [ ] Timeout and retry configured
- [ ] Rate limiting implemented
- [ ] Error handling for connectivity issues
- [ ] Incremental extraction where possible

---

## 📓 ORCHESTRATION CHECKLIST

- [ ] dbutils.notebook.run for sub-notebooks
- [ ] Parallel execution where possible
- [ ] Proper error handling and propagation
- [ ] Return values used for status
- [ ] Workflows/Jobs for scheduling
- [ ] Dependencies properly defined

---

## 📈 CHANGE DATA FEED CHECKLIST

- [ ] CDF enabled on tables needing change tracking
- [ ] Change types handled correctly
- [ ] Downstream consumers updated
- [ ] Retention configured appropriately
- [ ] Incremental processing implemented

---

## 🤖 MLFLOW CHECKLIST

- [ ] Experiments organized properly
- [ ] Parameters logged
- [ ] Metrics logged
- [ ] Models registered
- [ ] Model stages managed
- [ ] Feature Store integrated (if applicable)

---

## 🔒 CONCURRENCY CHECKLIST

- [ ] Appropriate isolation level set
- [ ] Conflict retry logic implemented
- [ ] Table constraints defined
- [ ] MERGE used for safe upserts
- [ ] No race conditions in logic

---

## 🚀 SERVERLESS SQL CHECKLIST

- [ ] Queries optimized for Photon
- [ ] Materialized views for repeated queries
- [ ] Statistics up to date
- [ ] Z-ORDER on filtered columns
- [ ] No Python UDFs (not Photon-compatible)

---

## 📦 ASSET BUNDLES CHECKLIST

- [ ] Bundle structure follows best practices
- [ ] Environment-specific configurations
- [ ] CI/CD integration set up
- [ ] Service principals for production
- [ ] Validation passes before deploy

---

## 🌐 NETWORK CHECKLIST

- [ ] Shuffle compression enabled
- [ ] Appropriate timeouts configured
- [ ] Network retries implemented
- [ ] Broadcast threshold optimized
- [ ] Shuffle partitions tuned

---

## 📋 COMPLETE SCORING GUIDE (EXPANDED)

Rate each category 1-5:

| Category | Score (1-5) | Weight | Weighted |
|----------|-------------|--------|----------|
| Performance | ___ | x3 | ___ |
| Delta Lake | ___ | x3 | ___ |
| Code Quality | ___ | x2 | ___ |
| Error Handling | ___ | x2 | ___ |
| Security | ___ | x3 | ___ |
| Documentation | ___ | x1 | ___ |
| Testing | ___ | x2 | ___ |
| Streaming (if applicable) | ___ | x2 | ___ |
| Cost Optimization | ___ | x2 | ___ |
| Orchestration | ___ | x1 | ___ |
| **TOTAL** | | | ___/105 |

**Score Interpretation:**
- 90-105: Production ready, well optimized
- 75-89: Production ready, minor improvements possible
- 60-74: Needs optimization before production
- 45-59: Significant refactoring required
- <45: Major rewrite recommended

---

*Use this checklist alongside the full DATABRICKS_OPTIMIZATION_CONTEXT.md document*
