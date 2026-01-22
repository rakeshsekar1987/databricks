"""
Databricks Secrets Discovery Utility

Run this code in a Databricks notebook to discover all available
secret scopes and their keys in your environment.

Note: You can see the scope and key names, but NOT the actual secret values
(Databricks redacts them for security).
"""

# =============================================================================
# METHOD 1: Using dbutils.secrets (Run in Databricks Notebook)
# =============================================================================

def list_all_scopes_and_secrets():
    """
    List all secret scopes and their keys in the current Databricks workspace.
    
    Run this function in a Databricks notebook cell.
    """
    print("=" * 70)
    print("DATABRICKS SECRET SCOPES AND KEYS DISCOVERY")
    print("=" * 70)
    
    try:
        # List all secret scopes
        scopes = dbutils.secrets.listScopes()
        
        if not scopes:
            print("\nNo secret scopes found in this workspace.")
            print("You may need to create scopes first using the Databricks CLI or API.")
            return
        
        print(f"\nFound {len(scopes)} secret scope(s):\n")
        
        all_secrets = []
        
        for scope in scopes:
            scope_name = scope.name
            print(f"{'─' * 70}")
            print(f"📁 SCOPE: {scope_name}")
            print(f"{'─' * 70}")
            
            try:
                # List all secrets in this scope
                secrets = dbutils.secrets.list(scope_name)
                
                if secrets:
                    print(f"   Found {len(secrets)} secret(s):")
                    for secret in secrets:
                        key_name = secret.key
                        print(f"   🔑 Key: {key_name}")
                        all_secrets.append({
                            'scope': scope_name,
                            'key': key_name
                        })
                else:
                    print("   (No secrets in this scope)")
                    
            except Exception as e:
                print(f"   ⚠️  Error listing secrets: {str(e)}")
            
            print()
        
        # Summary
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Total Scopes: {len(scopes)}")
        print(f"Total Secrets: {len(all_secrets)}")
        
        print("\n" + "=" * 70)
        print("HOW TO USE THESE SECRETS IN YOUR CODE:")
        print("=" * 70)
        for secret in all_secrets:
            print(f'dbutils.secrets.get(scope="{secret["scope"]}", key="{secret["key"]}")')
        
        return all_secrets
        
    except NameError:
        print("ERROR: dbutils is not available.")
        print("This script must be run inside a Databricks notebook.")
        return None
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return None


def get_secret_value(scope_name, key_name):
    """
    Retrieve a secret value (will be redacted in notebook output).
    
    Args:
        scope_name (str): The secret scope name
        key_name (str): The secret key name
    
    Returns:
        str: The secret value (redacted in display)
    """
    try:
        value = dbutils.secrets.get(scope=scope_name, key=key_name)
        print(f"✅ Successfully retrieved secret: {scope_name}/{key_name}")
        print(f"   Value length: {len(value)} characters")
        print(f"   (Actual value is redacted for security)")
        return value
    except Exception as e:
        print(f"❌ Failed to retrieve secret: {str(e)}")
        return None


def check_secret_exists(scope_name, key_name):
    """
    Check if a specific secret exists.
    
    Args:
        scope_name (str): The secret scope name
        key_name (str): The secret key name
    
    Returns:
        bool: True if secret exists, False otherwise
    """
    try:
        dbutils.secrets.get(scope=scope_name, key=key_name)
        print(f"✅ Secret exists: {scope_name}/{key_name}")
        return True
    except Exception as e:
        print(f"❌ Secret not found: {scope_name}/{key_name}")
        print(f"   Error: {str(e)}")
        return False


# =============================================================================
# METHOD 2: Using Databricks REST API (Alternative)
# =============================================================================

def list_scopes_via_api(workspace_url, token):
    """
    List secret scopes using the Databricks REST API.
    
    Args:
        workspace_url (str): Your Databricks workspace URL
        token (str): Your Databricks personal access token
    
    Returns:
        list: List of scope names
    """
    import requests
    
    url = f"{workspace_url}/api/2.0/secrets/scopes/list"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        scopes = result.get('scopes', [])
        print(f"Found {len(scopes)} scope(s) via API:")
        for scope in scopes:
            print(f"  - {scope.get('name')} (backend: {scope.get('backend_type', 'DATABRICKS')})")
        
        return [s.get('name') for s in scopes]
    except Exception as e:
        print(f"API Error: {str(e)}")
        return []


def list_secrets_via_api(workspace_url, token, scope_name):
    """
    List secrets in a scope using the Databricks REST API.
    
    Args:
        workspace_url (str): Your Databricks workspace URL
        token (str): Your Databricks personal access token
        scope_name (str): The scope to list secrets from
    
    Returns:
        list: List of secret keys
    """
    import requests
    
    url = f"{workspace_url}/api/2.0/secrets/list"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"scope": scope_name}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()
        
        secrets = result.get('secrets', [])
        print(f"Found {len(secrets)} secret(s) in scope '{scope_name}':")
        for secret in secrets:
            print(f"  - {secret.get('key')}")
        
        return [s.get('key') for s in secrets]
    except Exception as e:
        print(f"API Error: {str(e)}")
        return []


# =============================================================================
# DATABRICKS CLI COMMANDS (Run in Terminal)
# =============================================================================

CLI_COMMANDS = """
# =============================================================================
# DATABRICKS CLI COMMANDS
# =============================================================================

# First, install and configure the Databricks CLI:
pip install databricks-cli
databricks configure --token

# List all secret scopes:
databricks secrets list-scopes

# List all secrets in a specific scope:
databricks secrets list --scope <scope-name>

# Example:
databricks secrets list --scope generic-scope

# Create a new scope:
databricks secrets create-scope --scope my-new-scope

# Add a secret to a scope:
databricks secrets put --scope my-scope --key my-secret-key

# Delete a secret:
databricks secrets delete --scope my-scope --key my-secret-key

# Delete a scope:
databricks secrets delete-scope --scope my-scope
"""


# =============================================================================
# RUN THIS IN YOUR DATABRICKS NOTEBOOK
# =============================================================================

NOTEBOOK_CODE = '''
# =============================================================================
# COPY AND PASTE THIS INTO A DATABRICKS NOTEBOOK CELL
# =============================================================================

# List all scopes
print("SECRET SCOPES IN THIS WORKSPACE:")
print("=" * 50)
scopes = dbutils.secrets.listScopes()
for scope in scopes:
    print(f"\\n📁 Scope: {scope.name}")
    secrets = dbutils.secrets.list(scope.name)
    for secret in secrets:
        print(f"   🔑 Key: {secret.key}")

# =============================================================================
# Or run the full discovery:
# =============================================================================
# %run /path/to/this/notebook
# list_all_scopes_and_secrets()
'''

print(NOTEBOOK_CODE)


# =============================================================================
# MAIN - Run when executed in Databricks
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DATABRICKS SECRETS DISCOVERY")
    print("=" * 70)
    print("\nThis script helps you discover all secret scopes and keys.")
    print("\nTo use this in Databricks, copy the code below into a notebook cell:\n")
    print(NOTEBOOK_CODE)
    print("\n" + "=" * 70)
    print("CLI COMMANDS (for terminal use):")
    print("=" * 70)
    print(CLI_COMMANDS)
