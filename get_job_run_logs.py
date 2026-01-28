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
    api_endpoint = f"{workspace_url}/api/2.1/jobs/runs/get-output"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "run_id": job_run_id
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
    api_endpoint = f"{workspace_url}/api/2.1/jobs/runs/get"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "run_id": job_run_id
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

def main_databricks():
    """
    Main function for execution in Databricks notebook environment
    Uses dbutils to get the token from secrets
    """
    # Configuration
    WORKSPACE_URL = "https://adb-5244115429641560.0.azuredatabricks.net"
    JOB_ID = "133166337001904"
    JOB_RUN_ID = "584498514062775"
    TASK_RUN_ID = "87528399080853"
    
    # Get token from Databricks secrets
    token = dbutils.secrets.get(scope="generic-scope", key='databricks-admin-token-scrt')
    
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
    
    print("Azure Databricks Job Run Logs Retriever")
    print("-" * 40)
    
    if len(sys.argv) > 1:
        # Token provided as command line argument
        token = sys.argv[1]
        main_standalone(token)
    else:
        print("\nUsage:")
        print("  Standalone: python get_job_run_logs.py <DATABRICKS_TOKEN>")
        print("  Databricks: Run main_databricks() in a notebook cell")
        print("\nFor Databricks notebook, copy the functions and run:")
        print("  logs = main_databricks()")
