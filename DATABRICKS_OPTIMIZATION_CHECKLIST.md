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

*Use this checklist alongside the full DATABRICKS_OPTIMIZATION_CONTEXT.md document*
