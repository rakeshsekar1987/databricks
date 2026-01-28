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

# ============================================================================
# TOKEN CONFIGURATION - Choose ONE method below
# ============================================================================

# METHOD 1: Get token from Databricks secrets (uncomment if using secrets)
# TOKEN = dbutils.secrets.get(scope="generic-scope", key='databricks-admin-token-scrt')

# METHOD 2: Use the current notebook's context token (RECOMMENDED for same workspace)
# This uses the token of the user/service principal running the notebook
TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

# METHOD 3: Hardcode token for testing (NOT recommended for production)
# TOKEN = "dapi..."  # Your personal access token

# ============================================================================
# TOKEN VALIDATION
# ============================================================================
print("=" * 80)
print("TOKEN VALIDATION")
print("=" * 80)

if TOKEN:
    # Show first and last few characters for verification (masked)
    token_preview = f"{TOKEN[:5]}...{TOKEN[-4:]}" if len(TOKEN) > 10 else "***"
    print(f"Token retrieved successfully: {token_preview}")
    print(f"Token length: {len(TOKEN)} characters")
else:
    print("ERROR: Token is empty or None!")
    print("Please check your token configuration above.")
    raise ValueError("Token is required for API authentication")

# COMMAND ----------

# MAGIC %md
# MAGIC ## API Functions

# COMMAND ----------

def make_api_request(method, endpoint, workspace_url, token, params=None, payload=None):
    """
    Generic API request handler with detailed error logging
    
    Args:
        method (str): HTTP method (GET, POST)
        endpoint (str): API endpoint path
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
        params (dict): Query parameters for GET requests
        payload (dict): JSON payload for POST requests
    
    Returns:
        dict: API response or None if failed
    """
    url = f"{workspace_url}{endpoint}"
    
    # Validate token
    if not token or token.strip() == "":
        print("ERROR: Token is empty or None!")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=payload)
        else:
            print(f"Unsupported HTTP method: {method}")
            return None
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
            
            # Additional debugging for 401 errors
            if e.response.status_code == 401:
                print("\n--- DEBUG INFO FOR 401 ERROR ---")
                print(f"Token present: {bool(token)}")
                print(f"Token length: {len(token) if token else 0}")
                print(f"Auth header format: Bearer {token[:5]}...{token[-4:] if token and len(token) > 10 else '***'}")
                print("Possible causes:")
                print("  1. Token is expired - generate a new Personal Access Token")
                print("  2. Token doesn't have required permissions (jobs:read)")
                print("  3. Token is from a different workspace")
                print("  4. Using service principal that lacks permissions")
                print("-" * 35)
        return None


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
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/get-output",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": run_id}
    )

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
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/get",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": run_id}
    )

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
    return make_api_request(
        method="POST",
        endpoint="/api/2.0/clusters/events",
        workspace_url=workspace_url,
        token=token,
        payload={"cluster_id": cluster_id, "limit": limit}
    )

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
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/export",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": run_id, "views_to_export": views_to_export}
    )

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
