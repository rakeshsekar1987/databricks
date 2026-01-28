"""
Azure Databricks Job Run Logs Retriever

This script retrieves the output logs of a Databricks job run using the REST API.

Job ID: 133166337001904
Job Run ID: 584498514062775
Task Run ID: 87528399080853
"""

import requests
import json
import time


def validate_token(token):
    """
    Validate the token and print diagnostic information
    
    Args:
        token (str): The Databricks API token
    
    Returns:
        bool: True if token appears valid, False otherwise
    """
    if not token:
        print("ERROR: Token is None or empty!")
        return False
    
    if not isinstance(token, str):
        print(f"ERROR: Token is not a string, got {type(token)}")
        return False
    
    token = token.strip()
    if len(token) == 0:
        print("ERROR: Token is empty after stripping whitespace!")
        return False
    
    # Show masked token for verification
    token_preview = f"{token[:5]}...{token[-4:]}" if len(token) > 10 else "***"
    print(f"Token preview: {token_preview}")
    print(f"Token length: {len(token)} characters")
    
    return True


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
                if token and len(token) > 10:
                    print(f"Auth header format: Bearer {token[:5]}...{token[-4:]}")
                print("Possible causes:")
                print("  1. Token is expired - generate a new Personal Access Token")
                print("  2. Token doesn't have required permissions (jobs:read)")
                print("  3. Token is from a different workspace")
                print("  4. Using service principal that lacks permissions")
                print("  5. Secret scope/key name is incorrect")
                print("-" * 35)
        return None


def get_job_run_output(job_run_id, workspace_url, token):
    """
    Get the output of a job run using the Databricks REST API
    
    Args:
        job_run_id (str): The job run ID to get output for
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
    
    Returns:
        dict: The job run output response
    """
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/get-output",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": job_run_id}
    )


def get_job_run_details(job_run_id, workspace_url, token):
    """
    Get the details of a job run using the Databricks REST API
    
    Args:
        job_run_id (str): The job run ID to get details for
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
    
    Returns:
        dict: The job run details response
    """
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/get",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": job_run_id}
    )


