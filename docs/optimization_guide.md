# Bronze Ingestion Optimization Playbook

This guide consolidates the performance, resilience, and cost-optimization techniques embedded in (or recommended alongside) the Bronze ingestion framework. Use it as a checklist when configuring clusters, tuning Spark/Delta settings, or operating pipelines under strict SLAs.

---

## 1. Delta Lake Essentials

- **Lakehouse storage**: Delta tables store data as Parquet files plus `_delta_log` transaction logs. File sizes between 16 MB and 1 GB deliver optimal read performance.
- **Auto optimize**: Enabled via table properties or session defaults.
  ```sql
  ALTER TABLE <table>
    SET TBLPROPERTIES (
      delta.autoOptimize.optimizeWrite = true,
      delta.autoOptimize.autoCompact = true
    );
  ```
  ```sql
  SET spark.databricks.delta.properties.defaults.autoOptimize.optimizeWrite = true;
  SET spark.databricks.delta.properties.defaults.autoOptimize.autoCompact = true;
  ```
- **Manual compaction**: Run `OPTIMIZE` (optionally with `ZORDER`) on dedicated maintenance clusters.
  ```sql
  OPTIMIZE catalog.schema.table
    ZORDER BY (high_cardinality_col1, high_cardinality_col2);
  ```
  - Z-Order ≤ 4 columns; choose columns frequently used in filters/joins.
- **Partitioning**: Partition only when tables exceed ~1 TB or have natural low-cardinality partition keys (e.g., `event_date`).
- **File size tuning**:
  ```sql
  ALTER TABLE catalog.schema.table
    SET TBLPROPERTIES (
      delta.targetFileSize = 134217728,
      delta.tuneFileSizesForRewrite = true
    );
  ```
- **Small-file remediation** (non-Unity Catalog):
  - Schedule OPTIMIZE + VACUUM notebooks on job clusters.
  - Avoid writing thousands of sub-MB files per run.

---

## 2. Delta Maintenance & Purging

- **VACUUM**: Remove stale files (default 7 days) on separate clusters.
  ```sql
  VACUUM catalog.schema.table;
  -- or with custom retention
  ALTER TABLE ... SET TBLPROPERTIES (delta.deletedFileRetentionDuration = 'interval 15 days');
  ```
- **CDF retention**: Framework defaults to 7 days – adjust via metadata for compliance.
- **Log retention**: Keep `delta.logRetentionDuration` aligned with data retention when auditing downstream.

---

## 3. Delta MERGE Optimization

- Keep target files smaller (16–64 MB) for merge-heavy tables (auto tune via `delta.tuneFileSizesForRewrite`).
- Filter partitions and Z-order columns in the `ON` clause to prune I/O.
- Broadcast source DataFrames ≤ 200 MB for faster merges (AQE auto-broadcast or `/*+ BROADCAST */` hints).
- Sample merge pattern with conditional deletes:
  ```sql
  MERGE INTO target AS t
  USING (SELECT * FROM source WHERE created_at >= current_date()-INTERVAL 5 DAY) AS s
  ON t.key = s.key
  WHEN MATCHED THEN UPDATE SET *
  WHEN NOT MATCHED THEN INSERT *
  WHEN NOT MATCHED BY SOURCE AND t.created_at >= current_date()-INTERVAL 5 DAY THEN DELETE;
  ```

---

## 4. Data Skipping, Pruning & Caching

- **Data skipping**: Delta automatically maintains file-level stats (first 32 columns). Control index columns via `delta.dataSkippingNumIndexedCols`.
- **Predicate pushdown**: Always filter soon after reads.
  ```python
  df = spark.read.table("catalog.schema.table").select("c1","c2").filter(col("c1") == lit("value"))
  ```
- **Partition pruning**: Provide filters on partition columns before joins.
- **Caching**:
  - Enable Delta (disk) cache: `spark.databricks.io.cache.enabled = true`.
  - Use `df.cache()` or `CACHE TABLE` only when reusing the same DataFrame multiple times in one job.
- **Intermediate results**:
  - Use temp views for single-use derived data.
  - Persist as Delta tables only when reused across actions/jobs.

---

## 5. Shuffles, Spills & Skew

### Broadcast & Join Strategies
- Prefer Broadcast Hash Join (BHJ) whenever one side < 200 MB.
  ```sql
  SET spark.sql.autoBroadcastJoinThreshold = 209715200;
  SELECT /*+ BROADCAST(dim) */ ...
  ```
- Disable broadcasting for large datasets: `SET spark.sql.autoBroadcastJoinThreshold = -1`.
- Set `spark.driver.maxResultSize` (cluster config) ≥ broadcast size but < driver memory (~8 GB for 32 GB driver).
- Prefer shuffle hash joins over sort-merge when tables are moderate:
  ```sql
  SET spark.sql.join.preferSortMergeJoin = false;
  ```

