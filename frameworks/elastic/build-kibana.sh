#!/usr/bin/env bash

# This is a separate build script for Kibana. It creates a stub Universe for the
# Kibana package and optionally publishes it to S3 or a local artifact server.

set -euxo pipefail

PUBLISH_METHOD="${1:-none}" # "none", "local", "aws", ".dcos".
PACKAGE_VERSION="${2:-stub-universe}"

FRAMEWORK_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_NAME="kibana"
DCOS_COMMONS_DIRECTORY="$(cd "${FRAMEWORK_DIRECTORY}/../.." && pwd)"
FRAMEWORK_UNIVERSE_DIRECTORY="${FRAMEWORK_UNIVERSE_DIRECTORY:=${FRAMEWORK_DIRECTORY}/universe-kibana}"

# Grab TEMPLATE_x vars for use in universe template.
# shellcheck source=versions.sh
source "${FRAMEWORK_DIRECTORY}/versions.sh"

export TOOLS_DIRECTORY=${DCOS_COMMONS_DIRECTORY}/tools

case "${PUBLISH_METHOD}" in
  local)
    echo "Launching HTTP artifact server"
    PUBLISH_SCRIPT="${TOOLS_DIRECTORY}/publish_http.py"
    ;;
  aws)
    echo "Uploading to S3"
    PUBLISH_SCRIPT="${TOOLS_DIRECTORY}/publish_aws.py"
    ;;
  .dcos)
    echo "Uploading .dcos files to S3"
    PUBLISH_SCRIPT="${TOOLS_DIRECTORY}/publish_dcos_file.py"
    ;;
  *)
    echo "---"
    echo "Nothing to build as it's a Marathon app, so skipping publish step."
    echo "Use one of the following additional arguments to get something that runs on a cluster:"
    echo "- 'local': Host the build in a local HTTP server for use by a DC/OS Vagrant cluster."
    echo "- 'aws': Upload the build to S3."
    ;;
esac

if [ -n "${PUBLISH_SCRIPT}" ]; then
  export TEMPLATE_DOCUMENTATION_PATH="https://docs.mesosphere.com/services/elastic/"

  exec "${PUBLISH_SCRIPT}" \
       "${FRAMEWORK_NAME}" \
       "${PACKAGE_VERSION}" \
       "${FRAMEWORK_UNIVERSE_DIRECTORY}" \
       "${FRAMEWORK_DIRECTORY}/kibana/init.sh" \
       "${FRAMEWORK_DIRECTORY}/kibana/nginx.conf.tmpl"
fi
