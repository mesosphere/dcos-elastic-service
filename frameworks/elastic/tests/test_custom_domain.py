import logging

import pytest

import sdk_hosts
import sdk_install
import sdk_networks

from tests import config


log = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def configure_package(configure_security):
    try:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)

        yield  # let the test session execute
    finally:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


@pytest.mark.sanity
def test_custom_domain():

    TASK_COUNT_MASTER = 3
    TASK_COUNT_DATA = 2
    TASK_COUNT_COORDINATOR = 1

    custom_domain = sdk_hosts.get_crypto_id_domain()
    sdk_install.install(
        config.PACKAGE_NAME,
        config.SERVICE_NAME,
        config.DEFAULT_TASK_COUNT,
        additional_options={"service": {"security": {"custom_domain": custom_domain}}},
    )

    expected_pod_endpoints = set(
        [
            "coordinator-http",
            "coordinator-transport",
            "data-http",
            "data-transport",
            "master-http",
            "master-transport",
        ]
    )
    service_pod_endpoints = sdk_networks.get_endpoint_names(
        config.PACKAGE_NAME, config.SERVICE_NAME
    )
    assert expected_pod_endpoints == set(service_pod_endpoints)

    for endpoint in service_pod_endpoints:
        test_endpoint = sdk_networks.get_endpoint(
            config.PACKAGE_NAME, config.SERVICE_NAME, endpoint
        )
        assert set(["address", "dns", "vip"]) == set(test_endpoint.keys())
        if "coordinator" in endpoint:
            check_custom_domain_address_dns(test_endpoint, TASK_COUNT_COORDINATOR)
        elif "data" in endpoint:
            check_custom_domain_address_dns(test_endpoint, TASK_COUNT_DATA)
        elif "master" in endpoint:
            check_custom_domain_address_dns(test_endpoint, TASK_COUNT_MASTER)
        # Expect ip:port:
        for entry in test_endpoint["address"]:
            assert len(entry.split(":")) == 2
        # Expect custom domain:
        for entry in test_endpoint["dns"]:
            assert custom_domain in entry


def check_custom_domain_address_dns(endpoint, taskcount):
    assert len(endpoint["address"]) == taskcount
    assert len(endpoint["dns"]) == taskcount
