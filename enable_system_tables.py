#!/usr/bin/env python3
"""
Databricks System Tables Enablement Script

This script enables system tables (system schemas) in a Databricks workspace
using the Unity Catalog REST API.

System tables provide metadata about your Databricks workspace including:
- access.audit: Audit logs
- billing.usage: Billing and usage data  
- compute.clusters: Cluster information
- lineage.table_lineage: Table lineage data
- lineage.column_lineage: Column lineage data
- storage.predictive_optimization_operations_history: Predictive optimization history
- workflow.jobs: Workflow job metadata
- marketplace.listing_access_events: Marketplace access events
- serving.served_entities: Model serving entities
- serving.endpoint_usage: Model serving endpoint usage
- query.history: SQL query history
"""

import requests
import time
import json
from typing import Optional, List, Dict, Any


class DatabricksSystemTablesManager:
    """
    Manager class for enabling and managing Databricks system tables.
    """
    
    # Available system schemas that can be enabled
    AVAILABLE_SCHEMAS = [
        "access",           # Audit logs
        "billing",          # Usage and billing data
        "compute",          # Cluster and compute metadata
        "lineage",          # Table and column lineage
        "storage",          # Storage optimization data
        "workflow",         # Jobs and workflow metadata
        "marketplace",      # Marketplace access events
        "serving",          # Model serving metadata
        "query",            # SQL query history
    ]
    
    def __init__(
        self, 
        workspace_url: str, 
        token: str, 
        metastore_id: Optional[str] = None
    ):
        """
        Initialize the System Tables Manager.
        
        Args:
            workspace_url: The Databricks workspace URL (e.g., https://adb-xxx.azuredatabricks.net)
            token: Databricks access token with admin privileges
            metastore_id: Optional metastore ID. If not provided, will auto-detect.
        """
        self.workspace_url = workspace_url.rstrip('/')
        self.token = token
        self.metastore_id = metastore_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        payload: Optional[Dict] = None,
        retry_count: int = 3
    ) -> Optional[Dict]:
        """
        Make an HTTP request to the Databricks API with retry logic.
        
        Args:
            method: HTTP method (GET, PUT, DELETE, POST)
            endpoint: API endpoint path
            payload: Optional request payload
            retry_count: Number of retries on failure
            
        Returns:
            Response JSON or None on failure
        """
        url = f"{self.workspace_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                if method == "GET":
                    response = requests.get(url, headers=self.headers)
                elif method == "PUT":
                    response = requests.put(url, headers=self.headers, json=payload)
                elif method == "DELETE":
                    response = requests.delete(url, headers=self.headers)
                elif method == "POST":
                    response = requests.post(url, headers=self.headers, json=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                # Handle empty responses (204 No Content)
                if response.status_code == 204 or not response.text:
                    return {}
                    
                return response.json()
                
            except requests.exceptions.RequestException as e:
                wait_time = 2 ** attempt
                print(f"Request failed (attempt {attempt + 1}/{retry_count}): {str(e)}")
                if attempt < retry_count - 1:
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"All retries exhausted for {endpoint}")
                    return None
                    
        return None
    
    def get_current_metastore(self) -> Optional[str]:
        """
        Get the current metastore ID assigned to the workspace.
        
        Returns:
            Metastore ID or None if not found
        """
        print("Fetching current metastore assignment...")
        
        result = self._make_request("GET", "/api/2.1/unity-catalog/current-metastore-assignment")
        
        if result and 'metastore_id' in result:
            self.metastore_id = result['metastore_id']
            print(f"Found metastore ID: {self.metastore_id}")
            return self.metastore_id
        else:
            print("Could not determine metastore ID. Please provide it explicitly.")
            return None
    
    def list_system_schemas(self) -> List[Dict[str, Any]]:
        """
        List all system schemas and their current state.
        
        Returns:
            List of system schema information dictionaries
        """
        if not self.metastore_id:
            self.get_current_metastore()
            
        if not self.metastore_id:
            print("Error: Metastore ID is required")
            return []
        
        print(f"Listing system schemas for metastore: {self.metastore_id}")
        
        endpoint = f"/api/2.1/unity-catalog/metastores/{self.metastore_id}/systemschemas"
        result = self._make_request("GET", endpoint)
        
        if result and 'schemas' in result:
            schemas = result['schemas']
            print(f"Found {len(schemas)} system schemas")
            return schemas
        else:
            print("No system schemas found or error occurred")
            return []
    
    def enable_system_schema(self, schema_name: str) -> bool:
        """
        Enable a specific system schema.
        
        Args:
            schema_name: Name of the system schema to enable (e.g., 'access', 'billing')
            
        Returns:
            True if successful, False otherwise
        """
        if not self.metastore_id:
            self.get_current_metastore()
            
        if not self.metastore_id:
            print("Error: Metastore ID is required")
            return False
        
        print(f"Enabling system schema: {schema_name}")
        
        endpoint = f"/api/2.1/unity-catalog/metastores/{self.metastore_id}/systemschemas/{schema_name}"
        result = self._make_request("PUT", endpoint)
        
        if result is not None:
            print(f"Successfully enabled system schema: {schema_name}")
            return True
        else:
            print(f"Failed to enable system schema: {schema_name}")
            return False
    
    def disable_system_schema(self, schema_name: str) -> bool:
        """
        Disable a specific system schema.
        
        Args:
            schema_name: Name of the system schema to disable
            
        Returns:
            True if successful, False otherwise
        """
        if not self.metastore_id:
            self.get_current_metastore()
            
        if not self.metastore_id:
            print("Error: Metastore ID is required")
            return False
        
        print(f"Disabling system schema: {schema_name}")
        
        endpoint = f"/api/2.1/unity-catalog/metastores/{self.metastore_id}/systemschemas/{schema_name}"
        result = self._make_request("DELETE", endpoint)
        
        if result is not None:
            print(f"Successfully disabled system schema: {schema_name}")
            return True
        else:
            print(f"Failed to disable system schema: {schema_name}")
            return False
    
    def enable_all_system_schemas(self) -> Dict[str, bool]:
        """
        Enable all available system schemas.
        
        Returns:
            Dictionary mapping schema names to success status
        """
        print("Enabling all available system schemas...")
        results = {}
        
        for schema in self.AVAILABLE_SCHEMAS:
            results[schema] = self.enable_system_schema(schema)
            time.sleep(0.5)  # Small delay to avoid rate limiting
            
        # Summary
        successful = sum(1 for v in results.values() if v)
        print(f"\nSummary: Enabled {successful}/{len(results)} system schemas")
        
        return results
    
    def get_system_tables_status(self) -> None:
        """
        Print a detailed status report of all system schemas.
        """
        print("\n" + "=" * 60)
        print("SYSTEM TABLES STATUS REPORT")
        print("=" * 60 + "\n")
        
        schemas = self.list_system_schemas()
        
        if not schemas:
            print("No system schemas found or unable to retrieve status.")
            return
        
        for schema in schemas:
            name = schema.get('schema', 'Unknown')
            state = schema.get('state', 'Unknown')
            
            status_icon = "✓" if state == "ENABLE_COMPLETED" else "○" if state == "AVAILABLE" else "⋯"
            print(f"  {status_icon} {name}: {state}")
        
        print("\n" + "=" * 60)
        print("Legend: ✓ = Enabled, ○ = Available (not enabled), ⋯ = Other state")
        print("=" * 60 + "\n")


