
from typing import Any, Dict, Iterator

import pytest
import sdk_cmd
import sdk_install
import sdk_hosts
import sdk_security
import sdk_utils

from tests import config
from security import transport_encryption

sg_internal_users_secret_name="sg_internal_users"

def _uninstall_services() -> None:
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)

@pytest.fixture
def sg_internal_users_path(tmp_path) -> str:
    path = tmp_path / "sg_internal_users.yml"
    sg_internal_users_config = (
        'admin.readonly: true\n'
        'admin.hash: "$2y$12$Pd3kIQD1WgaKpekPyMkUi.jmBDF3QDmPIEUg37wXCRufZZQOnYYYW"\n' # password: admin_password
        'admin.roles: [ admin ]\n'
        
        'kibanaserver.readonly: true\n'
        'kibanaserver.hash: "$2y$12$lrwJYnjrlTGgOcf7Kd6xXOHIbkqFWBO3qgqyLYlEwIuRM3CfgL5fG"\n' # password: kibanaserver_password

        'kibanaro.hash: "$2y$12$gaYwLqeOWzvWXuvf5OnpFe3kqsqKggxHiiMp/JG9hq2nnuxTFtcN."\n' # password: kibanaro_password
        'kibanaro.roles: [kibanauser, readall]\n')

    path.write_text(sg_internal_users_config)
    return path.resolve()

@pytest.fixture(scope="module")
def service_account(configure_security: None) -> Iterator[Dict[str, Any]]:
    service_account_info = transport_encryption.setup_service_account(config.SERVICE_NAME)
    try:

        yield service_account_info
    finally:
        transport_encryption.cleanup_service_account(config.SERVICE_NAME, service_account_info)

@pytest.mark.sanity
def test_searchguard_support_elastic(service_account: Dict[str, Any], sg_internal_users_path: str):
    try:
        _uninstall_services()
        sdk_cmd.run_cli('security secrets create -f {} {}'.format(str(sg_internal_users_path), sg_internal_users_secret_name))

        sdk_install.install(
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
                "sgadmin_nodes" : {"count" : 1},
                "elasticsearch": {"searchguard_enabled": True, "health_user": "admin", "health_user_password": "admin_password", "searchguard_internal_users" : sg_internal_users_secret_name},
            },
        )

        curl_cmd = 'curl -L -i -k -s {}/_searchguard/health'.format("https://" + sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200))
        rc, stdout, stderr = sdk_cmd.service_task_exec(config.SERVICE_NAME, "master-0-node", curl_cmd)
        assert bool(rc == 0 and stdout and "HTTP/1.1 200" in stdout and '"status":"UP"' in stdout)

    finally:
        _uninstall_services()
        sdk_security.delete_secret(sg_internal_users_secret_name)


@pytest.mark.sanity
def test_searchguard_support_kibana(service_account: Dict[str, Any], sg_internal_users_path: str):
    try:
        _uninstall_services()
        sdk_cmd.run_cli('security secrets create -f {} {}'.format(str(sg_internal_users_path), sg_internal_users_secret_name))

        sdk_install.install(
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
                "sgadmin_nodes" : {"count" : 1},
                "elasticsearch": {"searchguard_enabled": True, "health_user": "admin", "health_user_password": "admin_password", "searchguard_internal_users" : sg_internal_users_secret_name},
            },
        )

        elasticsearch_url = "https://" + sdk_hosts.vip_host(config.SERVICE_NAME, "coordinator", 9200)

        sdk_install.install(
            config.KIBANA_PACKAGE_NAME,
            config.KIBANA_SERVICE_NAME,
            0,
            {
              "kibana": {"elasticsearch_url": elasticsearch_url, "elasticsearch_tls": True, "searchguard_enabled": True, "user": "kibanaserver", "password": "kibanaserver_password"},
            },
            wait_for_deployment=False,
            insert_strict_options=False,
        )

        curl_cmd = 'curl -L -i -k -u kibanaserver:kibanaserver_password -s {}/{}'.format(
            sdk_utils.dcos_url().rstrip("/"), "service/{}/{}".format(config.KIBANA_PACKAGE_NAME, "api/saved_objects/_find?type=index-pattern").lstrip("/")
        )
        rc, stdout, _ = sdk_cmd.master_ssh(curl_cmd)
        assert bool(rc == 0 and stdout and "HTTP/1.1 200" in stdout and '"status":"UP"' in stdout)

    finally:
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
        _uninstall_services()
        sdk_security.delete_secret(sg_internal_users_secret_name)