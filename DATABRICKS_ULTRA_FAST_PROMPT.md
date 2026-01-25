# Databricks Notebook Optimization - Ultra-Fast Prompt

> **Use this for rapid optimization. Paste notebook after this prompt.**

---

## COPY THIS PROMPT (Optimized for Speed)

```
You are a Databricks optimization expert. Analyze and optimize the notebook below.

## FIX IN ORDER:

### 1. CRITICAL (Security/OOM)
- Replace hardcoded credentials → `dbutils.secrets.get(scope, key)`
- Replace `.collect()` on large data → aggregations or `.limit()`
- Replace `for row in df.collect()` → DataFrame transformations
- Add `checkpointLocation` to streaming writes

### 2. PERFORMANCE
Add at notebook start:
```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
spark.conf.set("spark.sql.autoBroadcastJoinThreshold", "50MB")
```

Then fix:
- Add `broadcast(small_df)` for tables <100MB
- Select only needed columns early
- Filter on partition columns first  
- Cache DFs used 2+ times: `.cache()` → use → `.unpersist()`
- Replace `@udf` with built-in functions or `@pandas_udf`
- Window: Always `Window.partitionBy().orderBy()`

### 3. DELTA LAKE
- Use MERGE for upserts (not delete+insert)
- Use `replaceWhere` for partition overwrites
- Enable schema auto-merge if needed

### 4. CODE QUALITY
- Add try/except with logging
- Use `dbutils.widgets` for parameters
- Add function docstrings

## OUTPUT:
1. Issues table: `| Severity | Issue | Cell | Fix |`
2. Refactored code (complete, runnable)
3. Expected improvement estimate

NOTEBOOK TO OPTIMIZE:
```

---

## EVEN FASTER - One-Liner Prompt

For experienced users who just need a quick review:

```
Optimize this Databricks notebook: enable AQE, fix .collect()/UDFs, add broadcast hints for small tables, cache reused DFs, add error handling, use secrets for credentials. Output: issues table + refactored code.
```

---

## FEATURE-SPECIFIC MINI-PROMPTS

### Joins Only
```
Analyze joins in this notebook. For each join: 1) Should it broadcast? 2) Is there skew? 3) Are nulls handled? Provide optimized code.
```

### Streaming Only  
```
Optimize this streaming notebook. Check: Auto Loader config, watermarking, checkpoint location, trigger strategy, state management. Provide refactored code.
```

### Delta Only
```
Optimize Delta Lake operations. Check: MERGE vs delete+insert, replaceWhere usage, Z-ORDER candidates, statistics, partition strategy. Provide recommendations with code.
```

### Security Audit
```
Security audit this notebook. Find: hardcoded credentials, exposed secrets, missing access controls, PII handling issues. Provide severity ratings and fixes.
```

### Cost Optimization
```
Analyze this notebook for cost optimization. Check: cluster sizing hints, spot instance compatibility, unnecessary shuffles, storage efficiency, caching strategy. Provide recommendations.
```

---

## RESPONSE TEMPLATE FOR CLAUDE

When optimizing, use this structure for fastest processing:

```markdown
## Issues Found

| # | Severity | Issue | Location | Fix |
|---|----------|-------|----------|-----|
| 1 | CRITICAL | ... | Cell X | ... |

## Key Changes
- Change 1: [reason]
- Change 2: [reason]

## Refactored Code

```python
# [Complete notebook code here]
```

## Expected Results
- Runtime: X min → Y min (Z% faster)
- Memory: [improvement]
- Cost: [savings estimate if applicable]
```

---

## QUICK REFERENCE CARD

### Must-Have Configurations
```python
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.databricks.delta.optimizeWrite.enabled", "true")
spark.conf.set("spark.databricks.delta.autoCompact.enabled", "true")
```

### Top 5 Fixes (80% of Performance Gains)
1. Enable AQE
2. Broadcast small tables
3. Cache reused DataFrames
4. Remove Python UDFs
5. Select columns early, filter on partitions

### Top 5 Anti-Patterns
1. `.collect()` on large data
2. `for row in df.collect()`
3. `@udf` decorator
4. `SELECT *`
5. Window without partitionBy

---

*Ultra-Fast Prompt v1.0 | Optimized for Claude efficiency*
