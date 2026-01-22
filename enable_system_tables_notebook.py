"""
Databricks Notebook: Enable Unity Catalog and System Tables

This script is designed to run in a Databricks notebook environment.
It uses the REST API pattern similar to the execute_sql_query function
and leverages dbutils for secret management.

Features:
  - Creates a Unity Catalog metastore if one doesn't exist
  - Assigns the metastore to the workspace
  - Enables system tables (schemas)

Usage in Databricks notebook:
  1. Copy this code into a notebook cell
  2. Configure the variables at the top
  3. Run the cell to enable Unity Catalog and system tables
"""

import requests
import time
import json
from typing import Optional, List, Dict, Any

# ============================================================================
# CONFIGURATION - Modify these values for your environment
# ============================================================================

# Workspace URL (e.g., "https://adb-5244115429641560.0.azuredatabricks.net")
WORKSPACE_URL = "https://adb-7026533606192812.12.azuredatabricks.net"

# Secret scope and key for the Databricks admin token
SECRET_SCOPE = "generic-scope"
SECRET_KEY = "databricks-admin-token-scrt"

# ============================================================================
# UNITY CATALOG CONFIGURATION
# ============================================================================

# Metastore name (used when creating a new metastore)
METASTORE_NAME = "unity-catalog-metastore"

# Storage root for metastore data (REQUIRED for new metastore creation)
# Azure: "abfss://<container>@<storage-account>.dfs.core.windows.net/<path>"
# AWS: "s3://<bucket>/<path>"
# GCP: "gs://<bucket>/<path>"
STORAGE_ROOT = None  # e.g., "abfss://unity-catalog@mystorageaccount.dfs.core.windows.net/metastore"

# Azure region (required for Azure)
REGION = "eastus2"  # e.g., "eastus", "westus2", "eastus2"

# Metastore ID (set to None for auto-detection/creation, or specify manually)
METASTORE_ID = None  # e.g., "12345678-1234-1234-1234-123456789abc"

# ============================================================================
# SYSTEM TABLES CONFIGURATION
# ============================================================================

# Schemas to enable (set to None to enable all available)
# Available: access, billing, compute, lineage, storage, workflow, marketplace, serving, query
SCHEMAS_TO_ENABLE = None  # Set to list like ["access", "billing"] for specific schemas

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_workspace_id() -> Optional[str]:
    """Get the current workspace ID from Spark config or context."""
    try:
        # Try multiple methods to get workspace ID
        workspace_id = None
        
        # Method 1: From Spark config
        try:
            workspace_id = spark.conf.get("spark.databricks.clusterUsageTags.clusterOwnerOrgId", None)
            if workspace_id:
                return workspace_id
        except Exception:
            pass
        
        # Method 2: From context tags
        try:
            context = json.loads(dbutils.notebook.entry_point.getDbutils().notebook().getContext().toJson())
            workspace_id = context.get('tags', {}).get('orgId')
            if workspace_id:
                return workspace_id
        except Exception:
            pass
        
        # Method 3: Extract from workspace URL
        # URL format: https://adb-{workspace_id}.{region}.azuredatabricks.net
        import re
        match = re.search(r'adb-(\d+)', WORKSPACE_URL)
        if match:
            return match.group(1)
            
        return None
    except Exception:
        return None


def get_token() -> str:
    """Retrieve the Databricks admin token from secrets."""
    return dbutils.secrets.get(scope=SECRET_SCOPE, key=SECRET_KEY)


# ============================================================================
# UNITY CATALOG MANAGEMENT FUNCTIONS
# ============================================================================

