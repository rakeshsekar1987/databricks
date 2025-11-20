# Cluster Sizing Examples and Calculations

This document provides cluster sizing calculations for two scenarios and recommendations for achieving the 20-minute SLA target.

## Baseline Cluster Configuration

- **Node Type**: Standard_DS3_v2 (4 vCPU, 14 GB RAM per node)
- **Workers**: 16 nodes
- **Total Cores**: 16 workers × 4 cores = **64 cores**
- **Driver**: 1 node (4 vCPU, 14 GB RAM)

## Parallelism Calculation Formula

For each table:
```
parallelism = ceil(table_size_MB / min_partition_size_MB)
parallelism = min(parallelism, max_partitions_per_table)  # Cap at 512
```

Where:
- `min_partition_size_MB` = 128 MB (default)
- `max_partitions_per_table` = 512 (default)

## Example A: 5 GB Total Data Across 500 Tables

### Assumptions
- Total data: 5,120 MB (5 GB)
- Number of tables: 500
- Average table size: ~10.24 MB per table
- Distribution: Mix of small (< 128 MB) and large tables

### Parallelism Calculation

**Small tables (< 128 MB):**
- Assume 450 tables at ~10 MB each
- Parallelism per table: ceil(10 / 128) = **1 partition**
- Total partitions: 450 × 1 = 450 partitions

**Large tables (≥ 128 MB):**
- Assume 50 tables at ~100 MB each
- Parallelism per table: ceil(100 / 128) = **1 partition**
- Total partitions: 50 × 1 = 50 partitions

**Total Partitions**: 500 partitions

### Time Estimation

**Assumptions:**
- Each core can process ~100 MB/min with good parallelism
- Network and JDBC overhead: ~20% additional time
- Concurrent table processing: Up to 500 tables (limited by cluster cores)

**Calculation:**
```
Sequential processing time = (5,120 MB / 100 MB/min) = 51.2 minutes
With 64 cores: 51.2 / 64 = 0.8 minutes (per core workload)
With overhead: 0.8 × 1.2 = 0.96 minutes ≈ 1 minute
```

**However**, with 500 tables, we need to consider:
- Concurrent table processing: min(500, 64) = 64 tables at once
- Batches: ceil(500 / 64) = 8 batches
- Time per batch: ~1 minute
- **Total estimated time: ~8-10 minutes** ✅ (Well under 20-minute SLA)

### Recommended Cluster for Example A

**Baseline cluster is SUFFICIENT:**
- 16 workers (64 cores) can handle this workload
- Autoscaling: 8-32 workers (32-128 cores) provides headroom
- **Recommendation**: Start with 16 workers, enable autoscaling to 24 workers if needed

---

## Example B: 2.5 GB Total Data Across 500 Tables

### Assumptions
- Total data: 2,560 MB (2.5 GB)
- Number of tables: 500
- Average table size: ~5.12 MB per table
- Distribution: Mostly small tables

### Parallelism Calculation

**Small tables (< 128 MB):**
- Assume 480 tables at ~5 MB each
- Parallelism per table: ceil(5 / 128) = **1 partition**
- Total partitions: 480 × 1 = 480 partitions

**Medium tables:**
- Assume 20 tables at ~20 MB each
- Parallelism per table: ceil(20 / 128) = **1 partition**
- Total partitions: 20 × 1 = 20 partitions

**Total Partitions**: 500 partitions

### Time Estimation

**Calculation:**
```
Sequential processing time = (2,560 MB / 100 MB/min) = 25.6 minutes
With 64 cores: 25.6 / 64 = 0.4 minutes (per core workload)
With overhead: 0.4 × 1.2 = 0.48 minutes ≈ 0.5 minutes
```

**With concurrent table processing:**
- Concurrent tables: min(500, 64) = 64 tables at once
- Batches: ceil(500 / 64) = 8 batches
- Time per batch: ~0.5 minutes
- **Total estimated time: ~4-5 minutes** ✅ (Well under 20-minute SLA)

### Recommended Cluster for Example B

**Baseline cluster is MORE THAN SUFFICIENT:**
- 16 workers (64 cores) easily handles this workload
- **Recommendation**: Can reduce to 12 workers (48 cores) to save costs, or keep 16 for headroom

