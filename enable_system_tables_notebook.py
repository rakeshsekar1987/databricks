"""
Databricks Notebook: Enable System Tables

This script is designed to run in a Databricks notebook environment.
It uses the REST API pattern similar to the execute_sql_query function
and leverages dbutils for secret management.

Usage in Databricks notebook:
  1. Copy this code into a notebook cell
  2. Configure the variables at the top
  3. Run the cell to enable system tables
"""

import requests
import time
import json
from typing import Optional, List, Dict, Any

# ============================================================================
# CONFIGURATION - Modify these values for your environment
# ============================================================================

# Workspace URL (e.g., "https://adb-5244115429641560.0.azuredatabricks.net")
WORKSPACE_URL = "https://adb-5244115429641560.0.azuredatabricks.net"

# Secret scope and key for the Databricks admin token
SECRET_SCOPE = "generic-scope"
SECRET_KEY = "databricks-admin-token-scrt"

# Schemas to enable (set to None to enable all available)
# Available: access, billing, compute, lineage, storage, workflow, marketplace, serving, query
SCHEMAS_TO_ENABLE = None  # Set to list like ["access", "billing"] for specific schemas

# Metastore ID (set to None for auto-detection, or specify manually if auto-detection fails)
# You can find this in Unity Catalog settings or by running: SELECT current_metastore()
METASTORE_ID = None  # e.g., "12345678-1234-1234-1234-123456789abc"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_workspace_id() -> Optional[str]:
    """Get the current workspace ID from Spark config."""
    try:
        return spark.conf.get("spark.databricks.workspaceUrl", None)
    except Exception:
        return None


def get_token() -> str:
    """Retrieve the Databricks admin token from secrets."""
    return dbutils.secrets.get(scope=SECRET_SCOPE, key=SECRET_KEY)


def get_current_metastore_id(workspace_url: str, token: str) -> Optional[str]:
    """
    Get the current metastore ID assigned to the workspace.
    Tries multiple API endpoints for compatibility.
    
    Args:
        workspace_url: The Databricks workspace URL
        token: Databricks access token
        
    Returns:
        Metastore ID or None if not found
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Try multiple endpoints in order of preference
    endpoints_to_try = [
        # Method 1: Current metastore assignment (newer API)
        ("/api/2.1/unity-catalog/current-metastore-assignment", "metastore_id"),
        # Method 2: Metastore summary
        ("/api/2.1/unity-catalog/metastore_summary", "metastore_id"),
        # Method 3: List metastores and get the first one
        ("/api/2.1/unity-catalog/metastores", None),
    ]
    
    for endpoint, key in endpoints_to_try:
        api_url = f"{workspace_url}{endpoint}"
        print(f"  Trying: {endpoint}")
        
        try:
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                if key:
                    # Direct key lookup
                    metastore_id = result.get(key)
                else:
                    # List response - get first metastore
                    metastores = result.get('metastores', [])
                    if metastores:
                        metastore_id = metastores[0].get('metastore_id')
                    else:
                        continue
                
                if metastore_id:
                    print(f"  ✓ Found metastore ID: {metastore_id}")
                    return metastore_id
                    
            elif response.status_code == 404:
                print(f"  ✗ Endpoint not available (404)")
                continue
            else:
                print(f"  ✗ Error: {response.status_code}")
                continue
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request failed: {str(e)}")
            continue
    
    # If all API methods fail, try to get from Spark config (in notebook)
    try:
        # This works in Databricks notebooks with Unity Catalog
        metastore_id = spark.conf.get("spark.databricks.unityCatalog.metastoreId", None)
        if metastore_id:
            print(f"  ✓ Found metastore ID from Spark config: {metastore_id}")
            return metastore_id
    except Exception:
        pass
    
    print("  ✗ Could not determine metastore ID from any source")
    return None


def list_system_schemas(workspace_url: str, token: str, metastore_id: str) -> List[Dict]:
    """
    List all system schemas and their current state.
    
    Args:
        workspace_url: The Databricks workspace URL
        token: Databricks access token
        metastore_id: The metastore ID
        
    Returns:
        List of system schema dictionaries
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    api_endpoint = f"{workspace_url}/api/2.1/unity-catalog/metastores/{metastore_id}/systemschemas"
    
    try:
        response = requests.get(api_endpoint, headers=headers)
        response.raise_for_status()
        result = response.json()
        schemas = result.get('schemas', [])
        return schemas
    except requests.exceptions.RequestException as e:
        print(f"Error listing system schemas: {str(e)}")
        return []


