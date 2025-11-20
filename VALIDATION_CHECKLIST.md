# First-Time Run Validation Checklist

Use this checklist before running the ingestion pipeline for the first time in production.

## Pre-Flight Checks

### Network & Connectivity
- [ ] **SQL Server Accessibility**
  - Test connection from Databricks cluster: `telnet <sql-server-host> 1433`
  - Verify firewall rules allow Databricks IP ranges
  - Check if VPN or private endpoint is required

- [ ] **Port Configuration**
  - Default port 1433 is open, OR
  - Custom port is configured in `config.yaml`
  - SSL/TLS port (if using encrypted connection)

- [ ] **Gateway/Integration Runtime** (if applicable)
  - Self-hosted integration runtime is installed and running
  - Gateway hostname/port configured in `config.yaml`
  - Gateway has network access to SQL Server

### SQL Server Configuration

- [ ] **JDBC Connectivity**
  - SQL Server Browser service is running (if using named instances)
  - TCP/IP protocol is enabled in SQL Server Configuration Manager
  - SQL Server is listening on correct IP address

- [ ] **Authentication**
  - SQL Server authentication is enabled (if using SQL auth)
  - Windows authentication configured (if using Kerberos)
  - Service account has been created with appropriate permissions

- [ ] **Permissions**
  - Service account has `SELECT` permission on all source tables
  - Service account can query system tables (`sys.tables`, `sys.columns`, etc.)
  - Service account has permission to use Change Tracking functions (for incremental loads)
  - Service account has `VIEW CHANGE TRACKING STATE` permission (for incremental loads)

- [ ] **Change Tracking** (for incremental loads)
  - Change Tracking is enabled on database: `ALTER DATABASE ... SET CHANGE_TRACKING = ON`
  - Change Tracking is enabled on tables: `ALTER TABLE ... ENABLE CHANGE_TRACKING`
  - Verify: `SELECT * FROM sys.change_tracking_tables`
  - Retention period is appropriate (default: 2 days)

- [ ] **SQL Server Version**
  - SQL Server 2008 or later (for Change Tracking)
  - SQL Server 2016+ recommended for better JDBC performance
  - Verify: `SELECT @@VERSION`

### Databricks Configuration

- [ ] **Cluster Setup**
  - Cluster is created with appropriate node type and worker count
  - Autoscaling is configured (if using)
  - Cluster has sufficient resources (see `cluster_sizing_examples.md`)

- [ ] **Libraries Installed**
  - SQL Server JDBC driver: `com.microsoft.sqlserver:mssql-jdbc:12.4.2.jre8`
  - Delta Lake (included in Databricks Runtime 10.4+)
  - Verify libraries are attached to cluster

- [ ] **Secrets Configuration**
  - Secrets scope is created: `dbutils.secrets.listScopes()`
  - Username is stored: `dbutils.secrets.get(scope="sqlserver", key="username")`
  - Password is stored: `dbutils.secrets.get(scope="sqlserver", key="password")`
  - Secrets scope name matches configuration file

- [ ] **Storage Access**
  - Delta table paths are accessible (mount points or direct paths)
  - Checkpoint location is accessible: `/mnt/delta/checkpoints/change_tracking`
  - Metrics location is accessible: `/mnt/delta/metrics/ingestion_metrics`
  - Write permissions on all storage locations

- [ ] **Mount Points** (if using `/mnt/`)
  - Mount points are configured: `dbutils.fs.mounts()`
  - Mount points are accessible: `dbutils.fs.ls("/mnt/delta")`
  - Mount points have appropriate permissions

### Code & Configuration

- [ ] **Files Uploaded**
  - `ingest_master.py` is in Databricks workspace
  - `ingest_table.py` is in Databricks workspace
  - `sqlserver_utils.py` is in Databricks workspace
  - `config.yaml` is customized and uploaded

- [ ] **Configuration Validation**
  - All connection details are correct (host, port, database)
  - Table list is accurate (schema, table names)
  - Delta table paths are valid and accessible
  - Primary key columns are correct for each table
  - Partition column hints are correct (if specified)

