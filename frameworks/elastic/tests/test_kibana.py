import base64
from typing import Any, Dict, Iterator

import pytest
import sdk_cmd
import sdk_hosts
import sdk_install
import sdk_marathon
import sdk_networks
import sdk_service
from security import transport_encryption
import sdk_utils

from tests import config
from tests.commons import tls

kibana_virtual_network_plugin_labels = {"c": "d", "a": "b", "network_name": "dcos"}
pytestmark = [
    pytest.mark.skipif(
        sdk_utils.dcos_version_less_than("1.12"),
        reason="Kibana service URL won't work on DC/OS 1.11",
    )
]


@pytest.fixture
def configure_package(configure_security):
    try:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)

        yield
    finally:
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


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


@pytest.mark.incremental
@pytest.mark.sanity
@pytest.mark.timeout(60 * 60)
@sdk_utils.dcos_ee_only
@pytest.mark.skipif(
    sdk_utils.dcos_version_less_than("1.12"), reason="Kibana service URL won't work on DC/OS 1.11"
)
def test_security_toggle_with_kibana() -> None:
    try:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
        service_account_info = transport_encryption.setup_service_account(config.SERVICE_NAME)

        sdk_install.install(
            config.PACKAGE_NAME,
            service_name=config.SERVICE_NAME,
            expected_running_tasks=config.DEFAULT_TASK_COUNT,
            additional_options={
                "service": {
                    "name": config.SERVICE_NAME,
                    "service_account": service_account_info["name"],
                    "service_account_secret": service_account_info["secret"],
                }
            },
            timeout_seconds=30 * 60,
            wait_for_deployment=True,
        )

        # Write some data with security disabled, enabled security, and afterwards verify that we can
        # still read what we wrote.
        document_security_disabled_id = 1
        document_security_disabled_fields = {"name": "Elasticsearch", "role": "search engine"}
        config.create_document(
            config.DEFAULT_INDEX_NAME,
            config.DEFAULT_INDEX_TYPE,
            document_security_disabled_id,
            document_security_disabled_fields,
            service_name=config.SERVICE_NAME,
        )

        # Install Kibana.
        coordinator_host = sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200)
        sdk_install.install(
            config.KIBANA_PACKAGE_NAME,
            config.KIBANA_SERVICE_NAME,
            0,
            {"kibana": {"elasticsearch_url": "http://" + coordinator_host}},
            timeout_seconds=config.KIBANA_DEFAULT_TIMEOUT,
            wait_for_deployment=False,
            insert_strict_options=False,
        )

        # Verify that it works.
        config.check_kibana_adminrouter_integration(
            "service/{}/".format(config.KIBANA_PACKAGE_NAME)
        )
        config.check_kibana_adminrouter_integration(
            "service/{}/app/kibana".format(config.KIBANA_PACKAGE_NAME)
        )

        # Uninstall it.
        sdk_install.uninstall(config.KIBANA_SERVICE_NAME, config.KIBANA_PACKAGE_NAME)

        # Enable Elasticsearch security.
        sdk_service.update_configuration(
            config.PACKAGE_NAME,
            config.SERVICE_NAME,
            {
                "elasticsearch": {"xpack_security_enabled": True},
                "service": {
                    "update_strategy": "parallel",
                    "security": {"transport_encryption": {"enabled": True}},
                },
            },
            config.DEFAULT_TASK_COUNT,
            wait_for_deployment=False,
        )

        # Set up passwords. Basic HTTP credentials will have to be used in HTTP requests to
        # Elasticsearch from now on.
        passwords = config.setup_passwords(config.SERVICE_NAME, https=True)

        # Write some data with security enabled, disable security, and afterwards verify that we can
        # still read what we wrote.
        document_security_enabled_id = 2
        document_security_enabled_fields = {"name": "X-Pack", "role": "commercial plugin"}
        config.create_document(
            config.DEFAULT_INDEX_NAME,
            config.DEFAULT_INDEX_TYPE,
            document_security_enabled_id,
            document_security_enabled_fields,
            service_name=config.SERVICE_NAME,
            https=True,
            http_user=config.DEFAULT_ELASTICSEARCH_USER,
            http_password=passwords["elastic"],
        )

        # Install Kibana with security enabled.
        sdk_install.install(
            config.KIBANA_SERVICE_NAME,
            config.KIBANA_PACKAGE_NAME,
            0,
            {
                "service": {"name": config.KIBANA_SERVICE_NAME},
                "kibana": {
                    "elasticsearch_tls": True,
                    "elasticsearch_url": "https://" + coordinator_host,
                    "elasticsearch_xpack_security_enabled": True,
                    "user": config.DEFAULT_KIBANA_USER,
                    "password": passwords["kibana"],
                },
            },
            timeout_seconds=config.KIBANA_DEFAULT_TIMEOUT,
            wait_for_deployment=False,
            insert_strict_options=False,
        )

        # Verify that it works.
        config.check_kibana_adminrouter_integration(
            "service/{}/".format(config.KIBANA_PACKAGE_NAME)
        )
        config.check_kibana_adminrouter_integration(
            "service/{}/login".format(config.KIBANA_PACKAGE_NAME)
        )

        # Uninstall it.
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)

        # Disable Elastic security.
        sdk_service.update_configuration(
            config.PACKAGE_NAME,
            config.SERVICE_NAME,
            {
                "elasticsearch": {"xpack_security_enabled": False},
                "service": {
                    "update_strategy": "parallel",
                    "security": {"transport_encryption": {"enabled": False}},
                },
            },
            config.DEFAULT_TASK_COUNT,
            wait_for_deployment=True,
        )

        # Verify we can read what was written before toggling security, without basic HTTP credentials.
        document_security_disabled = config.get_document(
            config.DEFAULT_INDEX_NAME,
            config.DEFAULT_INDEX_TYPE,
            document_security_disabled_id,
            service_name=config.SERVICE_NAME,
        )
        assert (
            document_security_disabled["_source"]["name"]
            == document_security_disabled_fields["name"]
        )

        # Verify we can read what was written when security was enabled, without basic HTTP credentials.
        document_security_enabled = config.get_document(
            config.DEFAULT_INDEX_NAME,
            config.DEFAULT_INDEX_TYPE,
            document_security_enabled_id,
            service_name=config.SERVICE_NAME,
        )
        assert (
            document_security_enabled["_source"]["name"] == document_security_enabled_fields["name"]
        )
    finally:
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        transport_encryption.cleanup_service_account(config.SERVICE_NAME, service_account_info)


def _check_cni_working(expected_labels: Dict[str, str]) -> None:
    config.check_kibana_adminrouter_integration("service/{}/".format(config.KIBANA_SERVICE_NAME))
    kibana_config = sdk_marathon.get_config(config.KIBANA_SERVICE_NAME)
    actual_labels = kibana_config["networks"][0]["labels"]

    assert expected_labels == actual_labels


def _labels_to_config(labels: Dict[str, str]) -> None:
    return [{"key": k, "value": v} for (k, v) in labels.items() if k != "network_name"]
