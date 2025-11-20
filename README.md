# SQL Server to Delta Lake Ingestion Pipeline

Production-ready ingestion solution that loads data from on-premises Microsoft SQL Server into Delta tables on Azure Databricks. Supports up to 500 tables with full and incremental load modes.

## Features

- ✅ **Full Load**: Parallelized reads for large tables (> 128 MB), normal fetch for small tables
- ✅ **Incremental Load**: Change Tracking or CDC support with idempotent Delta MERGE
- ✅ **Schema Evolution**: Automatic detection and application of schema changes
- ✅ **Concurrent Processing**: Up to 500 tables processed concurrently
- ✅ **Retry & Backoff**: Configurable retry logic with exponential backoff
- ✅ **Monitoring**: Comprehensive metrics collection and observability
- ✅ **Scalable**: Auto-scaling cluster support with parallelism calculations

## Architecture

```
┌─────────────────┐
│  SQL Server     │
│  (On-Premises)  │
└────────┬────────┘
         │ JDBC
         │
┌────────▼─────────────────────────┐
│  Azure Databricks                 │
│  ┌──────────────────────────────┐ │
│  │ ingest_master.py             │ │
│  │ (Orchestrator)               │ │
│  └──────────┬───────────────────┘ │
│             │                      │
│  ┌──────────▼───────────────────┐ │
│  │ ingest_table.py              │ │
│  │ (Per-table ingestion)        │ │
│  └──────────┬───────────────────┘ │
│             │                      │
│  ┌──────────▼───────────────────┐ │
│  │ sqlserver_utils.py           │ │
│  │ (Metadata & Change Tracking) │ │
│  └──────────────────────────────┘ │
│                                   │
│  ┌──────────────────────────────┐ │
│  │ Delta Lake Tables            │ │
│  └──────────────────────────────┘ │
└───────────────────────────────────┘
```

## Prerequisites

1. **Azure Databricks Workspace** with:
   - Delta Lake enabled
   - Access to SQL Server (network connectivity or self-hosted integration runtime)
   - Secrets scope configured for SQL Server credentials

2. **SQL Server**:
   - JDBC connectivity enabled
   - Change Tracking enabled (for incremental loads) - see setup instructions below
   - Appropriate permissions for metadata queries

3. **Required Libraries** (installed on cluster):
   - `com.microsoft.sqlserver:mssql-jdbc:12.4.2.jre8` (or later)
   - Delta Lake (included in Databricks Runtime)

4. **Storage**:
   - Mount point or direct access to Delta table storage
   - Checkpoint location for change tracking metadata

## Installation

### Step 1: Upload Files to Databricks

Upload the following files to your Databricks workspace:

```
/Workspace/
  ├── ingest_master.py
  ├── ingest_table.py
  ├── sqlserver_utils.py
  ├── config_template.yaml
  └── config.yaml (your customized configuration)
```

**Using Databricks CLI:**
```bash
databricks workspace import ingest_master.py /Workspace/ingest_master.py --language PYTHON
databricks workspace import ingest_table.py /Workspace/ingest_table.py --language PYTHON
databricks workspace import sqlserver_utils.py /Workspace/sqlserver_utils.py --language PYTHON
```

### Step 2: Configure Secrets

Create a Databricks secrets scope for SQL Server credentials:

```python
# In Databricks notebook
from pyspark.dbutils import DBUtils
dbutils = DBUtils(spark)

# Create secrets scope (one-time setup)
dbutils.secrets.createScope(
    scope="sqlserver",
    initial_manage_principal="users"
)

# Set secrets
dbutils.secrets.put(scope="sqlserver", key="username", value="your_username")
dbutils.secrets.put(scope="sqlserver", key="password", value="your_password")
```

### Step 3: Create Configuration File

Copy `config_template.yaml` to `config.yaml` and customize:

