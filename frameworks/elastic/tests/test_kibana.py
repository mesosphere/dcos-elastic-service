import base64
from typing import Any, Dict, Iterator

import pytest
import sdk_cmd
import sdk_hosts
import sdk_install
import sdk_marathon
import sdk_networks
import sdk_utils

from tests import config
from tests.commons import tls

kibana_virtual_network_plugin_labels = {"c": "d", "a": "b", "network_name": "dcos"}


@pytest.fixture
def configure_package(configure_security):
    try:
        _uninstall_services()

        yield
    finally:
        _uninstall_services()


@pytest.fixture
def service_account(configure_security: None) -> Iterator[Dict[str, Any]]:
    """
    Sets up a service account for use with TLS.
    """
    yield from tls._service_account_impl(configure_security)


@pytest.fixture
def elastic_service(service_account: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    yield from tls._elastic_service_impl(
        service_account,
        {
            "service": {
                "name": config.SERVICE_NAME,
                "service_account": service_account["name"],
                "service_account_secret": service_account["secret"],
                "security": {"transport_encryption": {"enabled": True}},
                "virtual_network_enabled": True,
            },
            "elasticsearch": {"xpack_security_enabled": True},
        },
    )


@pytest.fixture
def kibana_application(elastic_service: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    yield from tls._kibana_application_impl(
        elastic_service,
        {
            "service": {
                "name": config.KIBANA_SERVICE_NAME,
                "virtual_network_enabled": True,
                "virtual_network_plugin_labels": _labels_to_config(
                    kibana_virtual_network_plugin_labels
                ),
            },
            "kibana": {
                "elasticsearch_tls": True,
                "elasticsearch_url": "https://"
                + sdk_hosts.vip_host(elastic_service["service"]["name"], "coordinator", 9200),
                "elasticsearch_xpack_security_enabled": True,
                "password": elastic_service["passwords"]["kibana"],
            },
        },
    )


@pytest.mark.sanity
def test_config_with_custom_yml(configure_package) -> None:
    sdk_install.install(
        config.PACKAGE_NAME,
        service_name=config.SERVICE_NAME,
        expected_running_tasks=config.DEFAULT_TASK_COUNT,
    )

    decoded_base_64_yml = "logging.json: true"
    base_64_yml = base64.b64encode(decoded_base_64_yml.encode("utf-8")).decode("utf-8")
    elasticsearch_url = "http://" + sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200)

    sdk_install.install(
        config.KIBANA_PACKAGE_NAME,
        config.KIBANA_SERVICE_NAME,
        0,
        {"kibana": {"elasticsearch_url": elasticsearch_url, "custom_kibana_yml": base_64_yml}},
        wait_for_deployment=False,
        insert_strict_options=False,
    )

    cmd = "bash -c 'grep \"{}\" kibana-*/config/kibana.yml'".format(decoded_base_64_yml)
    rc, stdout, stderr = sdk_cmd.marathon_task_exec(config.KIBANA_SERVICE_NAME, cmd)
    assert rc == 0 and decoded_base_64_yml in stdout

    config.check_kibana_adminrouter_integration("service/{}/".format(config.KIBANA_SERVICE_NAME))


@pytest.mark.sanity
def test_config_with_custom_placement(configure_package):
    non_default_placement = [["hostname", "CLUSTER"]]

    sdk_install.install(
        config.PACKAGE_NAME,
        service_name=config.SERVICE_NAME,
        expected_running_tasks=config.DEFAULT_TASK_COUNT,
    )

    sdk_install.install(
        config.KIBANA_PACKAGE_NAME,
        config.KIBANA_SERVICE_NAME,
        0,
        {"kibana": {"placement": non_default_placement}},
        wait_for_deployment=False,
        insert_strict_options=False,
    )

    marathon_constraints = sdk_marathon.get_config(config.KIBANA_SERVICE_NAME)["constraints"]

    assert marathon_constraints == non_default_placement
    assert config.check_kibana_adminrouter_integration(
        "service/{}/".format(config.KIBANA_SERVICE_NAME)
    )


@pytest.mark.sanity
def test_virtual_network(configure_package) -> None:
    sdk_install.install(
        config.PACKAGE_NAME,
        service_name=config.SERVICE_NAME,
        expected_running_tasks=config.DEFAULT_TASK_COUNT,
        additional_options=sdk_networks.ENABLE_VIRTUAL_NETWORKS_OPTIONS,
    )

    elasticsearch_url = "http://" + sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200)
    sdk_install.install(
        config.KIBANA_PACKAGE_NAME,
        config.KIBANA_SERVICE_NAME,
        0,
        {
            "service": {
                "virtual_network_enabled": True,
                "virtual_network_plugin_labels": _labels_to_config(
                    kibana_virtual_network_plugin_labels
                ),
            },
            "kibana": {"elasticsearch_url": elasticsearch_url},
        },
        wait_for_deployment=False,
        insert_strict_options=False,
    )

    _check_cni_working(kibana_virtual_network_plugin_labels)


@pytest.mark.tls
@pytest.mark.sanity
@sdk_utils.dcos_ee_only
@pytest.mark.skipif(
    sdk_utils.dcos_version_less_than("1.10"), reason="TLS tests require DC/OS 1.10+"
)
def test_virtual_network_tls(
    kibana_application: Dict[str, Any], elastic_service: Dict[str, Any]
) -> None:
    _check_cni_working(kibana_virtual_network_plugin_labels)


def _check_cni_working(expected_labels: Dict[str, str]) -> None:
    config.check_kibana_adminrouter_integration("service/{}/".format(config.KIBANA_SERVICE_NAME))
    kibana_config = sdk_marathon.get_config(config.KIBANA_SERVICE_NAME)
    actual_labels = kibana_config["networks"][0]["labels"]

    assert expected_labels == actual_labels


def _labels_to_config(labels: Dict[str, str]) -> None:
    return [{"key": k, "value": v} for (k, v) in labels.items() if k != "network_name"]


def _uninstall_services() -> None:
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
    sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
