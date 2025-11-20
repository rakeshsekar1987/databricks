"""
Table Ingestion Module
Handles full and incremental load logic for individual tables, including schema evolution and Delta MERGE.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
import time
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, lit, when, expr, hash as spark_hash, abs as spark_abs
from pyspark.sql.types import StructType
from delta.tables import DeltaTable
import json

from sqlserver_utils import SQLServerUtils

logger = logging.getLogger(__name__)


class TableIngestion:
    """Handles ingestion of a single table from SQL Server to Delta Lake."""
    
    def __init__(self, spark: SparkSession, connection_config: Dict[str, Any], 
                 table_config: Dict[str, Any], runtime_config: Dict[str, Any]):
        """
        Initialize table ingestion.
        
        Args:
            spark: SparkSession instance
            connection_config: Connection configuration
            table_config: Table-specific configuration
            runtime_config: Runtime options (fetch_size, partitioning, etc.)
        """
        self.spark = spark
        self.connection_config = connection_config
        self.table_config = table_config
        self.runtime_config = runtime_config
        self.sql_utils = SQLServerUtils(spark, connection_config)
        
        self.schema = table_config.get('schema')
        self.table = table_config.get('table')
        self.full_table_name = f"{self.schema}.{self.table}"
        self.delta_path = table_config.get('delta_table_path')
        self.mode = table_config.get('mode', 'full')
        self.pk_columns = table_config.get('pk_columns', [])
        
        # Metrics
        self.metrics = {
            'table': self.full_table_name,
            'mode': self.mode,
            'start_time': None,
            'end_time': None,
            'rows_read': 0,
            'bytes_read': 0,
            'partitions_used': 0,
            'fetch_size': runtime_config.get('fetch_size', 15000),
            'elapsed_seconds': 0,
            'status': 'unknown',
            'error_message': None
        }
    
    def calculate_parallelism(self, table_size_mb: Optional[float] = None) -> int:
        """
        Calculate number of partitions based on table size.
        Formula: ceil(table_size_MB / min_partition_size_MB)
        
        Args:
            table_size_mb: Table size in MB (if None, will query SQL Server)
            
        Returns:
            Number of partitions to use
        """
        # Check for override
        if self.runtime_config.get('parallelism_override'):
            return int(self.runtime_config['parallelism_override'])
        
        # Get table size if not provided
        if table_size_mb is None:
            table_size_mb = self.table_config.get('size_MB')
            if table_size_mb is None:
                logger.info(f"Table size not provided, querying SQL Server for {self.full_table_name}")
                table_size_mb = self.sql_utils.get_table_size_mb(self.schema, self.table)
        
        min_partition_size_mb = self.runtime_config.get('min_partition_size_mb', 128)
        max_partitions = self.runtime_config.get('max_partitions_per_table', 512)
        
        # Calculate parallelism
        parallelism = int(table_size_mb / min_partition_size_mb)
        parallelism = max(1, parallelism)  # At least 1 partition
        parallelism = min(parallelism, max_partitions)  # Cap at max
        
        logger.info(f"Table {self.full_table_name}: size={table_size_mb:.2f} MB, "
                   f"parallelism={parallelism} partitions")
        
        return parallelism
    
    def read_table_full_load(self, num_partitions: int) -> DataFrame:
        """
        Read table with parallelized JDBC reads for full load.
        
        Args:
            num_partitions: Number of partitions to create
            
        Returns:
            DataFrame with table data
        """
        jdbc_url = self.sql_utils.jdbc_url
        jdbc_props = self.sql_utils.jdbc_properties
        fetch_size = self.runtime_config.get('fetch_size', 15000)
        
        partition_column = self.table_config.get('partition_column_hint')
        
        # Strategy 1: Use numeric range partitioning if partition_column is numeric
        if partition_column and self.sql_utils.is_numeric_column(self.schema, self.table, partition_column):
            min_val, max_val = self.sql_utils.get_column_min_max(self.schema, self.table, partition_column)
            
            if min_val is not None and max_val is not None and min_val != max_val:
                logger.info(f"Using range partitioning on {partition_column} "
                           f"(min={min_val}, max={max_val}, partitions={num_partitions})")
                
                return self.spark.read.format("jdbc").option("url", jdbc_url).option(
                    "dbtable", self.full_table_name
                ).option("user", jdbc_props["user"]).option(
                    "password", jdbc_props["password"]
                ).option("driver", jdbc_props["driver"]).option(
                    "fetchSize", str(fetch_size)
                ).option("partitionColumn", partition_column).option(
                    "lowerBound", str(min_val)
                ).option("upperBound", str(max_val)
                ).option("numPartitions", str(num_partitions)
                ).load()
        
        # Strategy 2: Use hash-based partitioning on primary key
        if self.pk_columns:
            logger.info(f"Using hash-based partitioning on primary key: {self.pk_columns}")
            
            # Read full table first (this will be partitioned by Spark)
            df = self.spark.read.format("jdbc").option("url", jdbc_url).option(
                "dbtable", self.full_table_name
            ).option("user", jdbc_props["user"]).option(
                "password", jdbc_props["password"]
            ).option("driver", jdbc_props["driver"]).option(
                "fetchSize", str(fetch_size)
            ).load()
            
            # Repartition using hash of primary key
            if len(self.pk_columns) == 1:
                df = df.repartition(num_partitions, col(self.pk_columns[0]))
            else:
                # Hash multiple PK columns
                hash_expr = spark_hash(*[col(c) for c in self.pk_columns])
                df = df.withColumn("_hash", spark_abs(hash_expr) % num_partitions)
                df = df.repartition(num_partitions, col("_hash")).drop("_hash")
            
            return df
        
        # Strategy 3: Fallback to simple read with repartition
        logger.warning(f"No partitioning strategy available for {self.full_table_name}, "
                      f"using simple read with repartition")
        
        df = self.spark.read.format("jdbc").option("url", jdbc_url).option(
            "dbtable", self.full_table_name
        ).option("user", jdbc_props["user"]).option(
            "password", jdbc_props["password"]
        ).option("driver", jdbc_props["driver"]).option(
            "fetchSize", str(fetch_size)
        ).load()
        
        return df.repartition(num_partitions)
    
    def read_table_incremental(self, last_version: int) -> DataFrame:
        """
        Read changed rows using Change Tracking.
        
        Args:
            last_version: Last processed Change Tracking version
            
        Returns:
            DataFrame with changed rows
        """
        fetch_size = self.runtime_config.get('fetch_size', 15000)
        
        df = self.sql_utils.get_changed_rows(
            self.schema, self.table, last_version, self.pk_columns
        )
        
        return df
    
    def apply_schema_evolution(self, source_df: DataFrame) -> None:
        """
        Apply schema evolution to Delta table (add new columns).
        
        Args:
            source_df: Source DataFrame with new schema
        """
        try:
            # Check if Delta table exists
            delta_table = DeltaTable.forPath(self.spark, self.delta_path)
            target_schema = delta_table.toDF().schema
            
            # Detect schema changes
            schema_changes = self.sql_utils.detect_schema_changes(
                source_df.schema, target_schema
            )
            
            # Add new columns
            if schema_changes['added_columns']:
                logger.info(f"Adding {len(schema_changes['added_columns'])} new columns to {self.delta_path}")
                
                for field in schema_changes['added_columns']:
                    alter_sql = f"ALTER TABLE delta.`{self.delta_path}` ADD COLUMN {field.name} {field.dataType.simpleString()}"
                    if field.nullable:
                        alter_sql += " NULL"
                    else:
                        alter_sql += " NOT NULL"
                    
                    try:
                        self.spark.sql(alter_sql)
                        logger.info(f"Added column: {field.name}")
                    except Exception as e:
                        logger.error(f"Error adding column {field.name}: {str(e)}")
            
            # Log removed columns (destructive change - manual review needed)
            if schema_changes['removed_columns']:
                logger.warning(f"DESTRUCTIVE CHANGE: {len(schema_changes['removed_columns'])} columns removed "
                             f"from source. Manual review required: {[f.name for f in schema_changes['removed_columns']]}")
            
            # Log type changes
            if schema_changes['type_changes']:
                logger.warning(f"Type changes detected. Manual review required: {schema_changes['type_changes']}")
            
            # Log potential renames
            if schema_changes['renamed_columns']:
                logger.warning(f"Potential column renames detected (low confidence): "
                             f"{schema_changes['renamed_columns']}")
        
        except Exception as e:
            # Table doesn't exist yet, schema will be created on first write
            logger.info(f"Delta table doesn't exist yet, will create with source schema: {str(e)}")
    
    def write_to_delta_full_load(self, df: DataFrame) -> None:
        """
        Write DataFrame to Delta table for full load.
        
        Args:
            df: DataFrame to write
        """
        write_mode = self.runtime_config.get('delta', {}).get('default_write_mode', 'append')
        merge_schema = self.runtime_config.get('delta', {}).get('merge_schema', True)
        
        # Apply schema evolution if table exists and we're appending
        if write_mode == 'append':
            try:
                self.apply_schema_evolution(df)
            except:
                pass  # Table doesn't exist yet, will be created
        
        # Write to Delta
        writer = df.write.format("delta").mode(write_mode)
        
        if merge_schema:
            writer = writer.option("mergeSchema", "true")
        
        writer.save(self.delta_path)
        
        row_count = df.count()
        logger.info(f"Successfully wrote {row_count} rows to {self.delta_path}")
    
    def write_to_delta_incremental(self, df: DataFrame) -> None:
        """
        Write DataFrame to Delta table using MERGE for incremental load (idempotent upsert).
        
        Args:
            df: DataFrame with changed rows (must include SYS_CHANGE_OPERATION column)
        """
        if not self.pk_columns:
            raise ValueError(f"Primary key columns required for incremental load on {self.full_table_name}")
        
        # Ensure Delta table exists
        try:
            delta_table = DeltaTable.forPath(self.spark, self.delta_path)
        except:
            # Table doesn't exist, create it with first write
            logger.info(f"Delta table doesn't exist, creating with full load first")
            df_without_op = df.drop("SYS_CHANGE_OPERATION")
            self.write_to_delta_full_load(df_without_op)
            return
        
        # Apply schema evolution
        try:
            self.apply_schema_evolution(df.drop("SYS_CHANGE_OPERATION"))
        except:
            pass
        
        # Prepare merge conditions
        merge_condition = " AND ".join([f"target.{col} = source.{col}" for col in self.pk_columns])
        
        # Prepare column mappings (exclude SYS_CHANGE_OPERATION)
        source_columns = [col for col in df.columns if col != "SYS_CHANGE_OPERATION"]
        
        # Perform MERGE
        merge_builder = delta_table.alias("target").merge(
            df.alias("source"),
            merge_condition
        )
        
        # Update matched rows (for updates)
        update_set = {c: f"source.{c}" for c in source_columns}
        merge_builder = merge_builder.whenMatchedUpdate(
            condition=expr("source.SYS_CHANGE_OPERATION = 'U'"),
            set=update_set
        )
        
        # Delete matched rows (for deletes)
        merge_builder = merge_builder.whenMatchedDelete(
            condition=expr("source.SYS_CHANGE_OPERATION = 'D'")
        )
        
        # Insert new rows (for inserts and updates that don't match)
        insert_values = {c: f"source.{c}" for c in source_columns}
        merge_builder = merge_builder.whenNotMatchedInsert(
            condition=expr("source.SYS_CHANGE_OPERATION IN ('I', 'U')"),
            values=insert_values
        )
        
        merge_builder.execute()
        
        logger.info(f"Successfully merged {df.count()} changed rows to {self.delta_path}")
    
    def get_last_processed_version(self) -> Optional[int]:
        """
        Get last processed Change Tracking version from checkpoint table.
        
        Returns:
            Last processed version, or None if not found
        """
        checkpoint_path = self.runtime_config.get('checkpoint_location')
        if not checkpoint_path:
            return None
        
        try:
            checkpoint_df = self.spark.read.format("delta").load(checkpoint_path)
            result = checkpoint_df.filter(
                (col("schema_name") == self.schema) & 
                (col("table_name") == self.table)
            ).select("last_version").collect()
            
            if result and result[0][0] is not None:
                return int(result[0][0])
            return None
        except:
            return None
    
    def update_checkpoint(self, version: int) -> None:
        """
        Update checkpoint table with last processed version.
        
        Args:
            version: Change Tracking version to record
        """
        checkpoint_path = self.runtime_config.get('checkpoint_location')
        if not checkpoint_path:
            return
        
        checkpoint_data = [{
            'schema_name': self.schema,
            'table_name': self.table,
            'last_version': version,
            'updated_at': time.time()
        }]
        
        checkpoint_df = self.spark.createDataFrame(checkpoint_data)
        
        # Initialize checkpoint table if it doesn't exist
        try:
            checkpoint_table = DeltaTable.forPath(self.spark, checkpoint_path)
            checkpoint_table.alias("target").merge(
                checkpoint_df.alias("source"),
                "target.schema_name = source.schema_name AND target.table_name = source.table_name"
            ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
        except:
            # Table doesn't exist, create it
            checkpoint_df.write.format("delta").mode("overwrite").save(checkpoint_path)
    
    def ingest(self) -> Dict[str, Any]:
        """
        Main ingestion method - orchestrates full or incremental load.
        
        Returns:
            Dictionary with ingestion metrics
        """
        self.metrics['start_time'] = time.time()
        
        try:
            if self.mode == 'full':
                # Full load
                logger.info(f"Starting full load for {self.full_table_name}")
                
                # Calculate parallelism
                num_partitions = self.calculate_parallelism()
                self.metrics['partitions_used'] = num_partitions
                
                # Read table
                df = self.read_table_full_load(num_partitions)
                
                # Collect metrics
                row_count = df.count()
                self.metrics['rows_read'] = row_count
                
                # Estimate bytes (rough approximation)
                sample_size = min(1000, row_count)
                if sample_size > 0:
                    sample_df = df.limit(sample_size)
                    sample_bytes = len(str(sample_df.collect()).encode('utf-8'))
                    estimated_bytes = (sample_bytes / sample_size) * row_count
                    self.metrics['bytes_read'] = estimated_bytes
                
                # Write to Delta
                self.write_to_delta_full_load(df)
                
                self.metrics['status'] = 'success'
                
            elif self.mode == 'incremental':
                # Incremental load
                logger.info(f"Starting incremental load for {self.full_table_name}")
                
                # Get last processed version
                last_version = self.get_last_processed_version()
                if last_version is None:
                    logger.warning(f"No checkpoint found for {self.full_table_name}, "
                                 f"performing full load first")
                    # Fallback to full load
                    self.mode = 'full'
                    return self.ingest()
                
                # Get current version
                current_version = self.sql_utils.get_change_tracking_version(self.schema, self.table)
                if current_version is None:
                    raise ValueError(f"Change Tracking not available for {self.full_table_name}")
                
                if current_version <= last_version:
                    logger.info(f"No changes detected for {self.full_table_name} "
                              f"(current={current_version}, last={last_version})")
                    self.metrics['status'] = 'success'
                    self.metrics['rows_read'] = 0
                    return self.metrics
                
                # Read changed rows
                df = self.read_table_incremental(last_version)
                
                # Collect metrics
                row_count = df.count()
                self.metrics['rows_read'] = row_count
                
                if row_count > 0:
                    # Write to Delta using MERGE
                    self.write_to_delta_incremental(df)
                    
                    # Update checkpoint
                    self.update_checkpoint(current_version)
                else:
                    logger.info(f"No changed rows for {self.full_table_name}")
                
                self.metrics['status'] = 'success'
            
            else:
                raise ValueError(f"Invalid mode: {self.mode}")
            
        except Exception as e:
            logger.error(f"Error ingesting {self.full_table_name}: {str(e)}", exc_info=True)
            self.metrics['status'] = 'failed'
            self.metrics['error_message'] = str(e)
            raise
        
        finally:
            self.metrics['end_time'] = time.time()
            self.metrics['elapsed_seconds'] = self.metrics['end_time'] - self.metrics['start_time']
        
        return self.metrics