```yaml
connection:
  host: "your-sql-server.database.windows.net"
  port: 1433
  database: "SourceDatabase"
  username: "{{secrets/sqlserver/username}}"
  password: "{{secrets/sqlserver/password}}"

tables:
  - schema: "dbo"
    table: "YourTable"
    mode: "full"
    size_MB: 100
    pk_columns: ["id"]
    delta_table_path: "/mnt/delta/source/your_table"
```

### Step 4: Enable Change Tracking (for Incremental Loads)

**On SQL Server:**
```sql
-- Enable Change Tracking on database
ALTER DATABASE YourDatabase
SET CHANGE_TRACKING = ON
(CHANGE_RETENTION = 2 DAYS, AUTO_CLEANUP = ON);

-- Enable Change Tracking on specific table
ALTER TABLE dbo.YourTable
ENABLE CHANGE_TRACKING
WITH (TRACK_COLUMNS_UPDATED = ON);
```

**Verify:**
```sql
SELECT * FROM sys.change_tracking_databases;
SELECT * FROM sys.change_tracking_tables;
```

### Step 5: Create Checkpoint Table (for Incremental Loads)

The checkpoint table will be created automatically on first run, or create manually:

```sql
-- In Databricks SQL or notebook
CREATE TABLE IF NOT EXISTS delta.`/mnt/delta/checkpoints/change_tracking` (
  schema_name STRING,
  table_name STRING,
  last_version BIGINT,
  updated_at DOUBLE
) USING DELTA;
```

## Usage

### Running as Databricks Job

1. **Create Job** using `databricks_job.json`:
   ```bash
   databricks jobs create --json-file databricks_job.json
   ```

2. **Or create via UI**:
   - Go to Databricks Workspace → Jobs → Create Job
   - Set task type: Python script
   - Script path: `/Workspace/ingest_master.py`
   - Parameters: `["/Workspace/config.yaml", "500"]`
   - Configure cluster as specified in `databricks_job.json`

### Running from Notebook

```python
from ingest_master import IngestionOrchestrator

orchestrator = IngestionOrchestrator("/Workspace/config.yaml")
results = orchestrator.run(max_workers=500)

print(f"Successfully ingested {results['successful']} tables")
print(f"Failed: {results['failed']} tables")
```

### Running from Command Line

```bash
# Using Databricks CLI
databricks jobs run-now --job-id <job-id>

# Or using spark-submit (if running locally)
spark-submit ingest_master.py config.yaml 500
```

## Configuration Reference

### Connection Configuration

```yaml
connection:
  host: "sql-server-hostname"
  port: 1433
  database: "DatabaseName"
  username: "{{secrets/sqlserver/username}}"
  password: "{{secrets/sqlserver/password}}"
  auth_type: "sql_auth"  # or "kerberos", "managed_identity"
  jdbc_options:
    connectionTimeout: 30000
    encrypt: true
    trustServerCertificate: false
```

### Table Configuration

```yaml
tables:
  - schema: "dbo"
    table: "TableName"
    mode: "full"  # or "incremental"
    size_MB: 100  # Optional: will query if not provided
    pk_columns: ["id"]  # Required for incremental mode
    partition_column_hint: "id"  # Optional: numeric column for partitioning
    delta_table_path: "/mnt/delta/source/table_name"
    incremental_type: "ChangeTracking"  # or "CDC"
```

### Runtime Options

```yaml
runtime:
  fetch_size: 15000  # Records per JDBC fetch (10k-25k)
  min_partition_size_mb: 128  # Minimum partition size
  max_partitions_per_table: 512  # Maximum partitions
  retry:
    max_retries: 3
    initial_backoff_seconds: 5
    max_backoff_seconds: 60
```

## Testing Plan

### Phase 1: Single Table Test (10 minutes)

1. **Test Full Load:**
   ```yaml
   tables:
     - schema: "dbo"
       table: "TestTable"
       mode: "full"
       size_MB: 50
       pk_columns: ["id"]
       delta_table_path: "/mnt/delta/test/test_table"
   ```