def check_unity_catalog_enabled(workspace_url: str, token: str) -> Dict[str, Any]:
    """
    Check if Unity Catalog is enabled for this workspace.
    
    Returns:
        Dictionary with 'enabled' boolean and 'metastore_id' if enabled
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Try to get current metastore assignment
    endpoints_to_try = [
        "/api/2.1/unity-catalog/current-metastore-assignment",
        "/api/2.1/unity-catalog/metastore_summary",
    ]
    
    for endpoint in endpoints_to_try:
        try:
            response = requests.get(f"{workspace_url}{endpoint}", headers=headers)
            if response.status_code == 200:
                result = response.json()
                metastore_id = result.get('metastore_id')
                if metastore_id:
                    return {"enabled": True, "metastore_id": metastore_id, "details": result}
        except Exception:
            continue
    
    return {"enabled": False, "metastore_id": None}


def list_metastores(workspace_url: str, token: str) -> List[Dict]:
    """
    List all metastores in the account.
    
    Returns:
        List of metastore dictionaries
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(
            f"{workspace_url}/api/2.1/unity-catalog/metastores",
            headers=headers
        )
        if response.status_code == 200:
            return response.json().get('metastores', [])
        else:
            print(f"Error listing metastores: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"Error listing metastores: {str(e)}")
        return []


def create_metastore(
    workspace_url: str, 
    token: str, 
    name: str, 
    storage_root: str,
    region: str
) -> Optional[Dict]:
    """
    Create a new Unity Catalog metastore.
    
    Args:
        workspace_url: Databricks workspace URL
        token: Access token
        name: Name for the new metastore
        storage_root: Cloud storage location for metastore data
        region: Cloud region
        
    Returns:
        Metastore details dictionary or None on failure
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "storage_root": storage_root,
        "region": region
    }
    
    print(f"Creating metastore '{name}'...")
    print(f"  Storage root: {storage_root}")
    print(f"  Region: {region}")
    
    try:
        response = requests.post(
            f"{workspace_url}/api/2.1/unity-catalog/metastores",
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"  ✓ Metastore created successfully!")
            print(f"  Metastore ID: {result.get('metastore_id')}")
            return result
        elif response.status_code == 409:
            print(f"  ✓ Metastore with this name already exists")
            # Try to find the existing metastore
            metastores = list_metastores(workspace_url, token)
            for m in metastores:
                if m.get('name') == name:
                    return m
            return None
        else:
            error_msg = response.json().get('message', response.text)
            print(f"  ✗ Failed to create metastore: {error_msg}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error creating metastore: {str(e)}")
        return None


def assign_metastore_to_workspace(
    workspace_url: str, 
    token: str, 
    metastore_id: str,
    workspace_id: str,
    default_catalog_name: str = "main"
) -> bool:
    """
    Assign a metastore to the current workspace.
    
    Args:
        workspace_url: Databricks workspace URL
        token: Access token
        metastore_id: ID of the metastore to assign
        workspace_id: ID of the workspace
        default_catalog_name: Name of the default catalog to create
        
    Returns:
        True if successful, False otherwise
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "metastore_id": metastore_id,
        "default_catalog_name": default_catalog_name
    }
    
    print(f"Assigning metastore to workspace...")
    print(f"  Metastore ID: {metastore_id}")
    print(f"  Workspace ID: {workspace_id}")
    
    try:
        response = requests.put(
            f"{workspace_url}/api/2.1/unity-catalog/workspaces/{workspace_id}/metastore",
            headers=headers,
            json=payload
        )
        
        if response.status_code in [200, 201, 204]:
            print(f"  ✓ Metastore assigned successfully!")
            return True
        elif response.status_code == 409:
            print(f"  ✓ Workspace already has a metastore assigned")
            return True
        else:
            error_msg = response.json().get('message', response.text) if response.text else str(response.status_code)
            print(f"  ✗ Failed to assign metastore: {error_msg}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error assigning metastore: {str(e)}")
        return False