### Adaptive Query Execution (AQE)
- Enable (framework default): `spark.sql.adaptive.enabled = true`.
- Auto-optimize shuffle partitions: `SET spark.sql.shuffle.partitions = auto`.
- AQE skew optimization automatically splits skewed partitions (runtime ≥ 3.0).

### Manual Shuffle Tuning
- Use Spark UI to inspect `Shuffle Read Size` & `Spill (Disk)`.
- Rule of thumb: each shuffle task handles 128–200 MB.
- Number of partitions `N = ceil(B / 128 / T) * T` where:
  - `B` = total shuffled MB, `T` = total worker cores.

### Skew Mitigation
- Detect skew via Spark UI (hanging tasks) or `GROUP BY` diagnostics.
  ```sql
  SELECT join_key, count(*) FROM table GROUP BY join_key;
  ```
- Remedies:
  - Filter null / dominant values pre-join.
  - Use skew hints: `SELECT /*+ SKEW('table','column',(v1,v2)) */ ...`.
  - Duplicate skewed keys with salts before joins.

### Spill Avoidance
- Increase `spark.sql.shuffle.partitions`.
- Use larger worker nodes (more RAM per core) for shuffle-heavy jobs.
- Keep `spark.memory.fraction` defaults unless workloads require fine-tune.

---

## 6. Data Skipping, Partitioning & Pruning Recap

| Technique | Benefit | Config |
|-----------|---------|--------|
| Delta data skipping | Skip non-qualifying files based on min/max stats | `delta.dataSkippingNumIndexedCols` |
| Predicate pushdown | Filter at source | `.filter()` ASAP / `WHERE` clause |
| Partition pruning | Avoid scanning irrelevant partitions | Filter on partition columns before join |

---

## 7. Caching & Persisting Intermediate Results

- **Delta cache**: Ideal for repeated reads of large tables; requires storage-optimized nodes.
- **Spark cache/persist**:
  ```python
  df = heavy_df.persist()
  df.count(); df.write.format("delta").save(...)
  ```
  Use only when multiple actions operate on the same lineage.
- **Temp views**: `CREATE OR REPLACE TEMP VIEW` for single-session reuse without disk writes.

---

## 8. Data Purging & Retention

- Align `delta.deletedFileRetentionDuration` with compliance (default 7 days).
- DAT/Bronze retention plan:
  - Bronze CDF retention = 7 days (framework default).
  - Weekly `VACUUM` job (autoscaling 1–4 workers).
  - Combine with `OPTIMIZE` for file compaction.

---

## 9. Databricks Cluster Tuning

### Cluster Types
- **All-purpose**: ad-hoc exploration; enable autoscaling (min=1) for dev/test.
- **Job clusters**: production pipelines; fix min workers > 1 for SLA stability.

### Instance Families
- Memory-optimized: ML, heavy shuffles, caching.
- Compute-optimized: ETL/ELT with full scans, OPTIMIZE/ZORDER jobs.
- Storage-optimized: Delta cache, analytic workloads.
- GPU-optimized: Deep learning/hybrid tasks.
- General purpose: Default; run VACUUM or light ETL.

### Worker Counts
- Start 2–4 workers (small), 8–10 (medium/large).
- Scale with shuffle partition tuning; ensure > 80 % utilization (Ganglia/Cluster metrics).

### Autoscaling & Pools
- Enable autoscaling for interactive clusters; set higher minimums in prod.
- Use instance pools for faster spin-up & cost savings (idle instances billed as VM only).

### Photon
- Enable for:
  - MERGE-heavy ETL
  - Large scans, joins, aggregations
  - Auto Loader & streaming pipelines

### Spot Instances
- Suitable for dev/adhoc workloads; avoid for drivers and SLA-critical jobs.

### Housekeeping
- Restart all-purpose clusters weekly.
- Use latest LTS Databricks Runtime.
- Configure `spark.driver.maxResultSize`, `spark.sql.autoBroadcastJoinThreshold`, etc., in cluster advanced options.
- Tag clusters for cost attribution.

---

## 10. Putting It Into Practice

1. **Before running ingestion**:
   - Validate metadata (partition hints, DQ tolerances, concurrency weights).
   - Choose cluster profile (num workers, node family, Photon).
   - Ensure AQE + auto optimize + Delta cache configs set (framework defaults).
2. **During runs**:
   - Monitor Spark UI for skew/spills; adjust shuffle partitions or hints.
   - Inspect Log Analytics dashboards fed by `StructuredLogger`.
3. **After runs**:
    - Use benchmark tables to confirm SLA compliance.
   - Schedule OPTIMIZE + VACUUM notebooks per data domain.
   - Update metadata (e.g., `delta.targetFileSize`, `max_parallelism`) if patterns change.

Following this guide ensures the Bronze ingestion framework stays performant, cost-efficient, and compliant as data volumes and source diversity grow.