def enable_system_schema(
    workspace_url: str, 
    token: str, 
    metastore_id: str, 
    schema_name: str
) -> bool:
    """
    Enable a specific system schema using the Unity Catalog REST API.
    
    Args:
        workspace_url: The Databricks workspace URL
        token: Databricks access token
        metastore_id: The metastore ID
        schema_name: Name of the system schema to enable
        
    Returns:
        True if successful, False otherwise
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    api_endpoint = f"{workspace_url}/api/2.1/unity-catalog/metastores/{metastore_id}/systemschemas/{schema_name}"
    
    try:
        response = requests.put(api_endpoint, headers=headers)
        
        # Handle various success codes
        if response.status_code in [200, 201, 204]:
            print(f"✓ Successfully enabled system schema: {schema_name}")
            return True
        elif response.status_code == 409:
            # Already enabled
            print(f"✓ System schema already enabled: {schema_name}")
            return True
        else:
            response.raise_for_status()
            return True
            
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        try:
            error_detail = response.json().get('message', error_msg)
        except Exception:
            error_detail = error_msg
        print(f"✗ Failed to enable system schema {schema_name}: {error_detail}")
        return False


def disable_system_schema(
    workspace_url: str, 
    token: str, 
    metastore_id: str, 
    schema_name: str
) -> bool:
    """
    Disable a specific system schema.
    
    Args:
        workspace_url: The Databricks workspace URL
        token: Databricks access token
        metastore_id: The metastore ID
        schema_name: Name of the system schema to disable
        
    Returns:
        True if successful, False otherwise
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    api_endpoint = f"{workspace_url}/api/2.1/unity-catalog/metastores/{metastore_id}/systemschemas/{schema_name}"
    
    try:
        response = requests.delete(api_endpoint, headers=headers)
        
        if response.status_code in [200, 204]:
            print(f"✓ Successfully disabled system schema: {schema_name}")
            return True
        else:
            response.raise_for_status()
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to disable system schema {schema_name}: {str(e)}")
        return False


def print_status_report(schemas: List[Dict]) -> None:
    """Print a formatted status report of system schemas."""
    print("\n" + "=" * 60)
    print("SYSTEM TABLES STATUS REPORT")
    print("=" * 60 + "\n")
    
    if not schemas:
        print("No system schemas found.")
        return
    
    for schema in schemas:
        name = schema.get('schema', 'Unknown')
        state = schema.get('state', 'Unknown')
        
        if state == "ENABLE_COMPLETED":
            status_icon = "✓"
        elif state == "AVAILABLE":
            status_icon = "○"
        elif state == "ENABLE_INITIALIZED":
            status_icon = "⋯"
        else:
            status_icon = "?"
            
        print(f"  {status_icon} {name}: {state}")
    
    print("\n" + "=" * 60)
    print("Legend: ✓ = Enabled, ○ = Available, ⋯ = In Progress")
    print("=" * 60 + "\n")


# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