def setup_unity_catalog(
    workspace_url: str,
    token: str,
    metastore_name: str,
    storage_root: str,
    region: str
) -> Optional[str]:
    """
    Set up Unity Catalog for the workspace.
    
    This function will:
    1. Check if Unity Catalog is already enabled
    2. If not, create a metastore (if storage_root is provided)
    3. Assign the metastore to the workspace
    
    Args:
        workspace_url: Databricks workspace URL
        token: Access token
        metastore_name: Name for the metastore
        storage_root: Cloud storage location
        region: Cloud region
        
    Returns:
        Metastore ID if successful, None otherwise
    """
    print("\n" + "=" * 60)
    print("UNITY CATALOG SETUP")
    print("=" * 60 + "\n")
    
    # Step 1: Check if already enabled
    print("Step 1: Checking Unity Catalog status...")
    status = check_unity_catalog_enabled(workspace_url, token)
    
    if status['enabled']:
        print(f"  ✓ Unity Catalog is already enabled!")
        print(f"  Metastore ID: {status['metastore_id']}")
        return status['metastore_id']
    
    print("  ✗ Unity Catalog is not enabled for this workspace")
    
    # Step 2: Check for existing metastores
    print("\nStep 2: Checking for existing metastores...")
    metastores = list_metastores(workspace_url, token)
    
    metastore_id = None
    
    if metastores:
        print(f"  Found {len(metastores)} existing metastore(s):")
        for m in metastores:
            print(f"    - {m.get('name')} (ID: {m.get('metastore_id')}, Region: {m.get('region')})")
        
        # Try to find one in the same region
        for m in metastores:
            if m.get('region') == region:
                metastore_id = m.get('metastore_id')
                print(f"  Using existing metastore in region {region}: {metastore_id}")
                break
        
        if not metastore_id:
            # Use the first available metastore
            metastore_id = metastores[0].get('metastore_id')
            print(f"  Using first available metastore: {metastore_id}")
    else:
        print("  No existing metastores found")
        
        # Step 3: Create a new metastore
        if storage_root:
            print("\nStep 3: Creating new metastore...")
            metastore = create_metastore(workspace_url, token, metastore_name, storage_root, region)
            if metastore:
                metastore_id = metastore.get('metastore_id')
        else:
            print("\nStep 3: Cannot create metastore - STORAGE_ROOT not configured")
            print("  Please set STORAGE_ROOT to your cloud storage location:")
            print("  Azure: abfss://<container>@<storage-account>.dfs.core.windows.net/<path>")
            print("  AWS:   s3://<bucket>/<path>")
            print("  GCP:   gs://<bucket>/<path>")
            return None
    
    if not metastore_id:
        print("\n✗ Failed to obtain metastore ID")
        return None
    
    # Step 4: Assign metastore to workspace
    print("\nStep 4: Assigning metastore to workspace...")
    workspace_id = get_workspace_id()
    
    if not workspace_id:
        print("  ✗ Could not determine workspace ID")
        print("  Trying alternative assignment method...")
        
        # Try direct assignment without workspace ID
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Use the metastore assignment endpoint
            response = requests.put(
                f"{workspace_url}/api/2.1/unity-catalog/metastore_assignment",
                headers=headers,
                json={
                    "metastore_id": metastore_id,
                    "default_catalog_name": "main"
                }
            )
            
            if response.status_code in [200, 201, 204]:
                print(f"  ✓ Metastore assigned successfully!")
            elif response.status_code == 409:
                print(f"  ✓ Workspace already has a metastore assigned")
            else:
                print(f"  ✗ Failed: {response.text}")
                return None
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            return None
    else:
        if not assign_metastore_to_workspace(workspace_url, token, metastore_id, workspace_id):
            return None
    
    print("\n" + "=" * 60)
    print("✓ UNITY CATALOG SETUP COMPLETE")
    print("=" * 60)
    print(f"  Metastore ID: {metastore_id}")
    
    # Wait for assignment to propagate
    print("\nWaiting for Unity Catalog to initialize (30 seconds)...")
    time.sleep(30)
    
    return metastore_id


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

def run_full_setup():
    """
    Run the complete setup: Unity Catalog + System Tables.
    """
    print("=" * 60)
    print("DATABRICKS UNITY CATALOG & SYSTEM TABLES SETUP")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Workspace URL: {WORKSPACE_URL}")
    print(f"  Secret Scope: {SECRET_SCOPE}")
    print(f"  Metastore Name: {METASTORE_NAME}")
    print(f"  Storage Root: {STORAGE_ROOT or 'Not configured'}")
    print(f"  Region: {REGION}")
    print(f"  Target Schemas: {SCHEMAS_TO_ENABLE or 'ALL'}")
    print(f"  Metastore ID: {METASTORE_ID or 'Auto-detect/Create'}")
    
    # Get token
    print("\n" + "-" * 60)
    print("Retrieving access token...")
    token = get_token()
    print("  ✓ Token retrieved")
    
    # Phase 1: Set up Unity Catalog
    metastore_id = METASTORE_ID
    
    if not metastore_id:
        metastore_id = setup_unity_catalog(
            workspace_url=WORKSPACE_URL,
            token=token,
            metastore_name=METASTORE_NAME,
            storage_root=STORAGE_ROOT,
            region=REGION
        )
    
    if not metastore_id:
        print("\n" + "=" * 60)
        print("✗ SETUP FAILED")
        print("=" * 60)
        print("\nCould not set up Unity Catalog. Please check:")
        print("1. Your token has account admin privileges")
        print("2. STORAGE_ROOT is configured with a valid cloud storage path")
        print("3. The storage account is accessible and properly configured")
        return
    
    # Phase 2: Enable System Tables
    print("\n" + "=" * 60)
    print("ENABLING SYSTEM TABLES")
    print("=" * 60 + "\n")
    
    results = enable_system_tables(
        schemas_to_enable=SCHEMAS_TO_ENABLE,
        metastore_id=metastore_id
    )
    
    # Final Summary
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    print(f"\nMetastore ID: {metastore_id}")
    
    if results:
        successful = sum(1 for v in results.values() if v)
        print(f"System schemas enabled: {successful}/{len(results)}")
    
    print("\nYou can now query system tables like:")
    print("  SELECT * FROM system.access.audit")
    print("  SELECT * FROM system.billing.usage")
    print("  SELECT * FROM system.compute.clusters")


if __name__ == "__main__" or True:  # Set to True to run in notebook
    run_full_setup()
