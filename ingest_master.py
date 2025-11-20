"""
Master Orchestration Script
Entry point for SQL Server to Delta Lake ingestion pipeline.
Supports concurrent processing of up to 500 tables with monitoring and error handling.
"""

import sys
import yaml
import logging
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp
from delta.tables import DeltaTable

from ingest_table import TableIngestion
from sqlserver_utils import SQLServerUtils

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """Orchestrates ingestion of multiple tables from SQL Server to Delta Lake."""
    
    def __init__(self, config_path: str):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.spark = self._create_spark_session()
        self.metrics_location = self.config.get('runtime', {}).get('metrics_location', 
                                                                   '/mnt/delta/metrics/ingestion_metrics')
        
        # Initialize metrics collection
        self.all_metrics = []
        self.start_time = None
        self.end_time = None
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and parse YAML configuration."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Resolve secrets (Databricks secrets scope format: {{secrets/scope/key}})
            config = self._resolve_secrets(config)
            
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            raise
    
    def _resolve_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve Databricks secrets in configuration.
        Format: {{secrets/scope/key}}
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with secrets resolved
        """
        import re
        from pyspark.sql import SparkSession
        
        try:
            spark = SparkSession.getActiveSession()
            if spark is None:
                return config  # Can't resolve secrets without Spark session
            
            def resolve_value(value):
                if isinstance(value, str):
                    pattern = r'\{\{secrets/([^/]+)/([^}]+)\}\}'
                    match = re.search(pattern, value)
                    if match:
                        scope = match.group(1)
                        key = match.group(2)
                        try:
                            # Use dbutils to get secret (Databricks-specific)
                            from pyspark.dbutils import DBUtils
                            dbutils = DBUtils(spark)
                            secret_value = dbutils.secrets.get(scope=scope, key=key)
                            return value.replace(match.group(0), secret_value)
                        except:
                            logger.warning(f"Could not resolve secret: {scope}/{key}")
                            return value
                elif isinstance(value, dict):
                    return {k: resolve_value(v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [resolve_value(item) for item in value]
                return value
            
            return resolve_value(config)
        except Exception as e:
            logger.warning(f"Error resolving secrets: {str(e)}")
            return config
    
    def _create_spark_session(self) -> SparkSession:
        """Create SparkSession with optimized configuration."""
        spark_config = self.config.get('cluster', {}).get('spark_config', {})
        
        builder = SparkSession.builder.appName("SQLServer-Delta-Ingestion")
        
        # Apply Spark configuration
        for key, value in spark_config.items():
            builder = builder.config(key, value)
        
        # Enable Delta Lake
        spark = builder.getOrCreate()
        
        # Set log level
        spark.sparkContext.setLogLevel("WARN")
        
        return spark
    
    def _calculate_required_parallelism(self) -> Dict[str, Any]:
        """
        Calculate required parallelism and cluster sizing for target SLA.
        
        Returns:
            Dictionary with parallelism recommendations
        """
        tables = self.config.get('tables', [])
        total_size_mb = sum(t.get('size_MB', 128) for t in tables)
        num_tables = len(tables)
        
        # Calculate parallelism per table
        min_partition_size_mb = self.config.get('runtime', {}).get('min_partition_size_mb', 128)
        total_partitions = sum(
            max(1, int(t.get('size_MB', 128) / min_partition_size_mb))
            for t in tables
        )
        
        # Cluster specs
        cluster_config = self.config.get('cluster', {})
        cores_per_node = cluster_config.get('cores_per_node', 4)
        workers = cluster_config.get('workers', 16)
        total_cores = cores_per_node * workers
        
        # Estimate time (rough calculation)
        # Assume each partition can process ~100 MB/min with good parallelism
        estimated_minutes = (total_size_mb / 100) / min(total_cores, total_partitions)
        
        # Target: 20 minutes
        target_minutes = 20
        if estimated_minutes > target_minutes:
            # Calculate required cores
            required_cores = int((total_size_mb / 100) / target_minutes)
            recommended_workers = max(workers, int(required_cores / cores_per_node))
        else:
            recommended_workers = workers
        
        return {
            'total_tables': num_tables,
            'total_size_mb': total_size_mb,
            'total_partitions': total_partitions,
            'current_cores': total_cores,
            'estimated_minutes': estimated_minutes,
            'recommended_workers': recommended_workers,
            'recommended_cores': recommended_workers * cores_per_node,
            'target_sla_minutes': target_minutes
        }
    
    def _ingest_single_table(self, table_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest a single table (wrapper for error handling and retries).
        
        Args:
            table_config: Table configuration
            
        Returns:
            Metrics dictionary
        """
        table_name = f"{table_config.get('schema')}.{table_config.get('table')}"
        retry_config = self.config.get('runtime', {}).get('retry', {})
        max_retries = retry_config.get('max_retries', 3)
        initial_backoff = retry_config.get('initial_backoff_seconds', 5)
        max_backoff = retry_config.get('max_backoff_seconds', 60)
        backoff_multiplier = retry_config.get('backoff_multiplier', 2.0)
        
        last_error = None
        backoff = initial_backoff
        
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Processing {table_name} (attempt {attempt + 1}/{max_retries + 1})")
                
                ingestion = TableIngestion(
                    self.spark,
                    self.config.get('connection', {}),
                    table_config,
                    self.config.get('runtime', {})
                )
                
                metrics = ingestion.ingest()
                return metrics
                
            except Exception as e:
                last_error = e
                logger.error(f"Error processing {table_name} (attempt {attempt + 1}): {str(e)}")
                
                if attempt < max_retries:
                    logger.info(f"Retrying {table_name} after {backoff} seconds...")
                    time.sleep(backoff)
                    backoff = min(backoff * backoff_multiplier, max_backoff)
                else:
                    logger.error(f"Failed to process {table_name} after {max_retries + 1} attempts")
        
        # Return failure metrics
        return {
            'table': table_name,
            'mode': table_config.get('mode', 'unknown'),
            'status': 'failed',
            'error_message': str(last_error),
            'rows_read': 0,
            'elapsed_seconds': 0
        }
    
    def _save_metrics(self, metrics: List[Dict[str, Any]]) -> None:
        """
        Save ingestion metrics to Delta table.
        
        Args:
            metrics: List of metrics dictionaries
        """
        try:
            metrics_df = self.spark.createDataFrame(metrics)
            metrics_df = metrics_df.withColumn("ingestion_run_id", lit(time.time()))
            metrics_df = metrics_df.withColumn("timestamp", current_timestamp())
            
            # Append to metrics table
            metrics_df.write.format("delta").mode("append").save(self.metrics_location)
            
            logger.info(f"Saved metrics for {len(metrics)} tables to {self.metrics_location}")
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")
    
    def _print_summary(self, metrics: List[Dict[str, Any]]) -> None:
        """Print ingestion summary."""
        total_tables = len(metrics)
        successful = sum(1 for m in metrics if m.get('status') == 'success')
        failed = total_tables - successful
        
        total_rows = sum(m.get('rows_read', 0) for m in metrics)
        total_time = sum(m.get('elapsed_seconds', 0) for m in metrics)
        avg_time = total_time / total_tables if total_tables > 0 else 0
        
        total_bytes = sum(m.get('bytes_read', 0) for m in metrics)
        total_bytes_mb = total_bytes / (1024 * 1024)
        
        print("\n" + "="*80)
        print("INGESTION SUMMARY")
        print("="*80)
        print(f"Total Tables: {total_tables}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total Rows: {total_rows:,}")
        print(f"Total Data: {total_bytes_mb:.2f} MB")
        print(f"Total Time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        print(f"Average Time per Table: {avg_time:.2f} seconds")
        print(f"Overall Throughput: {total_rows/total_time:.0f} rows/sec" if total_time > 0 else "N/A")
        print("="*80)
        
        if failed > 0:
            print("\nFAILED TABLES:")
            for m in metrics:
                if m.get('status') == 'failed':
                    print(f"  - {m.get('table')}: {m.get('error_message', 'Unknown error')}")
    
    def run(self, max_workers: Optional[int] = None) -> Dict[str, Any]:
        """
        Run ingestion pipeline for all configured tables.
        
        Args:
            max_workers: Maximum concurrent table ingestions (default: number of tables, capped at 500)
            
        Returns:
            Dictionary with overall metrics
        """
        self.start_time = time.time()
        tables = self.config.get('tables', [])
        
        if not tables:
            raise ValueError("No tables configured for ingestion")
        
        logger.info(f"Starting ingestion for {len(tables)} tables")
        
        # Calculate and log parallelism recommendations
        parallelism_info = self._calculate_required_parallelism()
        logger.info(f"Parallelism Analysis:")
        logger.info(f"  Total Tables: {parallelism_info['total_tables']}")
        logger.info(f"  Total Size: {parallelism_info['total_size_mb']:.2f} MB")
        logger.info(f"  Total Partitions: {parallelism_info['total_partitions']}")
        logger.info(f"  Current Cores: {parallelism_info['current_cores']}")
        logger.info(f"  Estimated Time: {parallelism_info['estimated_minutes']:.2f} minutes")
        logger.info(f"  Recommended Workers: {parallelism_info['recommended_workers']}")
        
        # Determine max concurrent workers
        if max_workers is None:
            max_workers = min(len(tables), 500)  # Cap at 500 concurrent
        
        # Process tables concurrently
        logger.info(f"Processing {len(tables)} tables with max {max_workers} concurrent workers")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_table = {
                executor.submit(self._ingest_single_table, table_config): table_config
                for table_config in tables
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_table):
                completed += 1
                try:
                    metrics = future.result()
                    self.all_metrics.append(metrics)
                    logger.info(f"Completed {completed}/{len(tables)}: {metrics.get('table')} "
                              f"({metrics.get('status')}, {metrics.get('rows_read', 0)} rows, "
                              f"{metrics.get('elapsed_seconds', 0):.2f}s)")
                except Exception as e:
                    logger.error(f"Unexpected error in future: {str(e)}")
                    table_config = future_to_table[future]
                    self.all_metrics.append({
                        'table': f"{table_config.get('schema')}.{table_config.get('table')}",
                        'status': 'failed',
                        'error_message': str(e),
                        'rows_read': 0,
                        'elapsed_seconds': 0
                    })
        
        self.end_time = time.time()
        overall_time = self.end_time - self.start_time
        
        # Save metrics
        self._save_metrics(self.all_metrics)
        
        # Print summary
        self._print_summary(self.all_metrics)
        
        # Return overall metrics
        return {
            'total_tables': len(tables),
            'successful': sum(1 for m in self.all_metrics if m.get('status') == 'success'),
            'failed': sum(1 for m in self.all_metrics if m.get('status') == 'failed'),
            'total_rows': sum(m.get('rows_read', 0) for m in self.all_metrics),
            'total_time_seconds': overall_time,
            'metrics': self.all_metrics
        }


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python ingest_master.py <config_path> [max_workers]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    max_workers = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        orchestrator = IngestionOrchestrator(config_path)
        results = orchestrator.run(max_workers=max_workers)
        
        # Exit with error code if any tables failed
        if results['failed'] > 0:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
