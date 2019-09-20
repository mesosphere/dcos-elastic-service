import logging
from typing import Iterator

import pytest

import sdk_install
import sdk_utils
from tests import config

log = logging.getLogger(__name__)

foldered_name = sdk_utils.get_foldered_name(config.SERVICE_NAME)


@pytest.fixture(scope="module", autouse=True)
def set_up_security(configure_security: None) -> Iterator[None]:
    yield


@pytest.fixture(autouse=True)
def uninstall_packages(configure_security: None) -> Iterator[None]:
    try:
        log.info("Ensuring Elastic and Kibana are uninstalled before running test")
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_PACKAGE_NAME)
        sdk_install.uninstall(config.PACKAGE_NAME, foldered_name)

        yield  # let the test session execute
    finally:
        log.info("Ensuring Elastic and Kibana are uninstalled after running test")
        sdk_install.uninstall(config.KIBANA_PACKAGE_NAME, config.KIBANA_PACKAGE_NAME)
        sdk_install.uninstall(config.PACKAGE_NAME, foldered_name)


# TODO(mpereira): Re-enable this test after we release Elasticsearch 6.6.2+.
@pytest.mark.sanity
@pytest.mark.timeout(30 * 60)
@pytest.mark.skip(
    reason="DCOS-51376: Bug in Elasticsearch only fixed on 6.6.2+ causes this test to be flaky"
)
def test_xpack_security_enabled_update_matrix() -> None:
    log.info("Updating X-Pack Security from 'enabled' to 'enabled'")
    config.test_xpack_security_enabled_update(foldered_name, True, True)

    log.info("Updating X-Pack Security from 'enabled' to 'disabled'")
    config.test_xpack_security_enabled_update(foldered_name, True, False)

    log.info("Updating X-Pack Security from 'disabled' to 'enabled'")
    config.test_xpack_security_enabled_update(foldered_name, False, True)

    log.info("Updating X-Pack Security from 'disabled' to 'disabled'")
    config.test_xpack_security_enabled_update(foldered_name, False, False)
