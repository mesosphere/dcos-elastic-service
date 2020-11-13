import logging
import pytest
import re
import sdk_agents
import sdk_cmd
import sdk_install
import sdk_plan
import sdk_tasks
import sdk_utils
from typing import Iterator

from tests import config
from tests.test_data_integrity import _post_docs_with_bulk_request, _assert_indexed_docs_number

log = logging.getLogger(__name__)
service_name = sdk_utils.get_foldered_name(config.SERVICE_NAME)
DOCS_NUMBER = 100

master_external_volume = {
    "external_volume": {
        "enabled": True,
        "portworx_volume_options": "size=50",
        "volume_name": "MasterNodeVolume",
    }
}

data_external_volume = {
    "external_volume": {"enabled": True, "portworx_volume_options": "size=50", "volume_name": ""}
}

coordinator_external_volume = {
    "external_volume": {
        "enabled": True,
        "portworx_volume_options": "size=50",
        "volume_name": "CoordinatorNodeVolume",
    }
}

ingest_external_volume = {
    "external_volume": {
        "enabled": True,
        "portworx_volume_options": "size=50",
        "volume_name": "IngestNodeVolume",
    }
}

volume_options = {
    "service": {
        "replacement_failure_policy": {
            "enable_automatic_pod_replacement": True,
            "permanent_failure_timeout_secs": 60,
        }
    },
    "master_nodes": master_external_volume,
    "data_nodes": data_external_volume,
    "coordinator_nodes": coordinator_external_volume,
    "ingest_nodes": ingest_external_volume,
}


@pytest.fixture(scope="module", autouse=True)
def configure_package(configure_security: None, configure_external_volumes: None) -> Iterator[None]:
    try:
        sdk_cmd.run_cli("package install {} --yes --cli".format(config.PACKAGE_NAME))

        sdk_install.uninstall(config.PACKAGE_NAME, service_name)
        sdk_install.install(
            config.PACKAGE_NAME,
            service_name,
            config.DEFAULT_TASK_COUNT,
            additional_options=volume_options,
        )

        yield  # let the test session execute
    finally:
        sdk_install.uninstall(config.PACKAGE_NAME, service_name)


@pytest.mark.external_volumes
@pytest.mark.sanity
def test_data_integrity() -> None:
    _post_docs_with_bulk_request(DOCS_NUMBER)
    sdk_install.uninstall(config.PACKAGE_NAME, service_name)
    sdk_install.install(
        config.PACKAGE_NAME,
        service_name,
        config.DEFAULT_TASK_COUNT,
        additional_options=volume_options,
    )
    _assert_indexed_docs_number(DOCS_NUMBER)


@pytest.mark.external_volumes
@pytest.mark.sanity
def test_auto_replace_on_drain():
    candidate_tasks = sdk_tasks.get_tasks_avoiding_scheduler(
        service_name, re.compile("^(master|data|coordinator)-[0-9]+-node$")
    )

    log.info("Candidate tasks: {}".format(candidate_tasks))
    assert len(candidate_tasks) != 0, "Could not find a node to drain"

    # Pick the host of the first task from the above list
    replace_agent_id = candidate_tasks[0].agent_id
    replace_tasks = [task for task in candidate_tasks if task.agent_id == replace_agent_id]
    log.info(
        "Tasks on agent {} to be replaced after drain: {}".format(replace_agent_id, replace_tasks)
    )
    sdk_agents.drain_agent(replace_agent_id)

    sdk_plan.wait_for_kicked_off_recovery(service_name)
    sdk_plan.wait_for_completed_recovery(service_name)

    new_tasks = sdk_tasks.get_summary()

    for replaced_task in replace_tasks:
        new_task = [
            task
            for task in new_tasks
            if task.name == replaced_task.name and task.id != replaced_task.id
        ][0]
        log.info(
            "Checking affected task has moved to a new agent:\n"
            "old={}\nnew={}".format(replaced_task, new_task)
        )
        assert replaced_task.agent_id != new_task.agent_id

    # Reactivate the drained agent, otherwise uninstall plans will be halted for portworx
    sdk_agents.reactivate_agent(replace_agent_id)