2. **Verify:**
   - Data loaded correctly
   - Row count matches source
   - Schema matches source
   - Check Delta table location

3. **Test Incremental Load:**
   - Make changes in SQL Server
   - Run incremental load
   - Verify changes reflected in Delta

### Phase 2: Small Batch Test (30 minutes)

1. **Test 10 Tables:**
   - Mix of full and incremental loads
   - Mix of small and medium tables
   - Verify all tables load successfully

2. **Monitor:**
   - Cluster CPU/memory usage
   - JDBC connection pool
   - Delta write performance
   - Error logs

### Phase 3: Medium Batch Test (1 hour)

1. **Test 100 Tables:**
   - Use production-like configuration
   - Monitor for 20-minute SLA
   - Check for connection pool exhaustion
   - Verify metrics collection

### Phase 4: Full Production Test (2 hours)

1. **Test 500 Tables:**
   - Full production configuration
   - Monitor cluster autoscaling
   - Verify all tables complete within SLA
   - Review metrics and logs

### Validation Queries

**Check ingestion metrics:**
```sql
SELECT * FROM delta.`/mnt/delta/metrics/ingestion_metrics`
ORDER BY timestamp DESC
LIMIT 100;
```

**Check failed tables:**
```sql
SELECT * FROM delta.`/mnt/delta/metrics/ingestion_metrics`
WHERE status = 'failed'
ORDER BY timestamp DESC;
```

**Check table row counts:**
```sql
SELECT 
  table_name,
  COUNT(*) as row_count,
  MAX(updated_at) as last_updated
FROM delta.`/mnt/delta/source/your_table`
GROUP BY table_name;
```

## Monitoring

### Key Metrics

The pipeline collects the following metrics per table:

- `rows_read`: Number of rows ingested
- `bytes_read`: Estimated bytes read
- `elapsed_seconds`: Processing time
- `partitions_used`: Number of partitions
- `status`: "success" or "failed"
- `error_message`: Error details (if failed)

### Metrics Table Schema

```sql
CREATE TABLE IF NOT EXISTS default.ingestion_metrics (
  table STRING,
  mode STRING,
  start_time DOUBLE,
  end_time DOUBLE,
  rows_read BIGINT,
  bytes_read BIGINT,
  partitions_used INT,
  fetch_size INT,
  elapsed_seconds DOUBLE,
  status STRING,
  error_message STRING,
  ingestion_run_id DOUBLE,
  timestamp TIMESTAMP
) USING DELTA;
```

### Monitoring Dashboard Queries

**Throughput over time:**
```sql
SELECT 
  DATE_TRUNC('hour', timestamp) as hour,
  SUM(rows_read) as total_rows,
  SUM(elapsed_seconds) as total_time,
  SUM(rows_read) / SUM(elapsed_seconds) as rows_per_second
FROM delta.`/mnt/delta/metrics/ingestion_metrics`
WHERE status = 'success'
GROUP BY hour
ORDER BY hour DESC;
```

**Failed tables:**
```sql
SELECT 
  table,
  error_message,
  timestamp
FROM delta.`/mnt/delta/metrics/ingestion_metrics`
WHERE status = 'failed'
ORDER BY timestamp DESC;
```

## Troubleshooting

### Common Issues

1. **JDBC Connection Timeout**
   - Increase `connectionTimeout` and `socketTimeout` in JDBC options
   - Check network connectivity to SQL Server
   - Verify firewall rules

2. **Out of Memory Errors**
   - Reduce `fetch_size` to 10,000
   - Increase cluster worker memory
   - Reduce `max_workers` (concurrent tables)

3. **Schema Evolution Failures**
   - Check Delta table permissions
   - Verify column types are compatible
   - Review schema change logs

4. **Change Tracking Not Working**
   - Verify Change Tracking is enabled on database and table
   - Check SQL Server version (requires SQL Server 2008+)
   - Verify user has SELECT permission on change tracking functions

