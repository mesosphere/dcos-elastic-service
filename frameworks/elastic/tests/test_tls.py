import json
from typing import Any, Dict, Iterator

import pytest
import sdk_cmd
import sdk_hosts
import sdk_recovery
import sdk_utils
from toolz import get_in

from tests import config
from tests.commons import tls

pytestmark = [
    sdk_utils.dcos_ee_only,
    pytest.mark.skipif(
        sdk_utils.dcos_version_less_than("1.10"), reason="TLS tests require DC/OS 1.10+"
    ),
]


@pytest.fixture(scope="module")
def service_account(configure_security: None) -> Iterator[Dict[str, Any]]:
    """
    Sets up a service account for use with TLS.
    """
    yield from tls._service_account_impl(configure_security)


@pytest.fixture(scope="module")
def elastic_service(service_account: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    # create secret before installing elastic with security enabled
    config.install_security_secrets()
    yield from tls._elastic_service_impl(
        service_account,
        {
            "service": {
                "name": config.SERVICE_NAME,
                "service_account": service_account["name"],
                "service_account_secret": service_account["secret"],
                "security": {"transport_encryption": {"enabled": True}},
            },
            "elasticsearch": {
                "health_user_password": "elastic/healthUserPassword",
                "xpack_security_enabled": True,
            },
        },
    )


@pytest.fixture(scope="module")
def kibana_application(elastic_service: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    yield from tls._kibana_application_impl(
        elastic_service,
        {
            "service": {"name": config.KIBANA_SERVICE_NAME},
            "kibana": {
                "elasticsearch_tls": True,
                "elasticsearch_url": "https://"
                + sdk_hosts.vip_host(
                    elastic_service["service"]["name"], "coordinator", 9200
                ),
                "elasticsearch_xpack_security_enabled": True,
                "password": elastic_service["passwords"]["kibana"],
            },
        },
    )


@pytest.mark.tls
@pytest.mark.sanity
def test_crud_over_tls(elastic_service: Dict[str, Any]) -> None:
    service_name = elastic_service["service"]["name"]
    http_password = elastic_service["passwords"]["elastic"]
    index_name = config.DEFAULT_INDEX_NAME
    index_type = config.DEFAULT_INDEX_TYPE
    index = config.DEFAULT_SETTINGS_MAPPINGS
    document_fields = {"name": "Loren", "role": "developer"}
    document_id = 1

    config.create_index(
        index_name,
        index,
        service_name=service_name,
        https=True,
        http_password=http_password,
    )

    config.create_document(
        index_name,
        index_type,
        document_id,
        document_fields,
        service_name=service_name,
        https=True,
        http_password=http_password,
    )

    document = config.get_document(
        index_name, index_type, document_id, https=True, http_password=http_password
    )

    assert get_in(["_source", "name"], document) == document_fields["name"]


@pytest.mark.tls
@pytest.mark.sanity
@pytest.mark.skipif(
    sdk_utils.dcos_version_less_than("1.12"),
    reason="Kibana service URL won't work on DC/OS 1.11",
)
def test_kibana_tls(kibana_application: Dict[str, Any]) -> None:
    service_name = kibana_application["service"]["name"]
    config.check_kibana_adminrouter_integration("service/{}/".format(service_name))
    config.check_kibana_adminrouter_integration("service/{}/login".format(service_name))


@pytest.mark.tls
@pytest.mark.sanity
@pytest.mark.recovery
def test_tls_recovery(
    elastic_service: Dict[str, Any], service_account: Dict[str, Any]
) -> None:
    service_name = elastic_service["service"]["name"]
    package_name = elastic_service["package_name"]

    rc, stdout, _ = sdk_cmd.svc_cli(package_name, service_name, "pod list")

    assert rc == 0, "Pod list failed"

    for pod in json.loads(stdout):
        sdk_recovery.check_permanent_recovery(
            package_name, service_name, pod, recovery_timeout_s=60 * 60
        )
