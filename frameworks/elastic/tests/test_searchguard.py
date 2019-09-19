from typing import Any, Dict, Iterator

import pytest
import sdk_cmd
import sdk_install
import sdk_hosts
import sdk_security
import sdk_utils

from tests import config
from tests.commons import tls

sg_internal_users_secret_name = "sg_internal_users"

pytestmark = [
    sdk_utils.dcos_ee_only,
    pytest.mark.skipif(
        sdk_utils.dcos_version_less_than("1.10"), reason="TLS tests require DC/OS 1.10+"
    ),
]


@pytest.fixture
def sg_internal_users_path(tmp_path) -> str:
    path = tmp_path / "sg_internal_users.yml"
    sg_internal_users_config = (
        # password: admin_password
        "admin.readonly: true\n"
        'admin.hash: "$2y$12$Pd3kIQD1WgaKpekPyMkUi.jmBDF3QDmPIEUg37wXCRufZZQOnYYYW"\n'
        "admin.roles: [ admin ]\n"
        # password: kibanaserver_password
        "kibanaserver.readonly: true\n"
        'kibanaserver.hash: "$2y$12$lrwJYnjrlTGgOcf7Kd6xXOHIbkqFWBO3qgqyLYlEwIuRM3CfgL5fG"\n'
    )

    path.write_text(sg_internal_users_config)
    return path.resolve()


@pytest.fixture(scope="module")
def service_account(configure_security: None) -> Iterator[Dict[str, Any]]:
    yield from tls._service_account_impl(configure_security)


@pytest.fixture
def elastic_service(service_account: Dict[str, Any], sg_internal_users_path: str):
    try:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_cmd.run_cli(
            "security secrets create -f {} {}".format(
                str(sg_internal_users_path), sg_internal_users_secret_name
            )
        )

        yield sdk_install.install(
            config.PACKAGE_NAME,
            service_name=config.SERVICE_NAME,
            expected_running_tasks=config.DEFAULT_TASK_COUNT,
            additional_options={
                "service": {
                    "name": config.SERVICE_NAME,
                    "service_account": service_account["name"],
                    "service_account_secret": service_account["secret"],
                    "security": {"transport_encryption": {"enabled": True}},
                },
                "elasticsearch": {
                    "health_user": "admin",
                    "health_user_password": "admin_password",
                    "searchguard": {
                        "enabled": True,
                        "internal_users": sg_internal_users_secret_name,
                    },
                },
            },
        )
    finally:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_security.delete_secret(sg_internal_users_secret_name)


@pytest.mark.sanity
def test_searchguard_support_elastic(elastic_service):
    curl_cmd = "curl -L -i -k -s {}/_searchguard/health".format(
        "https://" + sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200)
    )
    rc, stdout, stderr = sdk_cmd.service_task_exec(config.SERVICE_NAME, "master-0-node", curl_cmd)
    assert bool(rc == 0 and stdout and "HTTP/1.1 200" in stdout and '"status":"UP"' in stdout)


@pytest.mark.sanity
@pytest.mark.skipif(
    sdk_utils.dcos_version_less_than("1.12"), reason="Kibana service URL won't work on DC/OS 1.11"
)
def test_searchguard_support_kibana(elastic_service):
    try:
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)

        elasticsearch_url = "https://" + sdk_hosts.vip_host(
            config.SERVICE_NAME, "coordinator", 9200
        )

        sdk_install.install(
            config.KIBANA_PACKAGE_NAME,
            config.KIBANA_SERVICE_NAME,
            0,
            {
                "kibana": {
                    "elasticsearch_url": elasticsearch_url,
                    "elasticsearch_tls": True,
                    "searchguard_enabled": True,
                    "user": "kibanaserver",
                    "password": "kibanaserver_password",
                }
            },
            wait_for_deployment=False,
            insert_strict_options=False,
        )

        assert config.check_kibana_adminrouter_integration(
            "service/{}/".format(config.KIBANA_PACKAGE_NAME)
        )
        assert config.check_kibana_adminrouter_integration(
            "service/{}/login".format(config.KIBANA_PACKAGE_NAME)
        )

    finally:
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
