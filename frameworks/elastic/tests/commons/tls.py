from typing import Any, Dict, Iterator

import sdk_install
import sdk_service
from security import transport_encryption

from tests import config


def _service_account_impl(configure_security: None) -> Iterator[Dict[str, Any]]:
    try:
        name = config.SERVICE_NAME
        service_account_info = transport_encryption.setup_service_account(name)

        yield service_account_info
    finally:
        transport_encryption.cleanup_service_account(config.SERVICE_NAME, service_account_info)


def _elastic_service_impl(
    service_account: Dict[str, Any], configuration: Dict[str, Any] = {}
) -> Iterator[Dict[str, Any]]:
    package_name = config.PACKAGE_NAME
    service_name = config.SERVICE_NAME

    # Additional 1 data node
    expected_running_tasks = config.DEFAULT_TASK_COUNT + 1

    try:
        sdk_install.uninstall(package_name, service_name)

        sdk_install.install(
            package_name,
            service_name=service_name,
            expected_running_tasks=expected_running_tasks,
            additional_options=configuration,
            timeout_seconds=30 * 60,
            wait_for_deployment=False,
        )

        # Set up passwords. Basic HTTP credentials will have to be used in HTTP requests to
        # Elasticsearch from now on.
        passwords = config.setup_passwords(service_name, https=True)
        http_password = passwords["elastic"]

        # Set up healthcheck basic HTTP credentials.
        sdk_service.update_configuration(
            package_name,
            service_name,
            {"elasticsearch": {"health_user_password": http_password}},
            expected_running_tasks,
        )

        config.check_elasticsearch_index_health(
            ".security-7",
            "green",
            service_name=service_name,
            http_password=http_password,
            https=True,
        )

        yield {**configuration, **{"package_name": package_name, "passwords": passwords}}
    finally:
        sdk_install.uninstall(package_name, service_name)


def _kibana_application_impl(
    elastic_service: Dict[str, Any], configuration: Dict[str, Any] = {}
) -> Iterator[Dict[str, Any]]:
    package_name = config.KIBANA_PACKAGE_NAME
    service_name = config.KIBANA_SERVICE_NAME

    try:
        sdk_install.uninstall(package_name, service_name)

        sdk_install.install(
            package_name,
            service_name=service_name,
            expected_running_tasks=0,
            additional_options=configuration,
            timeout_seconds=config.KIBANA_DEFAULT_TIMEOUT,
            wait_for_deployment=False,
        )

        yield {**configuration, **{"package_name": package_name, "elastic": elastic_service}}
    finally:
        sdk_install.uninstall(package_name, service_name)
