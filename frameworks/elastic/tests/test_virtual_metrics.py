from typing import Any, Dict, Iterator, List, Set

import pytest
import sdk_install
import sdk_metrics
import retrying

from tests import config


@pytest.fixture(scope="module", autouse=True)
def configure_package(configure_security: None) -> Iterator[None]:
    try:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_install.install(
            config.PACKAGE_NAME,
            config.SERVICE_NAME,
            config.DEFAULT_TASK_COUNT,
            additional_options={"service": {"virtual_network_enabled": True}},
        )

        yield  # let the test session execute
    finally:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


@pytest.mark.sanity
@pytest.mark.dcos_min_version("1.13")
@retrying.retry(
    stop_max_attempt_number=10,
    wait_fixed=1000,
    retry_on_exception=lambda e: isinstance(e, Exception),
)
def test_metrics() -> None:
    metrics = sdk_metrics.wait_for_metrics_from_cli("exporter-0-node", 60)

    elastic_metrics = list(non_zero_elastic_metrics(metrics))
    assert len(elastic_metrics) > 0

    node_types = ["master", "data", "coordinator"]
    node_names = get_node_names_from_metrics(elastic_metrics)
    for node_type in node_types:
        assert len(list(filter(lambda x: x.startswith(node_type), node_names))) > 0


def non_zero_elastic_metrics(metrics: List[Dict[Any, Any]]):
    for metric in metrics:
        if metric["name"].startswith("elasticsearch") and metric["value"] != 0:
            yield metric


def get_node_names_from_metrics(metrics: List[Dict[Any, Any]]) -> Set[str]:
    names = set()
    for metric in metrics:
        if "name" in metric["tags"]:
            names.add(metric["tags"]["name"])
    return names
