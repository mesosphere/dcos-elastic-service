# DC/OS Elastic service

This is the source repository for the [DC/OS
Elastic](https://mesosphere.com/service-catalog/elastic) package.

Official documentation can be found in the [service docs
page](https://docs.mesosphere.com/services/elastic/).

## Nightly integration test builds matrix

|                | DC/OS 1.11 | DC/OS 1.12 | DC/OS 1.13 | DC/OS Master |
| -------------- | ---------- | ---------- | ---------- | ------------ |
| **Open**       | (not tested) | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Open)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Open)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Open&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Open)/statusIcon"/></a> |
| **Permissive** | (not tested) | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Permissive)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Permissive)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Permissive&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Permissive)/statusIcon"/></a> |
| **Strict**     | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_111_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_111_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_112_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_112_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_113_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_113_Strict)/statusIcon"/></a> | <a href="https://teamcity.mesosphere.io/viewType.html?buildTypeId=DataServices_Elastic_IntegrationTests_DCOS_master_Strict&guest=1"><img src="https://teamcity.mesosphere.io/app/rest/builds/buildType:(id:DataServices_Elastic_IntegrationTests_DCOS_master_Strict)/statusIcon"/></a> |

## Development

The dcos-commons git submodule is set up via
[SSH](https://help.github.com/en/articles/connecting-to-github-with-ssh). Please
make sure you have that configured.

Also make sure your Docker daemon is [running under a non-root
user](https://docs.docker.com/install/linux/linux-postinstall/).

### Cloning the repository

```bash
git clone --recurse-submodules git@github.com:mesosphere/dcos-elastic-service.git /path/to/dcos-elastic-service
```

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
DOCKER_COMMAND='black frameworks' dcos-commons/run_container.sh elastic --project $(pwd)
```

#### config.json

```bash
DOCKER_COMMAND='
  ./tools/standardize_config_json.py
     --service-config-json frameworks/elastic/universe/config.json
     --sdk-tools-config frameworks/elastic/sdk-tools.json
' dcos-commons/run_container.sh elastic --project $(pwd)
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
DOCKER_COMMAND="frameworks/elastic/build.sh aws" dcos-commons/run_container.sh elastic --project $(pwd)
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

### Style guide

#### Opening pull requests

PR titles should be in imperative mood, useful, concise and follow the following
format:

```
[DCOS-xxxxx] Add support for new thing.
```

In the example above a JIRA ticket is referenced with the `[DCOS-xxxxx]` tag. If
for some reason the PR isn't related to a ticket, feel free to use "free-form"
tags, ideally ones that were already used like `[DOCS]`, `[SDK]`, `[MISC]`,
`[TOOLS]` or even `[SDK][TOOLS]` for increased specificity.

PR descriptions should include additional context regarding what is achieved
with the PR, why is it needed, rationale regarding decisions that were made,
possibly with pointers to actual commits.

Example:
```
To make it possible for the new thing we had to:
- Prepare this other thing (5417f75)
- Clean up something else (ec4c78d)

This was required because of this and that.

Example output of thing:

    {
      "a": 2
    }


Please look into http://www.somewebsite.com/details-about-thing
for more context.
```

#### Merging pull requests

When all checks are green, a PR should be merged as a squash-commit, with its
message being the PR title followed by the PR number. Example:

```
[DCOS-xxxxx] Add support for new thing. (#42)
```

The description for the squash-commit will ideally be the PR description
verbatim. If the PR description was empty (it probably shouldn't have been!) the
squash-commit description will by default be a list of all the commits in the
PR's branch. That list should be cleaned up to only contain useful entries (no
`fix`, `formatting`, `changed foo`, `refactored bar`), or rewritten so that
additional context is added to the commit, like in the example above for PR
descriptions.
