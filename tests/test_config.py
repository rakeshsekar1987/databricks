import pytest

from bronze_ingestion import constants
from bronze_ingestion.config import RuntimeConfig


def test_runtime_config_defaults():
    env = {
        "SOURCE_ID": "SRC01",
        "BRONZE_PATH": "/mnt/bronze",
    }
    cfg = RuntimeConfig.from_env(env)

    assert cfg.mode == "incremental"
    assert cfg.source_id == "SRC01"
    assert cfg.parallelism == constants.DEFAULT_PARALLELISM
    assert cfg.spark.enable_aqe is True
    assert cfg.cluster_profile == "standard"


def test_runtime_config_custom_values():
    env = {
        "MODE": "FULL",
        "SOURCE_ID": "SRC02",
        "BRONZE_PATH": "dbfs:/bronze",
        "PARALLELISM": "8",
        "CLUSTER_PROFILE": "photon",
        "SLA_MINUTES": "5",
        "EXTRA_SPARK_CONF": '{"spark.sql.shuffle.partitions":128}',
    }
    cfg = RuntimeConfig.from_env(env)

    assert cfg.mode == "full"
    assert cfg.parallelism == 8
    assert cfg.cluster_profile == "photon"
    assert cfg.sla_minutes == 5
    assert cfg.spark.extra_conf["spark.sql.shuffle.partitions"] == 128


def test_runtime_config_invalid_mode():
    env = {
        "MODE": "invalid",
        "SOURCE_ID": "SRC03",
        "BRONZE_PATH": "/tmp",
    }
    with pytest.raises(ValueError):
        RuntimeConfig.from_env(env)