def enable_system_tables_via_sql(
    sql_executor_func,
    warehouse_id: str,
    schemas: Optional[List[str]] = None
) -> Dict[str, bool]:
    """
    Alternative method: Enable system tables via SQL statements.
    
    This function uses the SQL execution approach similar to the user's
    execute_sql_query function.
    
    Args:
        sql_executor_func: A function that executes SQL queries 
                          (like execute_sql_query from user's example)
        warehouse_id: SQL warehouse ID
        schemas: List of schema names to enable, or None for all
        
    Returns:
        Dictionary mapping schema names to success status
    """
    all_schemas = schemas or [
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
    
    results = {}
    
    for schema in all_schemas:
        # SQL to enable system schema
        sql = f"""
        -- Enable system schema: {schema}
        ALTER SCHEMA system.{schema} ENABLE CHANGE TRACKING;
        """
        
        try:
            print(f"Enabling system schema via SQL: {schema}")
            result = sql_executor_func(sql, warehouse_id)
            results[schema] = result is not None
        except Exception as e:
            print(f"Error enabling {schema}: {str(e)}")
            results[schema] = False
    
    return results


# Example usage and main execution
if __name__ == "__main__":
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="Enable Databricks System Tables",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Enable all system schemas
  python enable_system_tables.py --workspace-url https://adb-xxx.azuredatabricks.net --token $DATABRICKS_TOKEN --enable-all

  # Enable specific schemas
  python enable_system_tables.py --workspace-url https://adb-xxx.azuredatabricks.net --token $DATABRICKS_TOKEN --schemas access billing compute

  # Check status only
  python enable_system_tables.py --workspace-url https://adb-xxx.azuredatabricks.net --token $DATABRICKS_TOKEN --status

Available system schemas:
  access      - Audit logs and access information
  billing     - Usage and billing data
  compute     - Cluster and compute metadata
  lineage     - Table and column lineage tracking
  storage     - Storage optimization data
  workflow    - Jobs and workflow metadata
  marketplace - Marketplace access events
  serving     - Model serving metadata
  query       - SQL query history
        """
    )
    
    parser.add_argument(
        "--workspace-url",
        type=str,
        default=os.environ.get("DATABRICKS_HOST"),
        help="Databricks workspace URL (or set DATABRICKS_HOST env var)"
    )
    
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("DATABRICKS_TOKEN"),
        help="Databricks access token (or set DATABRICKS_TOKEN env var)"
    )
    
    parser.add_argument(
        "--metastore-id",
        type=str,
        default=None,
        help="Metastore ID (optional, will auto-detect if not provided)"
    )
    
    parser.add_argument(
        "--schemas",
        type=str,
        nargs="+",
        help="Specific schemas to enable (space-separated)"
    )
    
    parser.add_argument(
        "--enable-all",
        action="store_true",
        help="Enable all available system schemas"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show current status of system schemas"
    )
    
    parser.add_argument(
        "--disable",
        type=str,
        nargs="+",
        help="Schemas to disable (space-separated)"
    )
    
    args = parser.parse_args()
    
    # Validate required arguments
    if not args.workspace_url:
        print("Error: --workspace-url is required (or set DATABRICKS_HOST env var)")
        exit(1)
        
    if not args.token:
        print("Error: --token is required (or set DATABRICKS_TOKEN env var)")
        exit(1)
    
    # Create manager instance
    manager = DatabricksSystemTablesManager(
        workspace_url=args.workspace_url,
        token=args.token,
        metastore_id=args.metastore_id
    )
    
    # Execute requested operations
    if args.status:
        manager.get_system_tables_status()
        
    elif args.enable_all:
        results = manager.enable_all_system_schemas()
        print("\nResults:")
        for schema, success in results.items():
            status = "✓ Enabled" if success else "✗ Failed"
            print(f"  {schema}: {status}")
            
    elif args.schemas:
        print(f"Enabling specified schemas: {', '.join(args.schemas)}")
        for schema in args.schemas:
            if schema not in manager.AVAILABLE_SCHEMAS:
                print(f"Warning: '{schema}' is not a recognized system schema")
            manager.enable_system_schema(schema)
            
    elif args.disable:
        print(f"Disabling specified schemas: {', '.join(args.disable)}")
        for schema in args.disable:
            manager.disable_system_schema(schema)
            
    else:
        # Default: show status
        manager.get_system_tables_status()
        print("\nUse --enable-all to enable all schemas, or --schemas to enable specific ones.")
        print("Run with --help for more options.")
