# Databricks notebook source
# MAGIC %md
# MAGIC # Azure Databricks Job Run Logs Retriever
# MAGIC 
# MAGIC This notebook retrieves the output logs of a Databricks job run using the REST API.
# MAGIC 
# MAGIC **Job Details:**
# MAGIC - Job ID: 133166337001904
# MAGIC - Job Run ID: 584498514062775
# MAGIC - Task Run ID: 87528399080853

# COMMAND ----------

import requests
import json
import time

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Configuration - Update these values as needed
WORKSPACE_URL = "https://adb-5244115429641560.0.azuredatabricks.net"
JOB_ID = "133166337001904"
JOB_RUN_ID = "584498514062775"
TASK_RUN_ID = "87528399080853"

# Get token from Databricks secrets
TOKEN = dbutils.secrets.get(scope="generic-scope", key='databricks-admin-token-scrt')

# COMMAND ----------

# MAGIC %md
# MAGIC ## API Functions

# COMMAND ----------

def get_job_run_output(run_id, workspace_url=WORKSPACE_URL, token=TOKEN):
    """
    Get the output of a job run using the Databricks REST API
    
    API: GET /api/2.1/jobs/runs/get-output
    
    Args:
        run_id (str): The run ID to get output for
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
    
    Returns:
        dict: The job run output response containing:
            - notebook_output: Result from notebook (if notebook task)
            - logs: Standard output logs
            - error: Error message if failed
            - error_trace: Stack trace if failed
            - metadata: Run metadata including run_page_url
    """
    api_endpoint = f"{workspace_url}/api/2.1/jobs/runs/get-output"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "run_id": run_id
    }
    
    try:
        response = requests.get(api_endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

# COMMAND ----------

def get_job_run_details(run_id, workspace_url=WORKSPACE_URL, token=TOKEN):
    """
    Get the details of a job run using the Databricks REST API
    
    API: GET /api/2.1/jobs/runs/get
    
    Args:
        run_id (str): The run ID to get details for
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
    
    Returns:
        dict: The job run details including state, tasks, cluster info
    """
    api_endpoint = f"{workspace_url}/api/2.1/jobs/runs/get"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "run_id": run_id
    }
    
    try:
        response = requests.get(api_endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

# COMMAND ----------

def get_cluster_events(cluster_id, workspace_url=WORKSPACE_URL, token=TOKEN, limit=100):
    """
    Get cluster events/logs for a specific cluster
    
    API: POST /api/2.0/clusters/events
    
    Args:
        cluster_id (str): The cluster ID
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
        limit (int): Maximum number of events to retrieve
    
    Returns:
        dict: The cluster events response
    """
    api_endpoint = f"{workspace_url}/api/2.0/clusters/events"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "cluster_id": cluster_id,
        "limit": limit
    }
    
    try:
        response = requests.post(api_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

# COMMAND ----------

def export_run(run_id, workspace_url=WORKSPACE_URL, token=TOKEN, views_to_export="ALL"):
    """
    Export and retrieve the job run views (notebooks, dashboards)
    
    API: GET /api/2.1/jobs/runs/export
    
    Args:
        run_id (str): The run ID to export
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
        views_to_export (str): Which views to export (CODE, DASHBOARDS, ALL)
    
    Returns:
        dict: The exported run response with views
    """
    api_endpoint = f"{workspace_url}/api/2.1/jobs/runs/export"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "run_id": run_id,
        "views_to_export": views_to_export
    }
    
    try:
        response = requests.get(api_endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
        return None

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Get Job Run Details

# COMMAND ----------

print("=" * 80)
print("FETCHING JOB RUN DETAILS")
print("=" * 80)
print(f"Job Run ID: {JOB_RUN_ID}")
print()

run_details = get_job_run_details(JOB_RUN_ID)

if run_details:
    print(f"Run Name: {run_details.get('run_name', 'N/A')}")
    print(f"Life Cycle State: {run_details.get('state', {}).get('life_cycle_state', 'N/A')}")
    print(f"Result State: {run_details.get('state', {}).get('result_state', 'N/A')}")
    print(f"Run Page URL: {run_details.get('run_page_url', 'N/A')}")
    
    # Show task details
    tasks = run_details.get('tasks', [])
    if tasks:
        print(f"\nNumber of Tasks: {len(tasks)}")
        for task in tasks:
            print(f"\n  Task Key: {task.get('task_key', 'N/A')}")
            print(f"  Run ID: {task.get('run_id', 'N/A')}")
            print(f"  State: {task.get('state', {}).get('life_cycle_state', 'N/A')}")
            print(f"  Result: {task.get('state', {}).get('result_state', 'N/A')}")
else:
    print("Failed to fetch run details")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Get Job Run Output (Main Run)

# COMMAND ----------

print("=" * 80)
print("FETCHING JOB RUN OUTPUT")
print("=" * 80)
print(f"Job Run ID: {JOB_RUN_ID}")
print()

run_output = get_job_run_output(JOB_RUN_ID)

if run_output:
    # Notebook output
    notebook_output = run_output.get('notebook_output', {})
    if notebook_output:
        print("NOTEBOOK OUTPUT:")
        print("-" * 40)
        result = notebook_output.get('result', 'No result')
        print(f"Result: {result}")
        if notebook_output.get('truncated'):
            print("(Output was truncated)")
        print()
    
    # Logs
    logs = run_output.get('logs', '')
    if logs:
        print("LOGS:")
        print("-" * 40)
        print(logs)
        print()
    
    # Error information
    error = run_output.get('error', '')
    if error:
        print("ERROR:")
        print("-" * 40)
        print(error)
        print()
    
    error_trace = run_output.get('error_trace', '')
    if error_trace:
        print("ERROR TRACE:")
        print("-" * 40)
        print(error_trace)
        print()
    
    # Metadata
    metadata = run_output.get('metadata', {})
    if metadata:
        print("METADATA:")
        print("-" * 40)
        print(f"Run Page URL: {metadata.get('run_page_url', 'N/A')}")
else:
    print("Failed to fetch run output")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Get Task Run Output

# COMMAND ----------

print("=" * 80)
print("FETCHING TASK RUN OUTPUT")
print("=" * 80)
print(f"Task Run ID: {TASK_RUN_ID}")
print()

task_output = get_job_run_output(TASK_RUN_ID)

if task_output:
    # Notebook output
    notebook_output = task_output.get('notebook_output', {})
    if notebook_output:
        print("NOTEBOOK OUTPUT:")
        print("-" * 40)
        result = notebook_output.get('result', 'No result')
        print(f"Result: {result}")
        if notebook_output.get('truncated'):
            print("(Output was truncated)")
        print()
    
    # Logs
    logs = task_output.get('logs', '')
    if logs:
        print("TASK LOGS:")
        print("-" * 40)
        print(logs)
        print()
    
    # SQL output (for SQL tasks)
    sql_output = task_output.get('sql_output', {})
    if sql_output:
        print("SQL OUTPUT:")
        print("-" * 40)
        print(json.dumps(sql_output, indent=2))
        print()
    
    # Error information
    error = task_output.get('error', '')
    if error:
        print("ERROR:")
        print("-" * 40)
        print(error)
        print()
    
    error_trace = task_output.get('error_trace', '')
    if error_trace:
        print("ERROR TRACE:")
        print("-" * 40)
        print(error_trace)
        print()
else:
    print("Failed to fetch task output")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Get Cluster Events (if applicable)

# COMMAND ----------

# Extract cluster ID from run details
cluster_id = None

if run_details:
    # Try cluster_instance at top level
    cluster_instance = run_details.get('cluster_instance', {})
    if cluster_instance:
        cluster_id = cluster_instance.get('cluster_id')
    
    # Try to get from tasks
    if not cluster_id:
        tasks = run_details.get('tasks', [])
        for task in tasks:
            task_cluster = task.get('cluster_instance', {})
            if task_cluster.get('cluster_id'):
                cluster_id = task_cluster.get('cluster_id')
                break

print("=" * 80)
print("FETCHING CLUSTER EVENTS")
print("=" * 80)

if cluster_id:
    print(f"Cluster ID: {cluster_id}")
    print()
    
    cluster_events = get_cluster_events(cluster_id)
    
    if cluster_events:
        events = cluster_events.get('events', [])
        print(f"Total Events: {len(events)}")
        print()
        
        for event in events[:10]:  # Show first 10 events
            event_type = event.get('type', 'N/A')
            timestamp = event.get('timestamp', 'N/A')
            details = event.get('details', {})
            print(f"[{timestamp}] {event_type}")
            if details:
                for key, value in details.items():
                    print(f"  - {key}: {value}")
    else:
        print("Failed to fetch cluster events")
else:
    print("No cluster ID found - skipping cluster events")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Export Run (Views)

# COMMAND ----------

print("=" * 80)
print("EXPORTING RUN VIEWS")
print("=" * 80)
print(f"Task Run ID: {TASK_RUN_ID}")
print()

exported_run = export_run(TASK_RUN_ID)

if exported_run:
    views = exported_run.get('views', [])
    print(f"Number of Views: {len(views)}")
    print()
    
    for i, view in enumerate(views):
        print(f"View {i+1}:")
        print(f"  Name: {view.get('name', 'N/A')}")
        print(f"  Type: {view.get('type', 'N/A')}")
        
        content = view.get('content', '')
        if content:
            print(f"  Content Preview (first 500 chars):")
            print(f"  {content[:500]}")
            if len(content) > 500:
                print("  ...")
        print()
else:
    print("Failed to export run (this may not be supported for this run type)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Complete Response Objects
# MAGIC 
# MAGIC The cells below display the full JSON responses for detailed analysis.

# COMMAND ----------

# Full run details
print("FULL RUN DETAILS JSON:")
print("=" * 80)
if run_details:
    print(json.dumps(run_details, indent=2, default=str))
else:
    print("No data")

# COMMAND ----------

# Full run output
print("FULL RUN OUTPUT JSON:")
print("=" * 80)
if run_output:
    print(json.dumps(run_output, indent=2, default=str))
else:
    print("No data")

# COMMAND ----------

# Full task output
print("FULL TASK OUTPUT JSON:")
print("=" * 80)
if task_output:
    print(json.dumps(task_output, indent=2, default=str))
else:
    print("No data")
