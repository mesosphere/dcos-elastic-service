#!/usr/bin/env bash

# This script creates an Elastic stub Universe from source code.

# It:
# 1. Builds SDK CLI binaries and the SDK bootstrap
# 2. Builds the scheduler (assuming all Java tests pass)
# 3. Builds and publishes the stub Universe using the aforementioned artifacts
# 4. Runs the script to build Kibana

set -euxo pipefail

PUBLISH_METHOD="${1:-none}" # "none", "local", "aws", ".dcos".
PACKAGE_VERSION="${2:-stub-universe}"

FRAMEWORK_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_NAME=$(basename "${FRAMEWORK_DIRECTORY}")
DCOS_COMMONS_DIRECTORY="$(cd "${FRAMEWORK_DIRECTORY}/../.." && pwd)"
UNIVERSE_URL_PATH="${UNIVERSE_URL_PATH:-}"

# Grab TEMPLATE_x vars for use in Universe template.
# shellcheck source=versions.sh
source "${FRAMEWORK_DIRECTORY}/versions.sh"

# Build SDK artifacts (CLIs, bootstrap.zip) that will be included in the
# resulting stub while skipping SDK tests (the "-b" flag).
"${DCOS_COMMONS_DIRECTORY}/build.sh" -b

# Build/test scheduler.zip.
"${DCOS_COMMONS_DIRECTORY}/gradlew" -p "${FRAMEWORK_DIRECTORY}" check distZip

# Build package with the SDK artifacts that were just built (SDK CLIs,
# bootstrap.zip, scheduler.zip).
"${DCOS_COMMONS_DIRECTORY}/tools/build_package.sh" \
  "${FRAMEWORK_NAME}" \
  "${FRAMEWORK_DIRECTORY}" \
  -a "${FRAMEWORK_DIRECTORY}/build/distributions/${FRAMEWORK_NAME}-scheduler.zip" \
  -a "${DCOS_COMMONS_DIRECTORY}/sdk/bootstrap/bootstrap.zip" \
  -a "${DCOS_COMMONS_DIRECTORY}/sdk/cli/dcos-service-cli-linux" \
  -a "${DCOS_COMMONS_DIRECTORY}/sdk/cli/dcos-service-cli-darwin" \
  -a "${DCOS_COMMONS_DIRECTORY}/sdk/cli/dcos-service-cli.exe" \
  "${@}"

# Build Kibana.
# UNIVERSE_URL_PATH is set in CI builds.
if [ "${UNIVERSE_URL_PATH}" ]; then
  KIBANA_URL_PATH="${UNIVERSE_URL_PATH}.kibana"
  UNIVERSE_URL_PATH="${KIBANA_URL_PATH}" \
                   "$FRAMEWORK_DIRECTORY/build-kibana.sh" "${PUBLISH_METHOD}" "${PACKAGE_VERSION}"
  cat "${KIBANA_URL_PATH}" >> "${UNIVERSE_URL_PATH}"
else
  "${FRAMEWORK_DIRECTORY}/build-kibana.sh" "${PUBLISH_METHOD}" "${PACKAGE_VERSION}"
fi