def enable_system_tables(
    schemas_to_enable: Optional[List[str]] = None,
    show_status: bool = True,
    metastore_id: Optional[str] = None
) -> Dict[str, bool]:
    """
    Main function to enable system tables.
    
    Args:
        schemas_to_enable: List of schema names to enable, or None for all
        show_status: Whether to show status report after enabling
        metastore_id: Optional metastore ID (will auto-detect if not provided)
        
    Returns:
        Dictionary mapping schema names to success status
    """
    # Available system schemas
    all_available_schemas = [
        "access",
        "billing",
        "compute",
        "lineage",
        "storage",
        "workflow",
        "marketplace",
        "serving",
        "query",
    ]
    
    # Get token
    print("Retrieving access token...")
    token = get_token()
    
    # Get metastore ID - use provided value or auto-detect
    if metastore_id:
        print(f"Using provided metastore ID: {metastore_id}")
    else:
        print("Auto-detecting metastore ID...")
        metastore_id = get_current_metastore_id(WORKSPACE_URL, token)
    
    if not metastore_id:
        print("\n" + "=" * 60)
        print("ERROR: Could not determine metastore ID.")
        print("=" * 60)
        print("\nPossible solutions:")
        print("1. Ensure Unity Catalog is enabled for this workspace")
        print("2. Manually set METASTORE_ID in the configuration section")
        print("3. Run this SQL to find your metastore ID:")
        print("   SELECT current_metastore()")
        print("=" * 60)
        return {}
    
    # Determine which schemas to enable
    target_schemas = schemas_to_enable or all_available_schemas
    
    print(f"\nEnabling {len(target_schemas)} system schema(s)...")
    print("-" * 40)
    
    # Enable each schema
    results = {}
    for schema in target_schemas:
        results[schema] = enable_system_schema(
            WORKSPACE_URL, 
            token, 
            metastore_id, 
            schema
        )
        time.sleep(0.5)  # Small delay to avoid rate limiting
    
    # Show status report if requested
    if show_status:
        print("\nRefreshing status...")
        time.sleep(2)  # Wait for status to update
        schemas = list_system_schemas(WORKSPACE_URL, token, metastore_id)
        print_status_report(schemas)
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    failed = len(results) - successful
    
    print(f"\nSummary: {successful} succeeded, {failed} failed")
    
    return results


def get_system_tables_status(metastore_id: Optional[str] = None) -> List[Dict]:
    """
    Get and display the current status of all system tables.
    
    Args:
        metastore_id: Optional metastore ID (will auto-detect if not provided)
    
    Returns:
        List of system schema dictionaries
    """
    print("Retrieving access token...")
    token = get_token()
    
    # Get metastore ID - use provided value or auto-detect
    if metastore_id:
        print(f"Using provided metastore ID: {metastore_id}")
    else:
        print("Auto-detecting metastore ID...")
        metastore_id = get_current_metastore_id(WORKSPACE_URL, token)
    
    if not metastore_id:
        print("\n" + "=" * 60)
        print("ERROR: Could not determine metastore ID.")
        print("=" * 60)
        print("\nPossible solutions:")
        print("1. Ensure Unity Catalog is enabled for this workspace")
        print("2. Manually set METASTORE_ID in the configuration section")
        print("3. Run this SQL to find your metastore ID:")
        print("   SELECT current_metastore()")
        print("=" * 60)
        return []
    
    print("Fetching system schemas status...")
    schemas = list_system_schemas(WORKSPACE_URL, token, metastore_id)
    
    print_status_report(schemas)
    
    return schemas


# ============================================================================
# EXECUTE - Uncomment the desired function call below
# ============================================================================

# Option 1: Enable all system schemas
# enable_system_tables()

# Option 2: Enable specific schemas only
# enable_system_tables(schemas_to_enable=["access", "billing", "compute"])

# Option 3: Just check current status
# get_system_tables_status()


# ============================================================================
# RUN WITH CONFIGURED SETTINGS
# ============================================================================

if __name__ == "__main__" or True:  # Set to True to run in notebook
    print("=" * 60)
    print("DATABRICKS SYSTEM TABLES ENABLEMENT")
    print("=" * 60)
    print(f"\nWorkspace URL: {WORKSPACE_URL}")
    print(f"Secret Scope: {SECRET_SCOPE}")
    print(f"Target Schemas: {SCHEMAS_TO_ENABLE or 'ALL'}")
    print(f"Metastore ID: {METASTORE_ID or 'Auto-detect'}")
    print()
    
    # Uncomment ONE of the following:
    
    # Enable system tables
    results = enable_system_tables(
        schemas_to_enable=SCHEMAS_TO_ENABLE,
        metastore_id=METASTORE_ID
    )
    
    # Or just check status
    # get_system_tables_status(metastore_id=METASTORE_ID)
