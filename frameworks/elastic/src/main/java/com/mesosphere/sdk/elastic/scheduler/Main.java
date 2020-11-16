package com.mesosphere.sdk.elastic.scheduler;

import com.mesosphere.sdk.framework.EnvStore;
import com.mesosphere.sdk.scheduler.DefaultScheduler;
import com.mesosphere.sdk.scheduler.SchedulerBuilder;
import com.mesosphere.sdk.scheduler.SchedulerConfig;
import com.mesosphere.sdk.scheduler.SchedulerRunner;
import com.mesosphere.sdk.scheduler.SchedulerUtils;
import com.mesosphere.sdk.specification.DefaultServiceSpec;
import com.mesosphere.sdk.specification.ReplacementFailurePolicy;
import com.mesosphere.sdk.specification.yaml.RawServiceSpec;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;

/**
 * Main entry point for the Scheduler.
 */
public final class Main {
  private static final String CUSTOM_YAML_BLOCK_BASE64_ENV = "CUSTOM_YAML_BLOCK_BASE64";
  private static final String ENABLE_AUTOMATIC_POD_REPLACEMENT_ENV = "ENABLE_AUTOMATIC_POD_REPLACEMENT";
  private Main() {}

  public static void main(String[] args) throws Exception {
    if (args.length != 1) {
      throw new IllegalArgumentException(
          "Expected one file argument, got: " + Arrays.toString(args)
      );
    }
    SchedulerRunner
        .fromSchedulerBuilder(createSchedulerBuilder(new File(args[0])))
        .run();
  }

  private static ReplacementFailurePolicy getReplacementFailurePolicy() throws Exception {
    return ReplacementFailurePolicy.newBuilder()
            .permanentFailureTimoutSecs(
                    Integer.valueOf(System.getenv("PERMANENT_FAILURE_TIMEOUT_SECS")))
            .minReplaceDelaySecs(
                    Integer.valueOf(System.getenv("MIN_REPLACE_DELAY_SECS")))
            .build();
  }

  private static SchedulerBuilder createSchedulerBuilder(File yamlSpecFile) throws Exception {
    RawServiceSpec rawServiceSpec = RawServiceSpec.newBuilder(yamlSpecFile).build();
    SchedulerConfig schedulerConfig = SchedulerConfig.fromEnv();

    // Modify pod environments in two ways:
    // 1) Elastic is unhappy if cluster.name contains slashes. Replace any slashes with
    // double-underscores.
    // 2) Base64 decode the custom YAML block.
    DefaultServiceSpec.Generator serviceSpecGenerator =
        DefaultServiceSpec.newGenerator(
            rawServiceSpec, schedulerConfig, yamlSpecFile.getParentFile())
            .setAllPodsEnv(
                "CLUSTER_NAME",
                SchedulerUtils.withEscapedSlashes(rawServiceSpec.getName())
            );

    String yamlBase64 = System.getenv(CUSTOM_YAML_BLOCK_BASE64_ENV);
    if (yamlBase64 != null && yamlBase64.length() > 0) {
      String esYamlBlock = new String(
          Base64.getDecoder().decode(yamlBase64),
          StandardCharsets.UTF_8
      );
      serviceSpecGenerator.setAllPodsEnv("CUSTOM_YAML_BLOCK", esYamlBlock);
    }

    DefaultServiceSpec.Builder builder = DefaultServiceSpec.newBuilder(serviceSpecGenerator.build());

    if (EnvStore.fromEnv().getOptionalBoolean(ENABLE_AUTOMATIC_POD_REPLACEMENT_ENV, false)) {
      builder.replacementFailurePolicy(getReplacementFailurePolicy());
    }

    return DefaultScheduler.newBuilder(builder.build(), schedulerConfig)
        .setCustomConfigValidators(Collections.singletonList(new ElasticZoneValidator()))
        .setPlansFrom(rawServiceSpec)
        .withSingleRegionConstraint();
  }
}
