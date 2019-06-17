# DC/OS Elastic service

This is the source repository for the [DC/OS
Elastic](https://mesosphere.com/service-catalog/elastic) package.

Official documentation can be found in the [service docs
page](https://docs.mesosphere.com/services/elastic/).

## Integration Test Builds Matrix

|                | DC/OS 1.11 | DC/OS 1.12 | DC/OS 1.13 | DC/OS Master |
| -------------- | ---------- | ---------- | ---------- | ------------ |
| **Open**       | (not tested) | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Open)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Open)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Open)/statusIcon"/></a> |
| **Permissive** | (not tested) | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Permissive)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Permissive)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Permissive)/statusIcon"/></a> |
| **Strict**     | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_111_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_111_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Strict)/statusIcon"/></a> |

## Getting Started

## Development

All commands assume that you're in the project root directory.

```bash
cd /path/to/dcos-elastic-service
```

### Running static code analyzers

#### Python

```bash
dcos-commons/tools/ci/steps/check_python_files.sh
```

### Running automatic code formatters

#### Python

```bash
DOCKER_COMMAND='black frameworks' dcos-commons/run_container.sh --project $(pwd)
```

### Building package

First make sure you have a valid AWS session configured either in the form of:
- `~/.aws/credentials` file and exported `AWS_PROFILE` environment variable

or

- exported `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables

If you work for Mesosphere, check out
[maws](https://github.com/mesosphere/maws).

The following command should be run from your host. It will run a Docker
container and build the package there:

```bash
DOCKER_COMMAND="frameworks/elastic/build.sh aws" dcos-commons/run_container.sh --project $(pwd)
```

You could also have the package be built in the host machine, but that's not
recommended:

```bash
frameworks/elastic/build.sh aws
```

### Running tests

First make sure you have a DC/OS cluster where your tests can be run on.

```bash
export CLUSTER_URL="http://your-dcos-cluster.com"
```

Optionally, export a stub Universe URL so that tests run against a particular
stub version of the service.

```bash
export STUB_UNIVERSE_URL='https://universe-converter.mesosphere.com/transform?url=...'
```

#### All tests

The following command should be run from your host. It will run a Docker
container and run all tests from there:

```bash
dcos-commons/test.sh elastic --project $(pwd)
```

#### Single test module

As before, the following command should be run from your host. It will run a
Docker container and run the specific test module from there.

```bash
export PYTEST_ARGS='frameworks/elastic/tests/test_sanity.py'
```

```bash
dcos-commons/test.sh elastic --project $(pwd)
```

#### Single test

As before, the following command should be run from your host. It will run a
Docker container and run the specific test module from there.

In the example below, the `-k` flag will match tests in all test modules for
tests named `test_endpoints`. If you wish to only match tests in a single test
module you'll need to set `PYTEST_ARGS` similar to the example above.

```bash
dcos-commons/test.sh elastic --project $(pwd) -k test_endpoints
```