def get_cluster_events(cluster_id, workspace_url, token, limit=100):
    """
    Get cluster events/logs for a specific cluster
    
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


def export_run(run_id, workspace_url, token, views_to_export="ALL"):
    """
    Export and retrieve the job run
    
    Args:
        run_id (str): The run ID to export
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
        views_to_export (str): Which views to export (CODE, DASHBOARDS, ALL)
    
    Returns:
        dict: The exported run response
    """
    return make_api_request(
        method="GET",
        endpoint="/api/2.1/jobs/runs/export",
        workspace_url=workspace_url,
        token=token,
        params={"run_id": run_id, "views_to_export": views_to_export}
    )


def get_job_run_logs(job_id, job_run_id, task_run_id, workspace_url, token):
    """
    Main function to retrieve all available logs for a job run
    
    Args:
        job_id (str): The job ID
        job_run_id (str): The job run ID  
        task_run_id (str): The task run ID
        workspace_url (str): The Azure Databricks workspace URL
        token (str): The Databricks API token
    
    Returns:
        dict: Combined log information
    """
    print("=" * 80)
    print("AZURE DATABRICKS JOB RUN LOGS RETRIEVER")
    print("=" * 80)
    print(f"\nJob ID: {job_id}")
    print(f"Job Run ID: {job_run_id}")
    print(f"Task Run ID: {task_run_id}")
    print(f"Workspace URL: {workspace_url}")
    print("=" * 80)
    
    logs = {
        "job_id": job_id,
        "job_run_id": job_run_id,
        "task_run_id": task_run_id,
        "run_details": None,
        "run_output": None,
        "task_output": None,
        "cluster_events": None,
        "exported_run": None
    }
    
    # 1. Get Job Run Details
    print("\n[1/5] Fetching Job Run Details...")
    run_details = get_job_run_details(job_run_id, workspace_url, token)
    if run_details:
        logs["run_details"] = run_details
        print(f"  - Run Name: {run_details.get('run_name', 'N/A')}")
        print(f"  - State: {run_details.get('state', {}).get('life_cycle_state', 'N/A')}")
        print(f"  - Result State: {run_details.get('state', {}).get('result_state', 'N/A')}")
        
        # Extract cluster ID if available
        cluster_instance = run_details.get('cluster_instance', {})
        cluster_id = cluster_instance.get('cluster_id')
        
        # Check tasks for cluster info
        tasks = run_details.get('tasks', [])
        if tasks:
            print(f"  - Number of Tasks: {len(tasks)}")
            for task in tasks:
                task_key = task.get('task_key', 'N/A')
                task_state = task.get('state', {})
                print(f"    - Task: {task_key}")
                print(f"      Life Cycle State: {task_state.get('life_cycle_state', 'N/A')}")
                print(f"      Result State: {task_state.get('result_state', 'N/A')}")
                
                # Get cluster ID from task
                task_cluster = task.get('cluster_instance', {})
                if task_cluster.get('cluster_id'):
                    cluster_id = task_cluster.get('cluster_id')
    else:
        print("  - Failed to fetch run details")
    
    # 2. Get Job Run Output (for the main run)
    print("\n[2/5] Fetching Job Run Output...")
    run_output = get_job_run_output(job_run_id, workspace_url, token)
    if run_output:
        logs["run_output"] = run_output
        
        # Print notebook output if available
        notebook_output = run_output.get('notebook_output', {})
        if notebook_output:
            print("  - Notebook Output:")
            result = notebook_output.get('result', 'No result')
            print(f"    Result: {result}")
            truncated = notebook_output.get('truncated', False)
            if truncated:
                print("    (Output was truncated)")
        
        # Print logs if available
        logs_output = run_output.get('logs', '')
        if logs_output:
            print("  - Logs:")
            print(logs_output[:2000])  # Print first 2000 chars
            if len(logs_output) > 2000:
                print("    ... (logs truncated for display)")
        
        # Print error if any
        error = run_output.get('error', '')
        if error:
            print(f"  - Error: {error}")
        
        # Print error trace if any
        error_trace = run_output.get('error_trace', '')
        if error_trace:
            print(f"  - Error Trace: {error_trace}")
        
        # Metadata
        metadata = run_output.get('metadata', {})
        if metadata:
            print(f"  - Run Page URL: {metadata.get('run_page_url', 'N/A')}")
    else:
        print("  - Failed to fetch run output")
    
    # 3. Get Task Run Output (for the specific task)
    print("\n[3/5] Fetching Task Run Output...")
    task_output = get_job_run_output(task_run_id, workspace_url, token)
    if task_output:
        logs["task_output"] = task_output
        
        # Print notebook output if available
        notebook_output = task_output.get('notebook_output', {})
        if notebook_output:
            print("  - Notebook Output:")
            result = notebook_output.get('result', 'No result')
            print(f"    Result: {result}")
        
        # Print logs if available
        logs_output = task_output.get('logs', '')
        if logs_output:
            print("  - Task Logs:")
            print(logs_output[:2000])
            if len(logs_output) > 2000:
                print("    ... (logs truncated for display)")
        
        # Print error if any
        error = task_output.get('error', '')
        if error:
            print(f"  - Error: {error}")
        
        error_trace = task_output.get('error_trace', '')
        if error_trace:
            print(f"  - Error Trace: {error_trace}")
    else:
        print("  - Failed to fetch task output")
    
    # 4. Get Cluster Events (if cluster ID was found)
    print("\n[4/5] Fetching Cluster Events...")
    if run_details:
        cluster_id = None
        
        # Try to get cluster ID from cluster_instance
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
        
        if cluster_id:
            print(f"  - Cluster ID: {cluster_id}")
            cluster_events = get_cluster_events(cluster_id, workspace_url, token)
            if cluster_events:
                logs["cluster_events"] = cluster_events
                events = cluster_events.get('events', [])
                print(f"  - Number of Events: {len(events)}")
                for event in events[:5]:  # Show first 5 events
                    event_type = event.get('type', 'N/A')
                    timestamp = event.get('timestamp', 'N/A')
                    print(f"    - [{timestamp}] {event_type}")
            else:
                print("  - Failed to fetch cluster events")
        else:
            print("  - No cluster ID found in run details")
    else:
        print("  - Skipped (no run details available)")
    
    # 5. Export Run
    print("\n[5/5] Exporting Run...")
    exported_run = export_run(task_run_id, workspace_url, token)
    if exported_run:
        logs["exported_run"] = exported_run
        views = exported_run.get('views', [])
        print(f"  - Number of Views: {len(views)}")
        for view in views:
            view_name = view.get('name', 'N/A')
            view_type = view.get('type', 'N/A')
            print(f"    - {view_name} ({view_type})")
    else:
        print("  - Failed to export run (may not be supported for this run type)")
    
    print("\n" + "=" * 80)
    print("LOG RETRIEVAL COMPLETE")
    print("=" * 80)
    
    return logs


def save_logs_to_file(logs, filename="job_run_logs.json"):
    """
    Save the collected logs to a JSON file
    
    Args:
        logs (dict): The logs dictionary
        filename (str): Output filename
    """
    with open(filename, 'w') as f:
        json.dump(logs, f, indent=2, default=str)
    print(f"\nLogs saved to: {filename}")


# ============================================================================
# MAIN EXECUTION - FOR DATABRICKS NOTEBOOK
# ============================================================================

def main_databricks(token_method="context"):
    """
    Main function for execution in Databricks notebook environment
    
    Args:
        token_method (str): How to get the token:
            - "context": Use the notebook context token (RECOMMENDED)
            - "secret": Use dbutils.secrets.get()
    """
    # Configuration
    WORKSPACE_URL = "https://adb-5244115429641560.0.azuredatabricks.net"
    JOB_ID = "133166337001904"
    JOB_RUN_ID = "584498514062775"
    TASK_RUN_ID = "87528399080853"
    
    # Get token based on method
    if token_method == "context":
        # METHOD 1: Use the current notebook's context token (RECOMMENDED)
        # This uses the token of the user/service principal running the notebook
        print("Using notebook context token...")
        token = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
    elif token_method == "secret":
        # METHOD 2: Get token from Databricks secrets
        print("Using token from secrets...")
        token = dbutils.secrets.get(scope="generic-scope", key='databricks-admin-token-scrt')
    else:
        raise ValueError(f"Unknown token_method: {token_method}. Use 'context' or 'secret'")
    
    # Validate token
    print("\n--- Token Validation ---")
    if not validate_token(token):
        raise ValueError("Token validation failed!")
    print("------------------------\n")
    
    # Retrieve logs
    logs = get_job_run_logs(
        job_id=JOB_ID,
        job_run_id=JOB_RUN_ID,
        task_run_id=TASK_RUN_ID,
        workspace_url=WORKSPACE_URL,
        token=token
    )
    
    # Save to file
    save_logs_to_file(logs)
    
    return logs


# ============================================================================
# MAIN EXECUTION - FOR LOCAL/STANDALONE TESTING
# ============================================================================

def main_standalone(token):
    """
    Main function for standalone execution (outside Databricks)
    Requires token to be passed as parameter
    
    Args:
        token (str): The Databricks API token
    """
    # Configuration
    WORKSPACE_URL = "https://adb-5244115429641560.0.azuredatabricks.net"
    JOB_ID = "133166337001904"
    JOB_RUN_ID = "584498514062775"
    TASK_RUN_ID = "87528399080853"
    
    # Validate token
    print("\n--- Token Validation ---")
    if not validate_token(token):
        raise ValueError("Token validation failed!")
    print("------------------------\n")
    
    # Retrieve logs
    logs = get_job_run_logs(
        job_id=JOB_ID,
        job_run_id=JOB_RUN_ID,
        task_run_id=TASK_RUN_ID,
        workspace_url=WORKSPACE_URL,
        token=token
    )
    
    # Save to file
    save_logs_to_file(logs)
    
    return logs


if __name__ == "__main__":
    import sys
    import os
    
    print("Azure Databricks Job Run Logs Retriever")
    print("-" * 40)
    
    # Try to get token from multiple sources
    token = None
    
    # 1. Command line argument
    if len(sys.argv) > 1:
        token = sys.argv[1]
        print("Using token from command line argument")
    
    # 2. Environment variable
    elif os.environ.get('DATABRICKS_TOKEN'):
        token = os.environ.get('DATABRICKS_TOKEN')
        print("Using token from DATABRICKS_TOKEN environment variable")
    
    if token:
        main_standalone(token)
    else:
        print("\nUsage:")
        print("  Option 1: python get_job_run_logs.py <DATABRICKS_TOKEN>")
        print("  Option 2: export DATABRICKS_TOKEN=<your_token> && python get_job_run_logs.py")
        print("\nFor Databricks notebook, use one of these methods:")
        print("  # Method 1: Use notebook context token (RECOMMENDED)")
        print("  logs = main_databricks(token_method='context')")
        print("")
        print("  # Method 2: Use token from secrets")
        print("  logs = main_databricks(token_method='secret')")
