#!/bin/bash

IFS=","
PLUGINS=""
PROXY_ES_JAVA_OPTS=""

# If a plugin fails to install, exit the script immediately with an error
set -e

if [ -n "${ELASTICSEARCH_PLUGINS}" ]; then
  PLUGINS="${ELASTICSEARCH_PLUGINS}"
fi

if [ -n "${PLUGIN_HTTP_PROXY_HOST}" ] && [ -n "${PLUGIN_HTTP_PROXY_PORT}" ]; then
  PROXY_ES_JAVA_OPTS="-Dhttp.proxyHost=${PLUGIN_HTTP_PROXY_HOST} -Dhttp.proxyPort=${PLUGIN_HTTP_PROXY_PORT}"
fi

if [ -n "$PLUGIN_HTTPS_PROXY_HOST" ] && [ -n "$PLUGIN_HTTPS_PROXY_PORT" ]; then
    PROXY_ES_JAVA_OPTS="$PROXY_ES_JAVA_OPTS -Dhttps.proxyHost=$PLUGIN_HTTPS_PROXY_HOST -Dhttps.proxyPort=$PLUGIN_HTTPS_PROXY_PORT"
fi

if [ -n "$PROXY_ES_JAVA_OPTS" ]; then
    export ES_JAVA_OPTS="$ES_JAVA_OPTS $PROXY_ES_JAVA_OPTS"
fi

if [ -n "${SEARCHGUARD_ENABLED}" ]; then
    openssl pkcs8 -in node.key -topk8 -nocrypt -out node.key.pkcs8
    PLUGIN_FILE=$(ls $MESOS_SANDBOX/search-guard-*.zip)

    SEARCHGUARD_PLUGIN="file://${PLUGIN_FILE}"
    if [ -n "$PLUGINS" ]; then
        PLUGINS="$PLUGINS$IFS$SEARCHGUARD_PLUGIN"
    else
        PLUGINS="$SEARCHGUARD_PLUGIN"
    fi
fi

for PLUGIN in ${PLUGINS}; do
  echo "Installing plugin: ${PLUGIN}"
  "./elasticsearch-${ELASTIC_VERSION}/bin/elasticsearch-plugin" install --batch "${PLUGIN}"
done