5. **Slow Performance**
   - Check cluster CPU utilization
   - Verify network bandwidth
   - Increase `fetch_size` if network is fast
   - Check for table locks on SQL Server

### Debug Mode

Enable detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Tuning

### For Large Tables (> 1 GB)

1. **Increase parallelism:**
   - Reduce `min_partition_size_mb` to 64 MB
   - Increase `max_partitions_per_table` to 1024

2. **Optimize fetch size:**
   - Increase `fetch_size` to 25,000
   - Monitor memory usage

3. **Cluster scaling:**
   - Increase workers to 24-32
   - Enable autoscaling

### For Many Small Tables

1. **Batch processing:**
   - Process in batches of 100 tables
   - Reduce `max_workers` to avoid connection pool exhaustion

2. **Connection pooling:**
   - Use connection pool manager
   - Reuse connections across tables

## Security Best Practices

1. **Secrets Management:**
   - Always use Databricks secrets scope
   - Never hardcode credentials
   - Rotate credentials regularly

2. **Network Security:**
   - Use VPN or private endpoint for SQL Server
   - Enable SSL/TLS encryption
   - Use self-hosted integration runtime if needed

3. **Access Control:**
   - Use service accounts with minimal permissions
   - Grant only SELECT on source tables
   - Use separate credentials for each environment

## Validation Checklist

Before running the pipeline for the first time, validate:

### Network & Connectivity
- [ ] SQL Server is accessible from Databricks cluster
- [ ] Firewall rules allow Databricks IP ranges
- [ ] Port 1433 (or custom port) is open
- [ ] SSL/TLS certificates are configured (if using encrypt=true)
- [ ] Self-hosted integration runtime is running (if using gateway)

### SQL Server Configuration
- [ ] JDBC connectivity is enabled
- [ ] SQL Server authentication is configured
- [ ] User has SELECT permission on source tables
- [ ] User has permission to query system tables (for metadata)
- [ ] Change Tracking is enabled (for incremental loads)
- [ ] SQL Server version is 2008 or later

### Databricks Configuration
- [ ] Databricks Runtime includes Delta Lake
- [ ] SQL Server JDBC driver is installed on cluster
- [ ] Secrets scope is created and populated
- [ ] Mount points are configured (if using /mnt/)
- [ ] Cluster has sufficient resources (see cluster sizing examples)

### Code & Configuration
- [ ] All Python files are uploaded to Databricks
- [ ] Configuration YAML is customized with correct values
- [ ] Delta table paths are accessible
- [ ] Checkpoint location is accessible
- [ ] Metrics location is accessible

### Testing
- [ ] Single table test passes (full load)
- [ ] Single table test passes (incremental load)
- [ ] Schema evolution test passes
- [ ] Error handling test passes (invalid table name)
- [ ] Retry logic test passes (simulated failure)

### Monitoring
- [ ] Metrics table is created
- [ ] Logging is configured
- [ ] Alerts are set up (optional)
- [ ] Dashboard queries work

## Assumptions

1. **Network Connectivity:**
   - Direct network access to SQL Server from Databricks, OR
   - Self-hosted integration runtime/gateway is available

2. **SQL Server Version:**
   - SQL Server 2008 or later (for Change Tracking)
   - SQL Server 2016 or later recommended (for better JDBC performance)

3. **Delta Lake:**
   - Delta Lake 2.0+ (included in Databricks Runtime 10.4+)
   - Write access to Delta table storage location

4. **Permissions:**
   - Read-only access to source tables
   - Write access to Delta tables
   - Metadata query permissions on SQL Server

## Support

For issues or questions:
1. Check logs in Databricks cluster driver logs
2. Review metrics table for failed tables
3. Check SQL Server error logs
4. Review troubleshooting section above

## License

This solution is provided as-is for production use. Customize as needed for your environment.
