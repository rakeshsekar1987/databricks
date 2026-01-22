"""
Databricks Billing Query Utility

This module provides functions to execute SQL queries on Azure Databricks
using the REST API and handle large result sets using EXTERNAL_LINKS disposition.

The EXTERNAL_LINKS disposition is required when query results exceed the inline
byte limit of ~26MB. This implementation handles chunked downloads and pagination.
"""

import requests
import json
import time
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    DoubleType, BooleanType, TimestampType, DateType, LongType
)
from pyspark.sql.functions import col as spark_col


def map_databricks_type_to_spark(databricks_type):
    """
    Map Databricks SQL type to PySpark data type
    
    Args:
        databricks_type (str): Databricks type name
    
    Returns:
        DataType: Corresponding PySpark data type
    """
    type_mapping = {
        'STRING': StringType(),
        'INT': IntegerType(),
        'INTEGER': IntegerType(),
        'BIGINT': LongType(),
        'LONG': LongType(),
        'DOUBLE': DoubleType(),
        'FLOAT': DoubleType(),
        'BOOLEAN': BooleanType(),
        'TIMESTAMP': TimestampType(),
        'DATE': DateType(),
    }
    return type_mapping.get(databricks_type.upper(), StringType())


def download_chunk_data(external_link, headers):
    """
    Download data from an external link (chunk).
    
    Args:
        external_link (dict): External link object containing the URL
        headers (dict): Request headers (may include authorization)
    
    Returns:
        list: List of rows from this chunk
    """
    # External links may have their own headers or be pre-signed URLs
    link_url = external_link.get('external_link')
    link_headers = external_link.get('http_headers', {})
    row_count = external_link.get('row_count', 'unknown')
    
    print(f"  Expected rows in chunk: {row_count}")
    print(f"  Downloading from URL: {link_url[:100]}..." if len(str(link_url)) > 100 else f"  Downloading from URL: {link_url}")
    
    # Build request headers from the external link's headers
    request_headers = {}
    if link_headers:
        # Handle different header formats from the API
        if isinstance(link_headers, dict):
            # Headers as dictionary: {"Header-Name": "value", ...}
            request_headers = link_headers.copy()
            print(f"  Using {len(request_headers)} header(s) from external link")
        elif isinstance(link_headers, list):
            # Headers as list of objects: [{"name": "Header-Name", "value": "value"}, ...]
            for header in link_headers:
                if isinstance(header, dict):
                    request_headers[header.get('name')] = header.get('value')
                elif isinstance(header, str):
                    # Skip string headers we can't parse
                    continue
            print(f"  Using {len(request_headers)} header(s) from external link")
    
    try:
        print("  Making HTTP request...")
        response = requests.get(link_url, headers=request_headers)
        print(f"  Response status code: {response.status_code}")
        response.raise_for_status()
        
        # Parse the response - it's typically newline-delimited JSON or CSV
        content_type = response.headers.get('Content-Type', '')
        print(f"  Response Content-Type: {content_type}")
        
        response_text = response.text
        print(f"  Response size: {len(response_text)} bytes")
        
        if not response_text.strip():
            print("  Warning: Empty response received")
            return []
        
        # Show first 200 chars for debugging
        print(f"  Response preview: {response_text[:200]}...")
        
        # Try parsing based on content
        response_text = response_text.strip()
        
        if 'json' in content_type.lower() or response_text.startswith('['):
            # JSON array format
            data = json.loads(response_text)
            print(f"  Parsed as JSON array: {len(data)} rows")
            return data
        elif response_text.startswith('{'):
            # Single JSON object - might be wrapped result
            data = json.loads(response_text)
            if isinstance(data, dict) and 'data_array' in data:
                print(f"  Parsed as wrapped JSON with data_array: {len(data['data_array'])} rows")
                return data['data_array']
            elif isinstance(data, list):
                print(f"  Parsed as JSON list: {len(data)} rows")
                return data
            else:
                print(f"  Warning: Unexpected JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return [data]
        else:
            # Try to parse as JSON anyway (common for Databricks responses)
            try:
                data = json.loads(response_text)
                if isinstance(data, list):
                    print(f"  Parsed as JSON: {len(data)} rows")
                    return data
                return [data]
            except json.JSONDecodeError:
                # Might be newline-delimited JSON (NDJSON) or Arrow format
                print("  Attempting to parse as newline-delimited JSON...")
                rows = []
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            print(f"  Warning: Could not parse line as JSON: {line[:50]}...")
                            continue
                print(f"  Parsed {len(rows)} rows from NDJSON")
                return rows
    except requests.exceptions.HTTPError as e:
        print(f"  HTTP Error: {e.response.status_code} - {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"  Error downloading chunk: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def fetch_all_external_data(result, headers, api_endpoint, statement_id):
    """
    Fetch all data from external links, handling pagination.
    
    Args:
        result (dict): The API response containing external links
        headers (dict): Request headers for API calls
        api_endpoint (str): Base API endpoint
        statement_id (str): The statement ID for fetching next chunks
    
    Returns:
        list: All rows from all chunks combined
    """
    all_data = []
    
    # Get the result object
    result_data = result.get('result', {})
    
    # Check if we have external links
    external_links = result_data.get('external_links', [])
    
    if external_links:
        print(f"Found {len(external_links)} external link(s) to download")
        
        for i, link in enumerate(external_links):
            print(f"Downloading chunk {i + 1}/{len(external_links)}...")
            
            # Debug: show link structure (first chunk only)
            if i == 0:
                print(f"  External link type: {type(link)}")
                if isinstance(link, dict):
                    print(f"  External link keys: {list(link.keys())}")
                    if 'http_headers' in link:
                        print(f"  HTTP headers type: {type(link.get('http_headers'))}")
            
            chunk_data = download_chunk_data(link, headers)
            if chunk_data:
                all_data.extend(chunk_data)
                print(f"  Retrieved {len(chunk_data)} rows from chunk {i + 1}")
    
    # Check if there are more chunks (pagination via next_chunk_index)
    next_chunk_index = result_data.get('next_chunk_index')
    next_chunk_internal_link = result_data.get('next_chunk_internal_link')
    
    while next_chunk_index is not None or next_chunk_internal_link:
        print(f"Fetching next chunk (index: {next_chunk_index})...")
        
        # Fetch the next chunk using the internal link or chunk endpoint
        if next_chunk_internal_link:
            chunk_url = next_chunk_internal_link
        else:
            chunk_url = f"{api_endpoint}/{statement_id}/result/chunks/{next_chunk_index}"
        
        try:
            chunk_response = requests.get(chunk_url, headers=headers)
            chunk_response.raise_for_status()
            chunk_result = chunk_response.json()
            
            # Get data from this chunk
            chunk_external_links = chunk_result.get('external_links', [])
            for link in chunk_external_links:
                chunk_data = download_chunk_data(link, headers)
                if chunk_data:
                    all_data.extend(chunk_data)
                    print(f"  Retrieved {len(chunk_data)} rows from chunk")
            
            # Also check for inline data_array in chunk
            chunk_data_array = chunk_result.get('data_array', [])
            if chunk_data_array:
                all_data.extend(chunk_data_array)
                print(f"  Retrieved {len(chunk_data_array)} rows from inline chunk data")
            
            # Update pagination pointers
            next_chunk_index = chunk_result.get('next_chunk_index')
            next_chunk_internal_link = chunk_result.get('next_chunk_internal_link')
            
        except Exception as e:
            print(f"Error fetching chunk: {str(e)}")
            break
    
    return all_data


def result_to_spark_dataframe(result, all_data=None):
    """
    Convert Databricks SQL API result to PySpark DataFrame
    
    Args:
        result (dict): The API response containing query results
        all_data (list, optional): Pre-fetched data rows (for external links)
    
    Returns:
        DataFrame: Query results as a PySpark DataFrame
    """
    # Get column schema
    schema_columns = result.get('manifest', {}).get('schema', {}).get('columns', [])
    
    # Get column names
    column_names = [col.get('name') for col in schema_columns]
    
    # Use provided data or get from inline result
    if all_data is not None:
        data_array = all_data
    else:
        result_data = result.get('result', {})
        data_array = result_data.get('data_array', [])
    
    # Create PySpark DataFrame with inferred schema (let Spark handle type conversion)
    if data_array:
        # First create DataFrame with all strings
        df = spark.createDataFrame(
            data_array, 
            schema=StructType([StructField(col, StringType(), True) for col in column_names])
        )
        
        # Then cast columns to proper types
        for col_info in schema_columns:
            col_name = col_info.get('name')
            col_type = col_info.get('type_name', '').upper()
            
            if 'TIMESTAMP' in col_type:
                df = df.withColumn(col_name, spark_col(col_name).cast('timestamp'))
            elif 'DATE' in col_type:
                df = df.withColumn(col_name, spark_col(col_name).cast('date'))
            elif col_type in ['INT', 'INTEGER']:
                df = df.withColumn(col_name, spark_col(col_name).cast('int'))
            elif col_type in ['BIGINT', 'LONG']:
                df = df.withColumn(col_name, spark_col(col_name).cast('long'))
            elif col_type in ['DOUBLE', 'FLOAT']:
                df = df.withColumn(col_name, spark_col(col_name).cast('double'))
            elif col_type == 'BOOLEAN':
                df = df.withColumn(col_name, spark_col(col_name).cast('boolean'))
        
        return df
    else:
        # Return empty DataFrame with correct schema
        fields = []
        for col in schema_columns:
            col_name = col.get('name')
            col_type = col.get('type_name')
            spark_type = map_databricks_type_to_spark(col_type)
            fields.append(StructField(col_name, spark_type, True))
        schema = StructType(fields)
        return spark.createDataFrame([], schema=schema)


def get_workspace_id():
    """
    Automatically get the current workspace ID
    
    Returns:
        str: The workspace ID
    """
    try:
        # Get workspace ID from Databricks context
        workspace_id = dbutils.notebook.entry_point.getDbutils().notebook().getContext().tags().get("orgId").get()
        return workspace_id
    except:
        try:
            # Alternative method using Spark conf
            workspace_id = spark.conf.get("spark.databricks.clusterUsageTags.clusterOwnerOrgId")
            return workspace_id
        except:
            print("Warning: Could not automatically determine workspace ID")
            return None


def execute_sql_query(sql_query, warehouse_id, use_external_links=True):
    """
    Execute a SQL query on Azure Databricks using the REST API.
    
    This function supports large result sets by using EXTERNAL_LINKS disposition,
    which downloads data in chunks instead of returning everything inline.
    
    Args:
        sql_query (str): The SQL statement to execute
        warehouse_id (str): The SQL warehouse ID to use for execution
        use_external_links (bool): Whether to use EXTERNAL_LINKS disposition 
                                   for large results (default: True)
    
    Returns:
        DataFrame: PySpark DataFrame with query results
    """
    workspace_url = "https://adb-5244115429641560.0.azuredatabricks.net"
    workspace_id = get_workspace_id()
    
    if workspace_id:
        print(f"Using workspace ID: {workspace_id}")
    
    token = dbutils.secrets.get(scope="generic-scope", key='databricks-admin-token-scrt')
    
    # API endpoint for SQL statement execution
    api_endpoint = f"{workspace_url}/api/2.0/sql/statements"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Build payload - use EXTERNAL_LINKS for large results
    payload = {
        "statement": sql_query,
        "warehouse_id": warehouse_id,
        "wait_timeout": "30s",
        "on_wait_timeout": "CONTINUE"
    }
    
    # Add disposition for handling large results
    if use_external_links:
        payload["disposition"] = "EXTERNAL_LINKS"
        payload["format"] = "JSON_ARRAY"  # Request data as JSON arrays
    
    try:
        # Submit the SQL statement
        response = requests.post(api_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        statement_id = result.get('statement_id')
        state = result.get('status', {}).get('state')
        
        print(f"Statement ID: {statement_id}")
        print(f"Initial State: {state}")
        
        # Poll for results if statement is still running
        while state in ['PENDING', 'RUNNING']:
            time.sleep(2)
            status_response = requests.get(
                f"{api_endpoint}/{statement_id}",
                headers=headers
            )
            status_response.raise_for_status()
            result = status_response.json()
            state = result.get('status', {}).get('state')
            print(f"Current State: {state}")
        
        # Check final state
        if state == 'SUCCEEDED':
            print("Query executed successfully!")
            
            # Check if we need to download external data
            result_data = result.get('result', {})
            external_links = result_data.get('external_links', [])
            
            if external_links:
                print("Large result set detected - downloading from external links...")
                all_data = fetch_all_external_data(result, headers, api_endpoint, statement_id)
                print(f"Total rows downloaded: {len(all_data)}")
                df = result_to_spark_dataframe(result, all_data)
            else:
                # Small result set - use inline data
                df = result_to_spark_dataframe(result)
            
            return df
        else:
            error_message = result.get('status', {}).get('error', {}).get('message', 'Unknown error')
            print(f"Query failed: {error_message}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        return None


def query_billing_table():
    """
    Query the comprehensive Databricks billing and usage analysis table.
    
    This function executes a complex SQL query that provides:
    - Job run costs
    - Execution times
    - Execution sources (Job/Pipeline/Notebook/SQL)
    - Cluster and warehouse details
    - Trigger types and scheduling information
    
    Returns:
        DataFrame: PySpark DataFrame with billing analysis results
    """
    # Your SQL warehouse ID
    warehouse_id = "4eee9e6d38f9665a"
    
    sql_query = """
-- ============================================================================
-- COMPREHENSIVE DATABRICKS USAGE & COST ANALYSIS QUERY (v4 - Business Focused)
-- ============================================================================
-- 
-- BUSINESS GOALS ADDRESSED:
--   1. Job run cost of a single job → total_list_cost_usd (grouped by job_run_id)
--   2. Total execution time → execution_time_minutes, execution_time_formatted
--   3. Execution source → executed_from (Job/Pipeline/Personal Notebook/SQL Warehouse)
--   4. Cluster used → cluster_name, cluster_id
--   5. Trigger type → how_was_it_triggered (Cron Schedule/Manual/Interactive/SQL Query)
--   6. Node & cluster details → node_details, cluster_size_details, warehouse_details
--
-- Filters:
--   - Date: 2025-01-01 to 2025-12-31
--   - Workspace: 5244115429641560
-- ============================================================================

WITH 
-- ============================================================================
-- CTE 1: FILTERED USAGE WITH COST
-- ============================================================================
usage_with_cost AS (
  SELECT
    u.workspace_id,
    u.record_id,
    u.billing_origin_product,
    u.sku_name,
    u.usage_metadata.job_id AS job_id,
    u.usage_metadata.job_run_id AS job_run_id,
    u.usage_metadata.job_name AS job_name_from_usage,
    u.usage_metadata.cluster_id AS cluster_id,
    u.usage_metadata.warehouse_id AS warehouse_id,
    u.usage_metadata.dlt_pipeline_id AS dlt_pipeline_id,
    u.usage_metadata.dlt_update_id AS dlt_update_id,
    u.usage_metadata.instance_pool_id AS instance_pool_id,
    u.usage_metadata.node_type AS node_type,
    u.usage_metadata.notebook_path AS notebook_path,
    u.identity_metadata.run_as AS run_as,
    u.custom_tags,
    u.product_features.is_serverless AS is_serverless,
    u.usage_start_time,
    u.usage_end_time,
    u.usage_quantity,
    u.usage_quantity * CAST(lp.pricing.default AS DECIMAL(18, 6)) AS list_cost
  FROM system.billing.usage u
  INNER JOIN system.billing.list_prices lp 
    ON u.cloud = lp.cloud 
    AND u.sku_name = lp.sku_name 
    AND u.usage_start_time >= lp.price_start_time 
    AND (u.usage_end_time <= lp.price_end_time OR lp.price_end_time IS NULL)
  WHERE 
    u.usage_date BETWEEN '2025-01-01' AND '2025-12-31'
    AND u.workspace_id = 5244115429641560
    AND u.billing_origin_product IN ('JOBS', 'ALL_PURPOSE', 'SQL', 'DLT')
),

-- ============================================================================
-- CTE 2: WORKSPACE INFO
-- ============================================================================
workspace_info AS (
  SELECT workspace_id, workspace_name, workspace_url
  FROM system.access.workspaces_latest
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 3: JOBS
-- ============================================================================
most_recent_jobs AS (
  SELECT
    workspace_id,
    job_id,
    name AS job_name,
    creator_user_name,
    run_as_user_name,
    trigger_type,
    trigger.schedule.quartz_cron_expression AS cron_schedule,
    trigger.schedule.timezone_id AS schedule_timezone,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, job_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.jobs
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 4: CLUSTERS
-- ============================================================================
most_recent_clusters AS (
  SELECT
    workspace_id,
    cluster_id,
    cluster_name,
    cluster_source,
    owned_by AS cluster_owner,
    driver_node_type,
    worker_node_type,
    worker_count,
    min_autoscale_workers,
    max_autoscale_workers,
    dbr_version,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, cluster_id ORDER BY change_time DESC) AS rn
  FROM system.compute.clusters
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 5: NODE SPECS
-- ============================================================================
node_specs AS (
  SELECT DISTINCT
    ns.node_type,
    ns.core_count,
    ns.memory_mb,
    ROUND(ns.memory_mb / 1024.0, 1) AS memory_gb
  FROM system.compute.node_types ns
),

-- ============================================================================
-- CTE 6: SQL WAREHOUSES
-- ============================================================================
warehouse_info AS (
  SELECT
    workspace_id,
    warehouse_id,
    warehouse_name,
    warehouse_type,
    warehouse_size
  FROM system.compute.warehouses
  WHERE workspace_id = 5244115429641560
),

-- ============================================================================
-- CTE 7: DLT PIPELINES
-- ============================================================================
most_recent_pipelines AS (
  SELECT
    workspace_id,
    pipeline_id,
    name AS pipeline_name,
    pipeline_type,
    created_by AS pipeline_creator,
    settings.serverless AS is_serverless_pipeline,
    ROW_NUMBER() OVER(PARTITION BY workspace_id, pipeline_id ORDER BY change_time DESC) AS rn
  FROM system.lakeflow.pipelines
  WHERE workspace_id = 5244115429641560
  QUALIFY rn = 1
),

-- ============================================================================
-- CTE 8: AGGREGATE USAGE BY RUN (Each row = one job run / one session)
-- ============================================================================
aggregated_usage AS (
  SELECT
    workspace_id,
    billing_origin_product,
    sku_name,
    job_id,
    job_run_id,
    cluster_id,
    warehouse_id,
    dlt_pipeline_id,
    dlt_update_id,
    FIRST(instance_pool_id, TRUE) AS instance_pool_id,
    FIRST(node_type, TRUE) AS node_type,
    FIRST(notebook_path, TRUE) AS notebook_path,
    FIRST(job_name_from_usage, TRUE) AS job_name_from_usage,
    FIRST(run_as, TRUE) AS run_as,
    FIRST(custom_tags, TRUE) AS custom_tags,
    FIRST(is_serverless, TRUE) AS is_serverless,
    SUM(usage_quantity) AS total_dbu,
    SUM(list_cost) AS total_list_cost,
    MIN(usage_start_time) AS execution_start_time,
    MAX(usage_end_time) AS execution_end_time,
    COUNT(DISTINCT record_id) AS usage_record_count
  FROM usage_with_cost
  GROUP BY ALL
),

-- ============================================================================
-- CTE 9: ADD EXECUTION DURATION
-- ============================================================================
usage_final AS (
  SELECT
    a.*,
    ROUND((UNIX_TIMESTAMP(a.execution_end_time) - UNIX_TIMESTAMP(a.execution_start_time)) / 60.0, 2) AS execution_time_minutes
  FROM aggregated_usage a
)

-- ============================================================================
-- FINAL SELECT - ORGANIZED BY BUSINESS PRIORITY
-- ============================================================================
SELECT
    -- Workspace
    u.workspace_id,
    w.workspace_name,
    
    -- SKU
    u.sku_name,

    -- Entity URL (clickable link for dashboards)
    CASE 
      WHEN u.job_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/jobs/', u.job_id, '" target="_blank">', 
               COALESCE(j.job_name, u.job_name_from_usage, u.job_id), '</a>')
      WHEN u.dlt_pipeline_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/pipelines/', u.dlt_pipeline_id, '" target="_blank">', 
               COALESCE(p.pipeline_name, u.dlt_pipeline_id), '</a>')
      WHEN u.warehouse_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/sql/warehouses/', u.warehouse_id, '" target="_blank">', 
               COALESCE(wh.warehouse_name, u.warehouse_id), '</a>')
      WHEN u.cluster_id IS NOT NULL THEN 
        CONCAT('<a href="', w.workspace_url, '/compute/clusters/', u.cluster_id, '" target="_blank">', 
               COALESCE(c.cluster_name, u.cluster_id), '</a>')
      ELSE NULL
    END AS entity_url,

    -- =========================================================================
    -- GOAL 1: JOB RUN COST (Cost of single job run)
    -- =========================================================================
    ROUND(u.total_list_cost, 2) AS total_list_cost_usd,
    ROUND(u.total_dbu, 4) AS total_dbu_consumed,
    
    -- =========================================================================
    -- GOAL 2: TOTAL EXECUTION TIME
    -- =========================================================================
    u.execution_time_minutes,
    ROUND(u.execution_time_minutes / 60.0, 2) AS execution_time_hours,
    CASE 
      WHEN u.execution_time_minutes IS NULL THEN 'N/A'
      WHEN u.execution_time_minutes >= 1440 THEN 
        CONCAT(FLOOR(u.execution_time_minutes / 1440), 'd ', 
               FLOOR(MOD(u.execution_time_minutes, 1440) / 60), 'h ', 
               CAST(MOD(u.execution_time_minutes, 60) AS INT), 'm')
      WHEN u.execution_time_minutes >= 60 THEN 
        CONCAT(FLOOR(u.execution_time_minutes / 60), 'h ', 
               CAST(MOD(u.execution_time_minutes, 60) AS INT), 'm')
      ELSE CONCAT(ROUND(u.execution_time_minutes, 1), 'm')
    END AS execution_time_formatted,
    u.execution_start_time,
    u.execution_end_time,
    
    -- =========================================================================
    -- GOAL 3: WHERE WAS IT EXECUTED FROM (Job/Pipeline/Personal Notebook/SQL)
    -- =========================================================================
    CASE 
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NOT NULL 
        THEN 'Scheduled/Automated Job'
      WHEN u.billing_origin_product = 'JOBS' AND u.job_run_id IS NULL 
        THEN 'Job Cluster (Ad-hoc)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NOT NULL 
        THEN 'Personal Notebook (Interactive Cluster)'
      WHEN u.billing_origin_product = 'ALL_PURPOSE' AND u.notebook_path IS NULL 
        THEN 'Interactive Cluster Session'
      WHEN u.billing_origin_product = 'SQL' 
        THEN 'SQL Warehouse Query'
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'DLT Pipeline Run'
      ELSE u.billing_origin_product
    END AS executed_from,
    
    u.notebook_path,
    
    -- Job/Pipeline Name & ID
    COALESCE(j.job_name, u.job_name_from_usage, p.pipeline_name) AS job_or_pipeline_name,
    u.job_id,
    u.job_run_id,
    u.dlt_pipeline_id,
    u.dlt_update_id,
    
    -- =========================================================================
    -- GOAL 4: WHICH CLUSTER WAS USED
    -- =========================================================================
    c.cluster_name,
    u.cluster_id,
    c.cluster_source AS cluster_created_by,  -- JOB, UI, API
    c.cluster_owner,
    c.dbr_version AS databricks_runtime,
    
    -- =========================================================================
    -- GOAL 5: HOW WAS IT TRIGGERED (Cron/Manual/Interactive/SQL)
    -- =========================================================================
    CASE
      -- Interactive cluster usage (personal notebook)
      WHEN u.billing_origin_product = 'ALL_PURPOSE' 
        THEN 'Manual - Personal Interactive Cluster'
      
      -- SQL Warehouse queries
      WHEN u.billing_origin_product = 'SQL' 
        THEN 'Manual - SQL Warehouse Query'
      
      -- DLT Pipelines
      WHEN u.billing_origin_product = 'DLT' AND p.is_serverless_pipeline = TRUE 
        THEN 'Automated - DLT Pipeline (Serverless)'
      WHEN u.billing_origin_product = 'DLT' 
        THEN 'Automated - DLT Pipeline'
      
      -- Jobs with cron schedule
      WHEN j.cron_schedule IS NOT NULL 
        THEN 'Automated - Cron Scheduled Job'
      WHEN j.trigger_type = 'CRON' 
        THEN 'Automated - Cron Scheduled Job'
      
      -- Jobs with other trigger types
      WHEN j.trigger_type = 'CONTINUOUS' 
        THEN 'Automated - Continuous Job'
      WHEN j.trigger_type = 'FILE_ARRIVAL' 
        THEN 'Automated - File Arrival Trigger'
      WHEN j.trigger_type IS NOT NULL 
        THEN CONCAT('Automated - ', j.trigger_type)
      
      -- Jobs without schedule (manual or API triggered)
      WHEN u.job_id IS NOT NULL AND j.cron_schedule IS NULL 
        THEN 'Manual - Job Run (API/UI Triggered)'
      
      -- Serverless job compute
      WHEN u.is_serverless = 'true' AND u.job_id IS NOT NULL 
        THEN 'Manual - Serverless Job Compute'
      
      ELSE 'Unknown'
    END AS how_was_it_triggered,
    
    j.cron_schedule,
    j.schedule_timezone,
    
    -- =========================================================================
    -- GOAL 6: NODE, WAREHOUSE, AND CLUSTER SIZE DETAILS
    -- =========================================================================
    
    -- Node Details
    u.node_type AS node_type_used,
    node_specs.core_count AS node_cores,
    node_specs.memory_gb AS node_memory_gb,
    
    -- Cluster Size Details (for classic compute)
    c.driver_node_type,
    driver_specs.core_count AS driver_cores,
    driver_specs.memory_gb AS driver_memory_gb,
    c.worker_node_type,
    worker_specs.core_count AS worker_cores,
    worker_specs.memory_gb AS worker_memory_gb,
    
    CASE 
      WHEN c.worker_count IS NOT NULL THEN c.worker_count
      ELSE NULL
    END AS fixed_worker_count,
    
    CASE 
      WHEN c.min_autoscale_workers IS NOT NULL 
        THEN CONCAT(c.min_autoscale_workers, ' to ', c.max_autoscale_workers)
      ELSE NULL
    END AS autoscale_worker_range,
    
    -- Total Cluster Capacity
    CASE 
      WHEN u.is_serverless = 'true' THEN 'Serverless (auto-scaled)'
      WHEN c.worker_count IS NOT NULL THEN 
        CONCAT(
          'Fixed: ', c.worker_count, ' workers | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' (', COALESCE(driver_specs.core_count, 0), ' cores, ', COALESCE(driver_specs.memory_gb, 0), ' GB) | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A'), ' (', COALESCE(worker_specs.core_count, 0), ' cores, ', COALESCE(worker_specs.memory_gb, 0), ' GB each)'
        )
      WHEN c.min_autoscale_workers IS NOT NULL THEN 
        CONCAT(
          'Autoscale: ', c.min_autoscale_workers, '-', c.max_autoscale_workers, ' workers | ',
          'Driver: ', COALESCE(c.driver_node_type, 'N/A'), ' (', COALESCE(driver_specs.core_count, 0), ' cores, ', COALESCE(driver_specs.memory_gb, 0), ' GB) | ',
          'Workers: ', COALESCE(c.worker_node_type, 'N/A'), ' (', COALESCE(worker_specs.core_count, 0), ' cores, ', COALESCE(worker_specs.memory_gb, 0), ' GB each)'
        )
      ELSE 'Unknown Configuration'
    END AS cluster_size_details,
    
    COALESCE(driver_specs.core_count, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.core_count, 0)) 
      AS total_max_cores,
    
    COALESCE(driver_specs.memory_gb, 0) + 
      (COALESCE(c.worker_count, c.max_autoscale_workers, 0) * COALESCE(worker_specs.memory_gb, 0)) 
      AS total_max_memory_gb,
    
    -- Instance Pool Details
    u.instance_pool_id,
    CASE 
      WHEN u.instance_pool_id IS NOT NULL THEN 'Yes - Using Instance Pool'
      ELSE 'No - On-Demand/Serverless'
    END AS uses_instance_pool,
    
    -- SQL Warehouse Details
    u.warehouse_id,
    wh.warehouse_name,
    wh.warehouse_type AS warehouse_type,  -- SERVERLESS, PRO, CLASSIC
    wh.warehouse_size AS warehouse_size,  -- SMALL, MEDIUM, LARGE, etc.
    CASE 
      WHEN wh.warehouse_id IS NOT NULL THEN
        CONCAT(
          'Type: ', COALESCE(wh.warehouse_type, 'N/A'), ' | ',
          'Size: ', COALESCE(wh.warehouse_size, 'N/A')
        )
      ELSE NULL
    END AS warehouse_details,
    
    -- DLT Pipeline Details
    p.pipeline_name,
    p.pipeline_type,
    p.pipeline_creator,
    
    -- =========================================================================
    -- ADDITIONAL CONTEXT
    -- =========================================================================
    
    -- Compute Type
    CASE 
      WHEN u.is_serverless = 'true' THEN 'Serverless'
      WHEN u.instance_pool_id IS NOT NULL THEN 'Pool-based'
      WHEN u.warehouse_id IS NOT NULL THEN 'SQL Warehouse'
      ELSE 'On-Demand Cluster'
    END AS compute_type,
    
    -- Identity & Tags
    u.run_as,
    j.creator_user_name AS job_creator,
    u.custom_tags,
    u.custom_tags['ClientName'] AS client_name,
    u.custom_tags['ServiceLine'] AS service_line,
    u.custom_tags['TeamName'] AS team_name,
    u.custom_tags['ENVIRONMENT'] AS environment,
    u.custom_tags['OWNER'] AS owner_tag

FROM usage_final u

-- Joins
LEFT JOIN workspace_info w 
  ON u.workspace_id = w.workspace_id

LEFT JOIN most_recent_jobs j
  ON u.job_id IS NOT NULL
  AND u.job_id = CAST(j.job_id AS STRING)

LEFT JOIN most_recent_clusters c 
  ON u.cluster_id = c.cluster_id

LEFT JOIN node_specs 
  ON u.node_type = node_specs.node_type

LEFT JOIN node_specs driver_specs 
  ON c.driver_node_type = driver_specs.node_type

LEFT JOIN node_specs worker_specs 
  ON c.worker_node_type = worker_specs.node_type

LEFT JOIN warehouse_info wh
  ON u.warehouse_id IS NOT NULL
  AND u.warehouse_id = wh.warehouse_id

LEFT JOIN most_recent_pipelines p
  ON u.dlt_pipeline_id IS NOT NULL
  AND u.dlt_pipeline_id = p.pipeline_id

ORDER BY 
  u.total_list_cost DESC, 
  u.execution_start_time DESC
LIMIT 40000;
    """

    # Execute query with EXTERNAL_LINKS disposition for large results
    result_df = execute_sql_query(sql_query, warehouse_id, use_external_links=True)
    
    if result_df is not None:
        row_count = result_df.count()
        print(f"\nQuery returned {row_count} rows")
        print(f"Columns: {result_df.columns}")
        
        # Show schema
        print("\nDataFrame Schema:")
        result_df.printSchema()
        
        # Display count
        print(f"\nTotal rows: {row_count}")
        
        return result_df
    else:
        print("Query did not return any results")
        return None


# Run the query when executed
if __name__ == "__main__":
    query_billing_table()