---

## Large Table Example: Single 3 GB Table

### Scenario
- Single table: 3,072 MB (3 GB)
- Calculate parallelism: ceil(3,072 / 128) = **24 partitions**

### Time Estimation

**With 64 cores:**
```
Processing time = (3,072 MB / 100 MB/min) / 64 cores = 0.48 minutes ≈ 30 seconds
With overhead: 30 × 1.2 = 36 seconds
```

**Result**: Single large table processes in **< 1 minute** with baseline cluster ✅

---

## Scaling Recommendations

### When to Scale Up

1. **Total data > 10 GB across 500 tables**
   - Consider increasing to 24-32 workers (96-128 cores)
   - Or increase `min_partition_size_mb` to 256 MB to reduce partition overhead

2. **Many large tables (> 1 GB each)**
   - Increase `max_partitions_per_table` to 1024 (if needed)
   - Consider increasing cluster size to 32 workers

3. **Network latency issues**
   - Increase `fetch_size` to 25,000
   - Consider using self-hosted integration runtime/gateway

4. **JDBC connection timeouts**
   - Increase `connectionTimeout` and `socketTimeout` in JDBC options
   - Reduce concurrent table processing (lower `max_workers`)

### Autoscaling Strategy

**Recommended autoscaling configuration:**
```yaml
autoscaling:
  enabled: true
  min_workers: 8   # Minimum for cost efficiency
  max_workers: 32  # Maximum for peak loads
```

**Benefits:**
- Start with minimum workers for cost savings
- Scale up automatically during peak ingestion
- Scale down after completion

### Cost Optimization

1. **Use spot instances** (if available) for worker nodes
2. **Terminate cluster** after job completion (use job clusters, not all-purpose)
3. **Optimize fetch_size**: Larger fetch sizes reduce round-trips but increase memory
4. **Batch processing**: Process tables in smaller batches if memory is constrained

---

## Formula Summary

### Required Cores Calculation

```
required_cores = ceil((total_data_MB / 100) / target_minutes_SLA)
recommended_workers = ceil(required_cores / cores_per_node)
```

**Example for 20-minute SLA with 10 GB:**
```
required_cores = ceil((10,240 / 100) / 20) = ceil(5.12) = 6 cores
recommended_workers = ceil(6 / 4) = 2 workers (minimum)
```

**But for 500 concurrent tables, we need:**
```
recommended_workers = max(required_cores / cores_per_node, num_tables / tables_per_core)
```

Where `tables_per_core` ≈ 8-10 (empirical, depends on table size)

### Throughput Estimates

- **Small tables (< 128 MB)**: ~50-100 tables/minute per core
- **Large tables (≥ 128 MB)**: ~100-200 MB/minute per core
- **Network overhead**: Add 20-30% buffer
- **JDBC overhead**: Add 10-20% buffer for connection management

---

## Monitoring and Tuning

### Key Metrics to Monitor

1. **Cluster CPU utilization**: Should be 60-80% during ingestion
2. **Network I/O**: Monitor bytes/sec from SQL Server
3. **JDBC connection pool**: Monitor connection wait times
4. **Delta write performance**: Monitor write latency

### Tuning Parameters

| Parameter | Default | Tuning Guidance |
|-----------|---------|-----------------|
| `fetch_size` | 15,000 | Increase to 25,000 for large tables, decrease to 10,000 if memory constrained |
| `min_partition_size_mb` | 128 | Increase to 256 for very large clusters, decrease to 64 for small clusters |
| `max_partitions_per_table` | 512 | Increase if single tables > 64 GB |
| `max_workers` (concurrent tables) | 500 | Reduce if JDBC connection pool exhausted |

---

## Conclusion

**For both Example A (5 GB) and Example B (2.5 GB):**

✅ **Baseline cluster (16 workers, 64 cores) is SUFFICIENT** for 20-minute SLA

**Recommendations:**
1. Start with 16 workers, enable autoscaling (8-32 workers)
2. Monitor first run and adjust based on actual performance
3. For larger datasets (> 10 GB), scale to 24-32 workers
4. Use job clusters (not all-purpose) to save costs
