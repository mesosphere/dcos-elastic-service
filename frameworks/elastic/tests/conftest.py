from typing import Iterator

import os
import pytest
import sdk_security
import sdk_external_volumes
from tests import config


@pytest.fixture(scope="session")
def configure_security(configure_universe: None) -> Iterator[None]:
    yield from sdk_security.security_session(config.SERVICE_NAME)


def pytest_runtest_makereport(item, call):
    """
    This pytest fixture in connection with `pytest_runtest_setup` add support
    for indicating that a set of tests are "incremental".
    When using @pytest.mark.incremental, tests following a failed test will not
    run but is marked as failed immediately.
    """
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    """
    This pytest fixture in connection with `pytest_runtest_makereport` add support
    for indicating that a set of tests are "incremental".
    When using @pytest.mark.incremental, tests following a failed test will not
    run but is marked as failed immediately.
    """
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" % previousfailed.name)


@pytest.fixture(scope="session")
def configure_external_volumes():
    if is_env_var_set("ENABLE_EXTERNAL_VOLUMES", default=str(False)):
        yield from sdk_external_volumes.external_volumes_session()
    else:
        yield

def is_env_var_set(key: str, default: str) -> bool:
    return str(os.environ.get(key, default)).lower() in ["true", "1"]