import pytest
import retrying
import os
from typing import Iterator
import sdk_install
import sdk_cmd
import sdk_tasks
from tests import config
import re

@pytest.fixture(scope="module", autouse=True)
def configure_package(configure_security: None) -> Iterator[None]:
    try:
        service_options={"elasticsearch": {"plugins": "repository-s3"}}
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)
        sdk_install.install(
            config.PACKAGE_NAME,
            config.SERVICE_NAME,
            config.DEFAULT_TASK_COUNT,
            additional_options=service_options,
        )

        yield  # let the test session execute
    finally:
        sdk_install.uninstall(config.PACKAGE_NAME, config.SERVICE_NAME)


@pytest.fixture(autouse=True)
def pre_test_setup() -> None:
    sdk_tasks.check_running(config.SERVICE_NAME, config.DEFAULT_TASK_COUNT)
    config.wait_for_expected_nodes_to_exist(task_count=config.DEFAULT_TASK_COUNT)

@pytest.mark.aws
@pytest.mark.sanity
def test_backup_restore():
    key_id = os.getenv("AWS_ACCESS_KEY_ID")
    if not key_id:
        assert (
            False
        ), 'AWS credentials are required for this test. Disable test with e.g. TEST_TYPES="sanity and not aws"'
    master_0_node_id=sdk_tasks.get_task_ids(config.SERVICE_NAME, "master-0-node")
    task_list=sdk_tasks.get_task_ids(config.SERVICE_NAME)
    for id in task_list:
        sdk_cmd.run_cli("task exec {} bash -c \"export JAVA_HOME=\$(ls -d \$MESOS_SANDBOX/jdk*/);  echo '{}' | ./elasticsearch-*/bin/elasticsearch-keystore add --stdin s3.client.default.access_key\"".format(id, os.getenv("AWS_ACCESS_KEY_ID")))
        sdk_cmd.run_cli("task exec {} bash -c \"export JAVA_HOME=\$(ls -d \$MESOS_SANDBOX/jdk*/);  echo '{}' | ./elasticsearch-*/bin/elasticsearch-keystore add --stdin s3.client.default.secret_key\"".format(id, os.getenv("AWS_SECRET_ACCESS_KEY")))
        sdk_cmd.run_cli("task exec {} bash -c \"export JAVA_HOME=\$(ls -d \$MESOS_SANDBOX/jdk*/);  echo '{}' | ./elasticsearch-*/bin/elasticsearch-keystore add --stdin s3.client.default.session_token\"".format(id, os.getenv("AWS_SESSION_TOKEN")))
        sdk_cmd.run_cli("task exec {} bash -c \"export JAVA_HOME=\$(ls -d \$MESOS_SANDBOX/jdk*/); ./elasticsearch-*/bin/elasticsearch-keystore list\"".format(id))

    sdk_cmd.run_cli("task exec {} /opt/mesosphere/bin/curl -i -XPOST -H 'Content-type: application/json' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/_nodes/reload_secure_settings\"".format(master_0_node_id[0]))
    sdk_cmd.run_cli("task exec "+master_0_node_id[0]+"  /opt/mesosphere/bin/curl -i -XPOST -H 'Content-type: application/json' -d '{\"name\": \"Niharika\"}' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/customer/entry/99?pretty\"")
    sdk_cmd.run_cli("task exec "+master_0_node_id[0]+" /opt/mesosphere/bin/curl -i -XPUT -H 'Content-type: application/json' -d '{\"type\": \"s3\", \"settings\": {\"bucket\": \"elastic-bkp-bucket\", \"region\": \"us-east-1\"} }' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/_snapshot/s3_repo?verify=false&pretty\"")

    # take backup
    sdk_cmd.run_cli("task exec {} /opt/mesosphere/bin/curl -i -XPUT -H 'Content-type: application/json' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/_snapshot/s3_repo/snap1?\"".format(master_0_node_id[0]))

    # Delete data before executing restore
    sdk_cmd.run_cli("task exec {} /opt/mesosphere/bin/curl -i -XDELETE -H 'Content-type: application/json' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/*\"".format(master_0_node_id[0]))

    # restore data
    sdk_cmd.run_cli("task exec {} /opt/mesosphere/bin/curl -i -XPOST -H 'Content-type: application/json' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/_snapshot/s3_repo/snap1/_restore\"".format(master_0_node_id[0]))
    
    _, output, _=sdk_cmd.run_cli("task exec {} /opt/mesosphere/bin/curl -i -u elastic:changeme -H 'Content-type: application/json' \"http://coordinator.elastic.l4lb.thisdcos.directory:9200/customer/entry/99?pretty\"".format(master_0_node_id[0]))

    assert '"name" : "Niharika"' in output
