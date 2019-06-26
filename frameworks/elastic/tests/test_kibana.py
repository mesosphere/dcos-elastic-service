import pytest
import sdk_cmd
import sdk_hosts
import sdk_install
import base64

from tests import config


@pytest.mark.sanity
def test_config_with_custom_yml() -> None:
    try:
        _uninstall_services()

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

        config.check_kibana_adminrouter_integration(
            "service/{}/".format(config.KIBANA_SERVICE_NAME)
        )
    finally:
        _uninstall_services()


def _uninstall_services() -> None:
    sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
    sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_SERVICE_NAME)
