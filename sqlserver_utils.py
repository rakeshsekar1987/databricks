"""
SQL Server Utility Functions
Provides methods for metadata queries, change tracking, schema detection, and DDL operations.
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType, StructField, DataType
import re

logger = logging.getLogger(__name__)


class SQLServerUtils:
    """Utility class for SQL Server operations and metadata queries."""
    
    def __init__(self, spark: SparkSession, connection_config: Dict[str, Any]):
        """
        Initialize SQL Server utilities.
        
        Args:
            spark: SparkSession instance
            connection_config: Dictionary with connection details (host, port, database, username, password, etc.)
        """
        self.spark = spark
        self.connection_config = connection_config
        self.jdbc_url = self._build_jdbc_url()
        self.jdbc_properties = self._build_jdbc_properties()
    
    def _build_jdbc_url(self) -> str:
        """Build JDBC URL for SQL Server."""
        host = self.connection_config['host']
        port = self.connection_config.get('port', 1433)
        database = self.connection_config['database']
        
        # Handle gateway if specified
        if self.connection_config.get('jdbc_options', {}).get('gateway_host'):
            host = self.connection_config['jdbc_options']['gateway_host']
            port = self.connection_config['jdbc_options'].get('gateway_port', 443)
        
        url = f"jdbc:sqlserver://{host}:{port};databaseName={database}"
        
        # Add SSL options
        jdbc_opts = self.connection_config.get('jdbc_options', {})
        if jdbc_opts.get('encrypt', True):
            url += ";encrypt=true"
        if jdbc_opts.get('trustServerCertificate', False):
            url += ";trustServerCertificate=true"
        
        return url
    
    def _build_jdbc_properties(self) -> Dict[str, str]:
        """Build JDBC connection properties."""
        props = {
            "user": self.connection_config['username'],
            "password": self.connection_config['password'],
            "driver": "com.microsoft.sqlserver.jdbc.SQLServerDriver"
        }
        
        jdbc_opts = self.connection_config.get('jdbc_options', {})
        if jdbc_opts.get('applicationName'):
            props['applicationName'] = jdbc_opts['applicationName']
        if jdbc_opts.get('selectMethod'):
            props['selectMethod'] = jdbc_opts['selectMethod']
        
        return props
    
    def get_table_size_mb(self, schema: str, table: str) -> float:
        """
        Query SQL Server to get table size in MB.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            Table size in MB
        """
        query = f"""
        SELECT 
            CAST(ROUND(((SUM(a.total_pages) * 8) / 1024.0), 2) AS FLOAT) AS size_mb
        FROM sys.tables t
        INNER JOIN sys.indexes i ON t.object_id = i.object_id
        INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
        INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
        WHERE t.schema_id = SCHEMA_ID('{schema}')
          AND t.name = '{table}'
          AND i.object_id > 255
          AND i.index_id <= 1
        GROUP BY t.name, t.schema_id
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS size_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()
            if result and result[0][0] is not None:
                return float(result[0][0])
            else:
                logger.warning(f"Could not determine size for {schema}.{table}, defaulting to 128 MB")
                return 128.0
        except Exception as e:
            logger.error(f"Error getting table size for {schema}.{table}: {str(e)}")
            return 128.0  # Default to 128 MB if query fails
    
    def get_primary_key_columns(self, schema: str, table: str) -> List[str]:
        """
        Get primary key columns for a table.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            List of primary key column names
        """
        query = f"""
        SELECT c.name AS column_name
        FROM sys.key_constraints kc
        INNER JOIN sys.index_columns ic ON kc.parent_object_id = ic.object_id 
            AND kc.unique_index_id = ic.index_id
        INNER JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        INNER JOIN sys.tables t ON kc.parent_object_id = t.object_id
        WHERE t.schema_id = SCHEMA_ID('{schema}')
          AND t.name = '{table}'
        ORDER BY ic.key_ordinal
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS pk_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            pk_columns = [row[0] for row in df.collect()]
            return pk_columns if pk_columns else []
        except Exception as e:
            logger.error(f"Error getting primary key for {schema}.{table}: {str(e)}")
            return []
    
    def get_table_schema(self, schema: str, table: str) -> StructType:
        """
        Get Spark schema for a SQL Server table.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            Spark StructType schema
        """
        try:
            # Read a small sample to infer schema
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"{schema}.{table}"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).option(
                "fetchSize", "1"
            ).limit(1).load()
            
            return df.schema
        except Exception as e:
            logger.error(f"Error getting schema for {schema}.{table}: {str(e)}")
            raise
    
    def is_numeric_column(self, schema: str, table: str, column: str) -> bool:
        """
        Check if a column is numeric and suitable for range partitioning.
        
        Args:
            schema: Schema name
            table: Table name
            column: Column name
            
        Returns:
            True if column is numeric (int, bigint, decimal, etc.)
        """
        query = f"""
        SELECT t.name AS type_name
        FROM sys.columns c
        INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
        INNER JOIN sys.tables tbl ON c.object_id = tbl.object_id
        WHERE tbl.schema_id = SCHEMA_ID('{schema}')
          AND tbl.name = '{table}'
          AND c.name = '{column}'
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS type_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()
            if result:
                type_name = result[0][0].lower()
                numeric_types = ['int', 'bigint', 'smallint', 'tinyint', 'decimal', 
                               'numeric', 'float', 'real', 'money', 'smallmoney']
                return any(nt in type_name for nt in numeric_types)
            return False
        except Exception as e:
            logger.warning(f"Error checking column type for {schema}.{table}.{column}: {str(e)}")
            return False
    
    def get_column_min_max(self, schema: str, table: str, column: str) -> Tuple[Optional[Any], Optional[Any]]:
        """
        Get min and max values for a numeric column (for range partitioning).
        
        Args:
            schema: Schema name
            table: Table name
            column: Column name
            
        Returns:
            Tuple of (min_value, max_value)
        """
        query = f"""
        SELECT MIN([{column}]) AS min_val, MAX([{column}]) AS max_val
        FROM [{schema}].[{table}]
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS minmax_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()[0]
            return (result[0], result[1])
        except Exception as e:
            logger.error(f"Error getting min/max for {schema}.{table}.{column}: {str(e)}")
            return (None, None)
    
    def get_change_tracking_version(self, schema: str, table: str) -> Optional[int]:
        """
        Get the current Change Tracking version for a table.
        Requires Change Tracking to be enabled on the database and table.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            Current Change Tracking version number, or None if not available
        """
        query = f"""
        SELECT CHANGE_TRACKING_CURRENT_VERSION() AS current_version
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS ct_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()
            if result and result[0][0] is not None:
                return int(result[0][0])
            return None
        except Exception as e:
            logger.warning(f"Change Tracking not available or error: {str(e)}")
            return None
    
    def get_changed_rows(self, schema: str, table: str, last_version: int, 
                        pk_columns: List[str]) -> DataFrame:
        """
        Get changed rows using Change Tracking.
        
        Args:
            schema: Schema name
            table: Table name
            last_version: Last processed Change Tracking version
            pk_columns: Primary key columns
            
        Returns:
            DataFrame with changed rows (including SYS_CHANGE_OPERATION column)
        """
        pk_cols_str = ", ".join([f"t.[{col}]" for col in pk_columns])
        pk_join = " AND ".join([f"t.[{col}] = c.[{col}]" for col in pk_columns])
        
        query = f"""
        SELECT t.*, c.SYS_CHANGE_OPERATION
        FROM [{schema}].[{table}] t
        RIGHT OUTER JOIN CHANGETABLE(CHANGES [{schema}].[{table}], {last_version}) AS c
        ON {pk_join}
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS changes_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).option(
                "fetchSize", str(self.connection_config.get('runtime', {}).get('fetch_size', 15000))
            ).load()
            
            return df
        except Exception as e:
            logger.error(f"Error getting changed rows for {schema}.{table}: {str(e)}")
            raise
    
    def get_cdc_lsn(self, capture_instance: str) -> Optional[str]:
        """
        Get the last processed LSN for CDC (Change Data Capture).
        
        Args:
            capture_instance: CDC capture instance name (usually schema_table)
            
        Returns:
            Last processed LSN as string, or None
        """
        query = f"""
        SELECT MAX(__$start_lsn) AS max_lsn
        FROM cdc.[{capture_instance}_CT]
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS cdc_query"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()
            if result and result[0][0] is not None:
                return str(result[0][0])
            return None
        except Exception as e:
            logger.warning(f"CDC not available or error: {str(e)}")
            return None
    
    def check_change_tracking_enabled(self, schema: str, table: str) -> bool:
        """
        Check if Change Tracking is enabled for a table.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            True if Change Tracking is enabled
        """
        query = f"""
        SELECT is_track_columns_updated_on
        FROM sys.change_tracking_tables
        WHERE object_id = OBJECT_ID('{schema}.{table}')
        """
        
        try:
            df = self.spark.read.format("jdbc").option("url", self.jdbc_url).option(
                "dbtable", f"({query}) AS ct_check"
            ).option("user", self.jdbc_properties["user"]).option(
                "password", self.jdbc_properties["password"]
            ).option("driver", self.jdbc_properties["driver"]).load()
            
            result = df.collect()
            return len(result) > 0
        except Exception as e:
            logger.warning(f"Error checking Change Tracking: {str(e)}")
            return False
    
    def detect_schema_changes(self, source_schema: StructType, 
                            target_schema: StructType) -> Dict[str, Any]:
        """
        Detect schema changes between source and target schemas.
        
        Args:
            source_schema: Source (SQL Server) schema
            target_schema: Target (Delta) schema
            
        Returns:
            Dictionary with:
            - added_columns: List of new columns to add
            - removed_columns: List of columns removed (destructive)
            - type_changes: List of type changes
            - renamed_columns: List of potential renames (heuristic-based)
        """
        source_fields = {f.name.lower(): f for f in source_schema.fields}
        target_fields = {f.name.lower(): f for f in target_schema.fields}
        
        added_columns = []
        removed_columns = []
        type_changes = []
        renamed_columns = []
        
        # Find added columns
        for name, field in source_fields.items():
            if name not in target_fields:
                added_columns.append(field)
        
        # Find removed columns
        for name, field in target_fields.items():
            if name not in source_fields:
                removed_columns.append(field)
        
        # Find type changes
        for name in source_fields:
            if name in target_fields:
                source_type = source_fields[name].dataType
                target_type = target_fields[name].dataType
                if str(source_type) != str(target_type):
                    type_changes.append({
                        'column': name,
                        'source_type': str(source_type),
                        'target_type': str(target_type)
                    })
        
        # Heuristic-based rename detection (simple: by type and nullable)
        # This is a basic implementation - production should use more sophisticated matching
        for removed_field in removed_columns:
            for added_field in added_columns:
                if (removed_field.dataType == added_field.dataType and 
                    removed_field.nullable == added_field.nullable):
                    renamed_columns.append({
                        'old_name': removed_field.name,
                        'new_name': added_field.name,
                        'confidence': 'low'  # Manual review recommended
                    })
        
        return {
            'added_columns': added_columns,
            'removed_columns': removed_columns,
            'type_changes': type_changes,
            'renamed_columns': renamed_columns
        }
