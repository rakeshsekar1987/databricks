# Azure Databricks System Tables Schema Documentation

This document provides a comprehensive overview of the Azure Databricks system tables used for billing, compute, and job cost analysis.

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Schemas](#table-schemas)
   - [system.billing.usage](#systembillingusage)
   - [system.billing.list_prices](#systembillinglist_prices)
   - [system.compute.warehouses](#systemcomputewarehouses)
   - [system.compute.node_types](#systemcomputenode_types)
   - [system.compute.clusters](#systemcomputeclusters)
   - [system.access.workspaces_latest](#systemaccessworkspaces_latest)
   - [system.lakeflow.jobs](#systemlakeflowjobs)
   - [system.lakeflow.pipelines](#systemlakeflowpipelines)
4. [Join Relationships](#join-relationships)
5. [Common Query Patterns](#common-query-patterns)

---

## Overview

Azure Databricks provides system tables that contain operational and billing data. These tables enable you to:

- Track compute usage and costs across workspaces
- Analyze job and pipeline execution costs
- Monitor cluster and warehouse utilization
- Generate cost allocation reports by custom tags (e.g., ClientName, TeamName, ServiceLine)

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           DATABRICKS SYSTEM TABLES RELATIONSHIPS                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────────────┐
                                    │  system.billing.     │
                                    │     list_prices      │
                                    │  ─────────────────── │
                                    │  • sku_name (PK)     │
                                    │  • price_start_time  │
                                    │  • price_end_time    │
                                    │  • pricing           │
                                    └──────────┬───────────┘
                                               │ sku_name
                                               ▼
┌──────────────────────┐          ┌──────────────────────────────────────────┐
│  system.access.      │          │          system.billing.usage            │
│  workspaces_latest   │          │  ──────────────────────────────────────  │
│  ──────────────────  │◄─────────│  • record_id (PK)                        │
│  • workspace_id (PK) │workspace │  • account_id                            │
│  • workspace_name    │   _id    │  • workspace_id ─────────────────────────┼──►┌─────────────────────┐
│  • workspace_url     │          │  • sku_name ─────────────────────────────┼──►│ list_prices         │
│  • status            │          │  • usage_quantity                        │   └─────────────────────┘
└──────────────────────┘          │  • usage_metadata (contains:)            │
                                  │    - cluster_id ─────────────────────────┼──►┌─────────────────────┐
┌──────────────────────┐          │    - job_id ─────────────────────────────┼──►│ system.lakeflow.    │
│  system.compute.     │          │    - node_type ─────────────────────────┼──►│ jobs                │
│    node_types        │◄─────────│    - warehouse_id ───────────────────────┼──►└─────────────────────┘
│  ──────────────────  │ node_    │    - dlt_pipeline_id                     │
│  • node_type (PK)    │  type    │    - instance_pool_id                    │   ┌─────────────────────┐
│  • core_count        │          │    - endpoint_id                         │   │ system.compute.     │
│  • memory_mb         │          │  • custom_tags                           │   │ clusters            │
│  • gpu_count         │          │  • identity_metadata                     │◄──┼─cluster_id          │
└──────────────────────┘          │  • product_features                      │   └─────────────────────┘
                                  └──────────────────────────────────────────┘
                                               │                                 ┌─────────────────────┐
                                               │ warehouse_id                    │ system.compute.     │
                                               └────────────────────────────────►│ warehouses          │
                                                                                 └─────────────────────┘
                                                                                          
                                               │ dlt_pipeline_id                 ┌─────────────────────┐
                                               └────────────────────────────────►│ system.lakeflow.    │
                                                                                 │ pipelines           │
                                                                                 └─────────────────────┘
```

---

## Table Schemas

### system.billing.usage

**Description:** The primary billing table containing all usage records for Databricks resources. This is the central fact table for cost analysis.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Unique identifier for the Databricks account (UUID format) |
| `workspace_id` | BIGINT | Unique identifier for the workspace where usage occurred |
| `record_id` | STRING | Unique identifier for each billing record (UUID format) |
| `sku_name` | STRING | Stock Keeping Unit name identifying the product/service (e.g., `PREMIUM_JOBS_COMPUTE`, `PREMIUM_ALL_PURPOSE_COMPUTE`) |
| `cloud` | STRING | Cloud provider (`AZURE`, `AWS`, `GCP`) |
| `usage_start_time` | TIMESTAMP | Start time of the usage period |
| `usage_end_time` | TIMESTAMP | End time of the usage period |
| `usage_date` | DATE | Date of the usage (derived from usage_start_time) |
| `custom_tags` | MAP<STRING, STRING> | User-defined tags for cost allocation (e.g., `ClientName`, `TeamName`, `ServiceLine`, `ENVIRONMENT`) |
| `usage_unit` | STRING | Unit of measurement (typically `DBU` - Databricks Units) |
| `usage_quantity` | DECIMAL | Amount of resources consumed in the specified unit |
| `usage_metadata` | STRUCT | Nested structure containing resource identifiers (see below) |
| `identity_metadata` | STRUCT | Information about who triggered the usage |
| `record_type` | STRING | Type of record (`ORIGINAL`, `RETRACTION`, `RESTATEMENT`) |
| `ingestion_date` | DATE | Date when the record was ingested into the billing system |
| `billing_origin_product` | STRING | Origin product category (`JOBS`, `ALL_PURPOSE`, `SQL`, `DLT`, etc.) |
| `product_features` | STRUCT | Product feature flags and configuration |
| `usage_type` | STRING | Type of usage (`COMPUTE_TIME`, `STORAGE`, etc.) |

#### usage_metadata Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `cluster_id` | STRING | Identifier of the cluster used |
| `job_id` | STRING | Identifier of the job (if applicable) |
| `job_run_id` | STRING | Identifier of the specific job run |
| `job_name` | STRING | Name of the job |
| `node_type` | STRING | VM/instance type used (e.g., `Standard_E32ds_v4`) |
| `warehouse_id` | STRING | SQL warehouse identifier (if applicable) |
| `dlt_pipeline_id` | STRING | Delta Live Tables pipeline identifier |
| `dlt_update_id` | STRING | DLT update identifier |
| `dlt_maintenance_id` | STRING | DLT maintenance task identifier |
| `instance_pool_id` | STRING | Instance pool identifier |
| `endpoint_id` | STRING | Model serving endpoint identifier |
| `endpoint_name` | STRING | Model serving endpoint name |
| `notebook_id` | STRING | Notebook identifier |
| `notebook_path` | STRING | Full path to the notebook |
| `metastore_id` | STRING | Unity Catalog metastore identifier |
| `catalog_id` | STRING | Unity Catalog catalog identifier |
| `schema_id` | STRING | Unity Catalog schema identifier |
| `uc_table_catalog` | STRING | Unity Catalog table catalog |
| `uc_table_schema` | STRING | Unity Catalog table schema |
| `uc_table_name` | STRING | Unity Catalog table name |
| `source_region` | STRING | Source region for cross-region operations |
| `destination_region` | STRING | Destination region for cross-region operations |
| `app_id` | STRING | Databricks App identifier |
| `app_name` | STRING | Databricks App name |
| `run_name` | STRING | Run name |
| `project_id` | STRING | Project identifier |
| `database_instance_id` | STRING | Database instance identifier |
| `budget_policy_id` | STRING | Budget policy identifier |
| `usage_policy_id` | STRING | Usage policy identifier |
| `private_endpoint_name` | STRING | Private endpoint name |
| `storage_api_type` | STRING | Storage API type |
| `sharing_materialization_id` | STRING | Delta Sharing materialization ID |
| `central_clean_room_id` | STRING | Clean room identifier |
| `branch_id` | STRING | Git branch identifier |
| `index_id` | STRING | Vector search index identifier |
| `agent_bricks_id` | STRING | Agent bricks identifier |
| `ai_runtime_pool_id` | STRING | AI runtime pool identifier |
| `ai_runtime_workload_id` | STRING | AI runtime workload identifier |
| `base_environment_id` | STRING | Base environment identifier |

#### identity_metadata Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `run_as` | STRING | Identity under which the workload ran |
| `created_by` | STRING | User who created the resource |
| `owned_by` | STRING | Owner of the resource |

#### product_features Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `is_photon` | STRING | Whether Photon acceleration is enabled (`true`/`false`) |
| `is_serverless` | STRING | Whether serverless compute is used (`true`/`false`) |
| `jobs_tier` | STRING | Jobs tier (`CLASSIC`, `LIGHT`, etc.) |
| `sql_tier` | STRING | SQL warehouse tier |
| `dlt_tier` | STRING | Delta Live Tables tier |
| `serving_type` | STRING | Model serving type |
| `model_serving` | STRING | Model serving configuration |
| `networking` | STRING | Networking configuration |
| `serverless_gpu` | STRING | Serverless GPU configuration |
| `ai_runtime` | STRING | AI runtime configuration |
| `ai_functions` | STRING | AI functions configuration |
| `ai_gateway` | STRING | AI gateway configuration |
| `agent_bricks` | STRING | Agent bricks configuration |
| `apps` | STRING | Databricks Apps configuration |
| `lakebase` | STRING | Lakebase configuration |
| `lakeflow_connect` | STRING | Lakeflow Connect configuration |
| `performance_target` | STRING | Performance target configuration |

---

### system.billing.list_prices

**Description:** Contains pricing information for all Databricks SKUs over time. Prices can change, so there are multiple rows per SKU with different effective date ranges.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Unique identifier for the Databricks account |
| `price_start_time` | TIMESTAMP | Start time when this price becomes effective |
| `price_end_time` | TIMESTAMP | End time when this price expires (`-` for current price) |
| `sku_name` | STRING | Stock Keeping Unit name (join key to `usage.sku_name`) |
| `cloud` | STRING | Cloud provider (`AZURE`, `AWS`, `GCP`) |
| `currency_code` | STRING | Currency code (typically `USD`) |
| `usage_unit` | STRING | Unit of measurement (`DBU`) |
| `pricing` | STRUCT | Pricing details structure (see below) |

#### pricing Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `default` | DECIMAL | Default list price per DBU |
| `promotional.default` | DECIMAL | Promotional discount price (if applicable) |
| `effective_list.default` | DECIMAL | Effective list price after any promotions |

**Note:** When joining with `usage`, use the `price_start_time` and `price_end_time` to get the correct price for the usage period.

---

### system.compute.warehouses

**Description:** Contains information about SQL warehouses configured in the account.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `workspace_id` | BIGINT | Workspace where the warehouse is located |
| `account_id` | STRING | Account identifier |
| `warehouse_id` | STRING | Unique identifier for the warehouse |
| `warehouse_name` | STRING | Display name of the warehouse |
| `warehouse_type` | STRING | Type of warehouse (`SERVERLESS`, `PRO`, `CLASSIC`) |
| `warehouse_channel` | STRING | Update channel (`CURRENT`, `PREVIEW`) |
| `warehouse_size` | STRING | Size of the warehouse (`SMALL`, `MEDIUM`, `LARGE`, etc.) |
| `min_clusters` | INT | Minimum number of clusters for auto-scaling |
| `max_clusters` | INT | Maximum number of clusters for auto-scaling |
| `auto_stop_minutes` | INT | Minutes of inactivity before auto-stop |

**Join Key:** `usage_metadata.warehouse_id` → `warehouses.warehouse_id`

---

### system.compute.node_types

**Description:** Reference table containing specifications for all available compute node types.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Account identifier |
| `node_type` | STRING | Node type identifier (e.g., `Standard_E32ds_v4`, `Standard_D4s_v5`) |
| `core_count` | INT | Number of CPU cores |
| `memory_mb` | INT | Memory in megabytes |
| `gpu_count` | INT | Number of GPUs (0 for non-GPU instances) |

**Join Key:** `usage_metadata.node_type` → `node_types.node_type`

---

### system.compute.clusters

**Description:** Contains detailed information about all clusters created in the account, including configuration and lifecycle data.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Account identifier |
| `workspace_id` | BIGINT | Workspace where the cluster is located |
| `cluster_id` | STRING | Unique identifier for the cluster |
| `cluster_name` | STRING | Display name of the cluster |
| `owned_by` | STRING | Email/username of the cluster owner |
| `create_time` | TIMESTAMP | When the cluster was created |
| `delete_time` | TIMESTAMP | When the cluster was deleted (`-` if active) |
| `driver_node_type` | STRING | Node type for the driver node |
| `worker_node_type` | STRING | Node type for worker nodes |
| `worker_count` | INT | Fixed number of workers (null if autoscaling) |
| `min_autoscale_workers` | INT | Minimum workers for autoscaling |
| `max_autoscale_workers` | INT | Maximum workers for autoscaling |
| `auto_termination_minutes` | INT | Minutes of inactivity before auto-termination |
| `enable_elastic_disk` | BOOLEAN | Whether elastic disk is enabled |
| `tags` | MAP<STRING, STRING> | Cluster tags for cost allocation |
| `cluster_source` | STRING | Source of cluster creation (`JOB`, `UI`, `API`) |
| `init_scripts` | ARRAY<STRING> | Initialization scripts |
| `aws_attributes` | STRUCT | AWS-specific attributes (null for Azure) |
| `azure_attributes` | STRUCT | Azure-specific attributes |
| `gcp_attributes` | STRUCT | GCP-specific attributes (null for Azure) |
| `driver_instance_pool_id` | STRING | Instance pool for driver node |
| `worker_instance_pool_id` | STRING | Instance pool for worker nodes |
| `dbr_version` | STRING | Databricks Runtime version |
| `change_time` | TIMESTAMP | Last modification time |
| `change_date` | DATE | Last modification date |
| `data_security_mode` | STRING | Data security mode (`NONE`, `SINGLE_USER`, `USER_ISOLATION`) |
| `policy_id` | STRING | Cluster policy ID |

#### azure_attributes Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `first_on_demand` | STRING | Number of on-demand instances before spot |
| `availability` | STRING | Instance availability type (`ON_DEMAND_AZURE`, `SPOT_AZURE`) |
| `spot_bid_max_price` | STRING | Maximum spot bid price (`-1.0` for market price) |

**Join Key:** `usage_metadata.cluster_id` → `clusters.cluster_id`

---

### system.access.workspaces_latest

**Description:** Contains the current state of all workspaces in the account.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Account identifier |
| `workspace_id` | BIGINT | Unique identifier for the workspace |
| `workspace_name` | STRING | Display name of the workspace |
| `workspace_url` | STRING | URL to access the workspace |
| `create_time` | TIMESTAMP | When the workspace was created |
| `status` | STRING | Current status (`RUNNING`, `BANNED`, `PROVISIONING`, etc.) |

**Join Key:** `usage.workspace_id` → `workspaces_latest.workspace_id`

---

### system.lakeflow.jobs

**Description:** Contains information about Databricks Jobs (Workflows). Note: This table uses Slowly Changing Dimension (SCD) Type 2 pattern, meaning there can be multiple rows per job showing historical changes.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `account_id` | STRING | Account identifier |
| `workspace_id` | BIGINT | Workspace where the job is located |
| `job_id` | BIGINT | Unique identifier for the job |
| `name` | STRING | Display name of the job |
| `creator_id` | BIGINT | User ID of the job creator |
| `tags` | MAP<STRING, STRING> | Job tags for categorization |
| `run_as` | BIGINT | User ID under which the job runs |
| `change_time` | TIMESTAMP | When this version of the job was recorded |
| `delete_time` | TIMESTAMP | When the job was deleted (`-` if active) |
| `description` | STRING | Job description |
| `trigger` | STRUCT | Trigger configuration (see below) |
| `trigger_type` | STRING | Type of trigger (`CRON`, `CONTINUOUS`, `FILE_ARRIVAL`, etc.) |
| `run_as_user_name` | STRING | Username under which the job runs |
| `creator_user_name` | STRING | Username of the job creator |
| `paused` | BOOLEAN | Whether the job schedule is paused |
| `timeout_seconds` | INT | Job timeout (0 for no timeout) |
| `health_rules` | ARRAY<STRUCT> | Health check rules |
| `deployment` | STRUCT | Deployment configuration |
| `create_time` | TIMESTAMP | When the job was created |

#### trigger Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `continuous` | STRUCT | Continuous trigger settings |
| `file_arrival` | STRUCT | File arrival trigger settings |
| `periodic` | STRUCT | Periodic trigger settings |
| `schedule` | STRUCT | Cron schedule settings |
| `table_update` | STRUCT | Table update trigger settings |

#### schedule Substructure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `quartz_cron_expression` | STRING | Cron expression for scheduling |
| `timezone_id` | STRING | Timezone for the schedule |

**Join Key:** `usage_metadata.job_id` → `jobs.job_id` (also include `workspace_id` for uniqueness)

**Note:** To get the current version of a job, filter by `delete_time = '-'` and use `ROW_NUMBER()` or `MAX(change_time)`.

---

### system.lakeflow.pipelines

**Description:** Contains information about Delta Live Tables (DLT) pipelines.

| Column | Data Type | Description |
|--------|-----------|-------------|
| `workspace_id` | BIGINT | Workspace where the pipeline is located |
| `pipeline_id` | STRING | Unique identifier for the pipeline (UUID format) |
| `pipeline_type` | STRING | Type of pipeline (`ETL_PIPELINE`, `STREAMING`) |
| `name` | STRING | Display name of the pipeline |
| `created_by` | STRING | Email/username of the creator |
| `run_as` | STRING | Identity under which the pipeline runs |
| `tags` | MAP<STRING, STRING> | Pipeline tags |
| `settings` | STRUCT | Pipeline settings (see below) |
| `configuration` | MAP<STRING, STRING> | Pipeline configuration key-value pairs |
| `change_time` | TIMESTAMP | Last modification time |
| `delete_time` | TIMESTAMP | When deleted (`-` if active) |
| `account_id` | STRING | Account identifier |
| `create_time` | TIMESTAMP | When the pipeline was created |

#### settings Structure

| Field | Data Type | Description |
|-------|-----------|-------------|
| `continuous` | BOOLEAN | Whether the pipeline runs continuously |
| `channel` | STRING | Update channel |
| `photon` | BOOLEAN | Whether Photon is enabled |
| `edition` | STRING | DLT edition (`CORE`, `PRO`, `ADVANCED`) |
| `serverless` | BOOLEAN | Whether serverless compute is used |
| `development` | BOOLEAN | Whether in development mode |

**Join Key:** `usage_metadata.dlt_pipeline_id` → `pipelines.pipeline_id`

---

## Join Relationships

### Primary Join Keys Summary

| From Table | Join Column(s) | To Table | Target Column(s) |
|------------|----------------|----------|------------------|
| `system.billing.usage` | `sku_name` | `system.billing.list_prices` | `sku_name` (+ time range check) |
| `system.billing.usage` | `workspace_id` | `system.access.workspaces_latest` | `workspace_id` |
| `system.billing.usage` | `usage_metadata.cluster_id` | `system.compute.clusters` | `cluster_id` |
| `system.billing.usage` | `usage_metadata.node_type` | `system.compute.node_types` | `node_type` |
| `system.billing.usage` | `usage_metadata.warehouse_id` | `system.compute.warehouses` | `warehouse_id` |
| `system.billing.usage` | `usage_metadata.job_id`, `workspace_id` | `system.lakeflow.jobs` | `job_id`, `workspace_id` |
| `system.billing.usage` | `usage_metadata.dlt_pipeline_id` | `system.lakeflow.pipelines` | `pipeline_id` |

### Composite Join Considerations

1. **Workspace Scoping:** Most joins should include `workspace_id` for accuracy, as IDs may not be globally unique.

2. **Time-Based Joins:** 
   - For `list_prices`, always check that `usage_date` falls between `price_start_time` and `price_end_time`
   - For `jobs` and `clusters`, consider `change_time` for historical accuracy

3. **Account Filtering:** Always include `account_id` when querying across tables for multi-account scenarios.

---

## Common Query Patterns

### 1. Calculate Total Cost by SKU

```sql
SELECT 
    u.sku_name,
    u.billing_origin_product,
    SUM(u.usage_quantity) AS total_dbu,
    SUM(u.usage_quantity * CAST(p.pricing.effective_list.default AS DECIMAL(18,6))) AS total_cost_usd
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
    ON u.sku_name = p.sku_name
    AND u.usage_date >= DATE(p.price_start_time)
    AND (p.price_end_time = '-' OR u.usage_date < DATE(p.price_end_time))
WHERE u.usage_date >= '2024-03-01'
GROUP BY u.sku_name, u.billing_origin_product
ORDER BY total_cost_usd DESC;
```

### 2. Cost by Client and Service Line (Using Custom Tags)

```sql
SELECT 
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    SUM(u.usage_quantity) AS total_dbu,
    COUNT(DISTINCT u.usage_metadata.cluster_id) AS cluster_count,
    COUNT(DISTINCT u.usage_metadata.job_id) AS job_count
FROM system.billing.usage u
WHERE u.usage_date >= '2024-03-01'
    AND u.custom_tags['ClientName'] IS NOT NULL
GROUP BY 
    u.custom_tags['ClientName'],
    u.custom_tags['ServiceLine'],
    u.custom_tags['TeamName']
ORDER BY total_dbu DESC;
```

### 3. Job Execution Cost Analysis

```sql
SELECT 
    j.name AS job_name,
    j.creator_user_name,
    w.workspace_name,
    SUM(u.usage_quantity) AS total_dbu,
    COUNT(DISTINCT u.usage_metadata.job_run_id) AS run_count,
    AVG(u.usage_quantity) AS avg_dbu_per_record
FROM system.billing.usage u
INNER JOIN system.lakeflow.jobs j
    ON u.usage_metadata.job_id = CAST(j.job_id AS STRING)
    AND u.workspace_id = j.workspace_id
    AND j.delete_time = '-'
LEFT JOIN system.access.workspaces_latest w
    ON u.workspace_id = w.workspace_id
WHERE u.billing_origin_product = 'JOBS'
    AND u.usage_date >= '2024-03-01'
GROUP BY j.name, j.creator_user_name, w.workspace_name
ORDER BY total_dbu DESC;
```

### 4. Cluster Resource Utilization

```sql
SELECT 
    c.cluster_name,
    c.cluster_source,
    c.driver_node_type,
    c.worker_node_type,
    n.core_count AS driver_cores,
    n.memory_mb / 1024 AS driver_memory_gb,
    SUM(u.usage_quantity) AS total_dbu,
    c.tags['ClientName'] AS client_name
FROM system.billing.usage u
INNER JOIN system.compute.clusters c
    ON u.usage_metadata.cluster_id = c.cluster_id
LEFT JOIN system.compute.node_types n
    ON c.driver_node_type = n.node_type
WHERE u.usage_date >= '2024-03-01'
GROUP BY 
    c.cluster_name, c.cluster_source, 
    c.driver_node_type, c.worker_node_type,
    n.core_count, n.memory_mb, c.tags['ClientName']
ORDER BY total_dbu DESC;
```

### 5. SQL Warehouse Usage

```sql
SELECT 
    wh.warehouse_name,
    wh.warehouse_type,
    wh.warehouse_size,
    w.workspace_name,
    SUM(u.usage_quantity) AS total_dbu
FROM system.billing.usage u
INNER JOIN system.compute.warehouses wh
    ON u.usage_metadata.warehouse_id = wh.warehouse_id
LEFT JOIN system.access.workspaces_latest w
    ON u.workspace_id = w.workspace_id
WHERE u.usage_metadata.warehouse_id IS NOT NULL
    AND u.usage_date >= '2024-03-01'
GROUP BY 
    wh.warehouse_name, wh.warehouse_type, 
    wh.warehouse_size, w.workspace_name
ORDER BY total_dbu DESC;
```

### 6. Daily Cost Trend with Pricing

```sql
SELECT 
    u.usage_date,
    u.billing_origin_product,
    SUM(u.usage_quantity) AS daily_dbu,
    SUM(u.usage_quantity * CAST(p.pricing.effective_list.default AS DECIMAL(18,6))) AS daily_cost_usd
FROM system.billing.usage u
LEFT JOIN system.billing.list_prices p
    ON u.sku_name = p.sku_name
    AND u.usage_date >= DATE(p.price_start_time)
    AND (p.price_end_time = '-' OR u.usage_date < DATE(p.price_end_time))
WHERE u.usage_date >= '2024-03-01'
GROUP BY u.usage_date, u.billing_origin_product
ORDER BY u.usage_date, u.billing_origin_product;
```

### 7. Environment-Based Cost Allocation

```sql
SELECT 
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['DEPLOYMENT_ID'] AS deployment_id,
    u.billing_origin_product,
    SUM(u.usage_quantity) AS total_dbu,
    COUNT(DISTINCT u.workspace_id) AS workspace_count
FROM system.billing.usage u
WHERE u.custom_tags['ENVIRONMENT'] IS NOT NULL
    AND u.usage_date >= '2024-03-01'
GROUP BY 
    u.custom_tags['ENVIRONMENT'],
    u.custom_tags['DEPLOYMENT_ID'],
    u.billing_origin_product
ORDER BY environment, total_dbu DESC;
```

---

## Custom Tags Reference

Based on the sample data, the following custom tags are used for cost allocation:

| Tag Name | Description | Example Values |
|----------|-------------|----------------|
| `ClientName` | Client/customer name | `Goldman`, `pimco` |
| `ServiceLine` | Business service line | `Fundadmin`, `regrep` |
| `TeamName` | Team identifier | `team-goldman-fundadmin-goldfinger`, `team-goldman-regrep-eyc-reporting` |
| `ENVIRONMENT` | Deployment environment | `Production` |
| `DEPLOYMENT_ID` | Deployment identifier | `CDP003` |
| `ENGAGEMENT_ID` | Business engagement ID | `65652357` |
| `OWNER` | Resource owner email | `michael.barnes@ey.com` |

---

## Notes and Best Practices

1. **Data Freshness:** Billing data typically has a 24-48 hour delay. Check `ingestion_date` for the latest available data.

2. **Price Lookups:** Always use temporal joins with `list_prices` to get accurate pricing for historical data.

3. **Job ID Matching:** The `job_id` in `usage_metadata` is stored as STRING, while `jobs.job_id` is BIGINT. Cast appropriately when joining.

4. **SCD Type 2 Tables:** For `jobs` and `clusters`, use `delete_time = '-'` to get current records, or use window functions for point-in-time accuracy.

5. **Null Handling:** Many fields in `usage_metadata` will be null depending on the `billing_origin_product`. Always use appropriate null-safe operations.

6. **Cost Calculation:** Multiply `usage_quantity` (in DBU) by the `pricing.effective_list.default` value to get cost in the specified currency.