- [ ] **Path Validation**
  - Delta table paths don't conflict with existing tables
  - Checkpoint path is dedicated for this pipeline
  - Metrics path is accessible

### Testing

- [ ] **Single Table Test**
  - Create test config with 1 small table
  - Run full load: `python ingest_master.py test_config.yaml 1`
  - Verify data loaded correctly
  - Verify row count matches source
  - Verify schema matches source

- [ ] **Incremental Load Test** (if using)
  - Run initial full load
  - Make changes in SQL Server (insert, update, delete)
  - Run incremental load
  - Verify changes are reflected in Delta table
  - Verify checkpoint is updated

- [ ] **Schema Evolution Test**
  - Add a column to source table in SQL Server
  - Run ingestion
  - Verify new column appears in Delta table
  - Verify existing data is preserved

- [ ] **Error Handling Test**
  - Test with invalid table name (should fail gracefully)
  - Test with invalid credentials (should fail with clear error)
  - Verify retry logic works (simulate temporary failure)

### Monitoring Setup

- [ ] **Metrics Collection**
  - Metrics table location is accessible
  - Verify metrics are written after test run
  - Query metrics: `SELECT * FROM delta.\`/mnt/delta/metrics/ingestion_metrics\``

- [ ] **Logging**
  - Cluster logs are accessible
  - Log level is appropriate (INFO for production)
  - Logs contain useful information for troubleshooting

- [ ] **Alerts** (optional)
  - Email notifications configured in Databricks job
  - Alert on failure is enabled
  - Alert on slow table is configured (if applicable)

## Production Readiness

### Performance Validation

- [ ] **Cluster Sizing**
  - Cluster has sufficient cores for target parallelism
  - Memory is adequate (check cluster metrics during test)
  - Network bandwidth is sufficient

- [ ] **SLA Validation**
  - Test run completes within target time (20 minutes for 500 tables)
  - Individual tables complete within timeout (30 minutes per table)
  - No connection pool exhaustion

- [ ] **Resource Utilization**
  - CPU utilization is 60-80% during ingestion (not 100%)
  - Memory usage is within limits
  - Network I/O is not saturated

### Operational Readiness

- [ ] **Documentation**
  - Runbook is documented
  - Troubleshooting guide is available
  - Contact information for support is documented

- [ ] **Backup & Recovery**
  - Delta table backups are configured (if required)
  - Checkpoint table is backed up (for incremental loads)
  - Recovery procedure is documented

- [ ] **Security Review**
  - Credentials are stored in secrets (not hardcoded)
  - Network traffic is encrypted (SSL/TLS)
  - Access controls are appropriate
  - Audit logging is enabled (if required)

## First Production Run

### Pre-Run

- [ ] Notify stakeholders of ingestion start time
- [ ] Verify SQL Server is not under maintenance
- [ ] Check cluster is available and healthy
- [ ] Review recent changes to source tables (if any)

### During Run

- [ ] Monitor cluster metrics (CPU, memory, network)
- [ ] Monitor Databricks job status
- [ ] Watch for errors in cluster logs
- [ ] Check SQL Server for locks or blocking queries

### Post-Run

- [ ] Verify all tables completed successfully
- [ ] Review metrics table for any warnings
- [ ] Spot-check data quality (row counts, sample data)
- [ ] Verify checkpoint table is updated (for incremental)
- [ ] Review performance metrics (time, throughput)
- [ ] Document any issues or anomalies

## Troubleshooting Quick Reference

| Issue | Check |
|-------|-------|
| Connection timeout | Firewall rules, network connectivity, SQL Server status |
| Authentication failed | Credentials in secrets, SQL auth enabled, permissions |
| Change Tracking not working | CT enabled on DB and table, permissions, SQL Server version |
| Out of memory | Reduce fetch_size, increase cluster memory, reduce concurrent tables |
| Slow performance | Check network bandwidth, increase cluster size, optimize fetch_size |
| Schema evolution failed | Delta table permissions, column type compatibility |

## Emergency Contacts

- **Databricks Admin**: ________________
- **SQL Server DBA**: ________________
- **Network Team**: ________________
- **On-Call Engineer**: ________________

---

**Last Updated**: _______________
**Validated By**: _______________
