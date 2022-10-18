import sys
import traceback
import uuid
from datetime import datetime
from typing import Any

from django.conf import settings

import pandas as pd
from jinja2 import Template
from loguru import logger
from prometheus_api_client import PrometheusConnect
from prometheus_api_client.utils import parse_datetime

from nops_k8s_agent.libs.commonutils import duration_string

# TO Add a new new frequency
# nops_k8s_agent/nops_k8s_agent/management/commands/send_metrics.py
# start_time
# get_metrics
# Run job
metrics_set = {
    "pod_metadata": {
        "pod_metadata_fmt_pod_info": "avg_over_time(kube_pod_info[{{ start_time }}])",
        "pod_metadata_fmt_pod_owners": "sum(avg_over_time(kube_pod_owner[{{ start_time }}])) by (pod, owner_name, owner_kind, namespace, uid, {{ cluster_id }})",
        "pod_metadata_fmt_job_owners": "sum(avg_over_time(kube_job_owner[{{ start_time }}])) by (job_name, owner_name, owner_kind, namespace , {{ cluster_id }})",
        "pod_metadata_fmt_replicaset_owners": "sum(avg_over_time(kube_replicaset_owner[{{ start_time }}])) by (replicaset, owner_name, owner_kind, namespace , {{ cluster_id }})",
        "pod_metadata": "sum(avg_over_time(kube_replicationcontroller_owner[{{ start_time }}])) by (replicationcontroller, owner_name, owner_kind, namespace , {{ cluster_id }})",
    },
    "node_metrics": {
        "node_metrics_fmt_node_memory_Buffers_bytes": "avg(avg_over_time(node_memory_Buffers_bytes[{{ start_time }}])) by (instance, {{ cluster_id }})",
        "node_metrics_fmt_node_memory_Cached_bytes": "avg(avg_over_time(node_memory_Cached_bytes[{{ start_time }}])) by (instance, {{ cluster_id }})",
        "node_metrics_fmt_node_memory_MemFree_bytes": "avg(avg_over_time(node_memory_Buffers_bytes[{{ start_time }}])) by (instance, {{ cluster_id }})",
        "node_metrics_fmt_node_cpu_seconds_total": 'avg(avg_over_time(node_cpu_seconds_total{mode="idle"}[{{ start_time }}])) by (instance, {{ cluster_id }}, mode, cpu)',
    },
    "low": {
        "metrics_fmt_ram_bytes_limit": 'avg(avg_over_time(kube_pod_container_resource_limits_memory_bytes{container!="", container!="POD", node!=""}[{{ start_time }}])) by (container, pod, namespace, node, {{ cluster_id }}, provider_id)',
        "metrics_fmt_cpu_cores_limit": 'avg(avg_over_time(kube_pod_container_resource_limits_cpu_cores{container!="", container!="POD", node!=""}[{{ start_time }}])) by (container, pod, namespace, node, {{ cluster_id }})',
        "metrics_fmt_ram_bytes_allocated": 'avg(avg_over_time(kube_pod_container_resource_requests_memory_bytes{container!="", container!="POD", node!=""}[{{ start_time }}])) by (container, pod, namespace, node, {{ cluster_id }}, provider_id)',
        "metrics_fmt_cpu_cores_allocated": 'avg(avg_over_time(kube_pod_container_resource_requests_cpu_cores{container!="", container!="POD", node!=""}[{{ start_time }}])) by (container, pod, namespace, node, {{ cluster_id }})',
        "metrics_fmt_namespace_labels": "avg_over_time(kube_namespace_labels[{{ start_time }}])",
        "metrics_fmt_namespace_annnotations": "avg_over_time(kube_namespace_annotations[{{ start_time }}])",
        "metrics_fmt_pod_labels": "avg_over_time(kube_pod_labels[{{ start_time }}])",
        "metrics_fmt_pod_annotations": "avg_over_time(kube_pod_annotations[{{ start_time }}])",
        "metrics_fmt_service_labels": "avg_over_time(service_selector_labels[{{ start_time }}])",
        "metrics_fmt_deployment_labels": "avg_over_time(deployment_match_labels[{{ start_time }}])",
        "metrics_fmt_statefulset_labels": "avg_over_time(statefulSet_match_labels[{{ start_time }}])",
        "metrics_fmt_pod_info": "avg_over_time(kube_pod_info[{{ start_time }}])",
        "metrics_fmt_container_info": "avg_over_time(kube_pod_container_info[{{ start_time }}])",
        "metrics_fmt_pod_owners": "sum(avg_over_time(kube_pod_owner[{{ start_time }}])) by (pod, owner_name, owner_kind, namespace , {{ cluster_id }})",
    },
    "medium": {
        "metrics_fmt_ram_usage_bytes": 'avg(avg_over_time(container_memory_usage_bytes{container!="", container!="POD", node!=""}[{{ start_time }}])) by (container, pod, namespace, node, {{ cluster_id }}, provider_id)',
        "metrics_fmt_net_transfer_bytes": 'sum(increase(container_network_transmit_bytes_total{pod!=""}[{{ start_time }}])) by (pod_name, pod, namespace, {{ cluster_id }})',
        "metrics_fmt_cpu_usage_avg": 'avg(rate(container_cpu_usage_seconds_total{container!="", container_name!="POD", container!="POD"}[{{ start_time }}])) by (container_name, container, pod_name, pod, namespace, instance,  {{ cluster_id }})',
        "metrics_fmt_cpu_usage_max": 'max(rate(container_cpu_usage_seconds_total{container!="", container_name!="POD", container!="POD"}[{{ start_time }}])) by (container_name, container, pod_name, pod, namespace, instance,  {{ cluster_id }})',
    },
    "high": {
        "metrics_fmt_pods": "avg(kube_pod_container_status_running{}) by (pod, namespace, {{ cluster_id }})[{{ start_time }}:{{ end_time }}]",
        "metrics_fmt_pods_uid": "avg(kube_pod_container_status_running{}) by (pod, namespace, uid, {{ cluster_id }})[{{ start_time }}:{{ end_time }}]",
    },
}
metrics_list = {
    # "metrics_fmt_daemonset_labels": 'sum(avg_over_time(kube_pod_owner{owner_kind="DaemonSet"}[{{ start_time }}])) by (pod, owner_name, namespace, {{ cluster_id }})',  # DEPRECATED
    # "metrics_fmt_job_labels": 'sum(avg_over_time(kube_pod_owner{owner_kind="Job"}[{{ start_time }}])) by (pod, owner_name, namespace, {{ cluster_id }})',  # DEPRECATED
    # "metrics_fmt_pods_with_replicaset_owner": 'sum(avg_over_time(kube_pod_owner{owner_kind="ReplicaSet"}[{{ start_time }}])) by (pod, owner_name, namespace , {{ cluster_id }})',  # DEPRECATED
    # "metrics_fmt_replicasets_without_owners": 'avg(avg_over_time(kube_replicaset_owner{owner_kind="<none>", owner_name="<none>"}[{{ start_time }}])) by (replicaset, namespace, {{ cluster_id }})',  # DEPRECATED
}


class KubeMetrics:
    def __init__(self):
        if settings.NOPS_K8S_AGENT_PROM_TOKEN:
            headers = {"Authorization": settings.NOPS_K8S_AGENT_PROM_TOKEN}
        else:
            headers = {}
        self.prom_client = PrometheusConnect(url=settings.PROMETHEUS_SERVER_ENDPOINT, headers=headers, disable_ssl=True)
        if settings.DEBUG is not True:
            logger.remove()
            logger.add(sys.stderr, level="WARNING")

    @classmethod
    def get_status(cls):
        try:
            self = cls()
            assert self.prom_client.get_metric_range_data(metric_name="kube_node_info")
            status = "Success"
        except Exception:
            status = "Failed"
        return status

    def start_time(self, frequency) -> datetime:
        start_time = parse_datetime("65m")
        if frequency == "low" or frequency == "pod_metadata":
            start_time = parse_datetime("65m")
        elif frequency == "medium":
            start_time = parse_datetime("35m")
        elif frequency == "high" or frequency == "node_metrics":
            start_time = parse_datetime("15m")
        logger.info(start_time)
        return start_time

    def end_time(self) -> datetime:
        end_time = parse_datetime("now")
        logger.info(end_time)
        return end_time

    def cluster_id(self) -> str:
        return settings.NOPS_K8S_AGENT_CLUSTER_ID

    def convert_metrics_template(self, template: str, input_params: dict[Any, Any]) -> str:
        try:
            tm = Template(template)
            tm.globals["enumerate"] = enumerate
            task = tm.render(**input_params)
            return task
        except Exception as err:
            logger.exception(traceback.format_exc())
            logger.exception(err)

    def get_metrics(self, frequency="high"):
        metrics_result = []
        try:
            metrics_params = {
                "cluster_id": "instance",
                "start_time": duration_string((self.end_time() - self.start_time(frequency)).total_seconds()),
                "end_time": duration_string((self.end_time() - self.start_time(frequency)).total_seconds()),
            }
            event_type = "k8s_metrics"
            if frequency == "pod_metadata":
                event_type = "k8s_pod_metadata"
            elif frequency == "node_metrics":
                event_type = "k8s_node_metrics"

            for key, value in metrics_set[frequency].items():
                logger.info(f"metrics template:{value}")
                metrics_query = self.convert_metrics_template(value, input_params=metrics_params)
                logger.info(metrics_query)
                response = self.prom_client.custom_query(query=metrics_query)
                result_df = self.metrics_to_df(input_array=response)
                if result_df is not None and result_df.shape[0] > 0:
                    result_df["metric_name"] = key
                    result_df["cluster_id"] = self.cluster_id()
                    result_df["event_id"] = str(uuid.uuid4())
                    result_df["cloud"] = "aws"  # TODO SUPPORT MORE CLOUD
                    result_df["event_type"] = event_type
                    result_df["extraction_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    result_df["schema_version"] = settings.SCHEMA_VERSION
                    logger.info(f"metric extraction completed for:{key}")
                    metrics_result.append(result_df)
        except Exception as err:
            logger.warning(err)
        finally:
            if metrics_result:
                final_pd = pd.concat(metrics_result)
                return final_pd.to_dict(orient="records")
            else:
                return None

    def metrics_to_df(self, input_array: dict[Any, Any]):
        try:
            df = pd.json_normalize(input_array)
            df.fillna("", inplace=True)
            if len(df.columns) == 0:
                return
            if "values" in list(df.columns):
                df[["value", "time"]] = df["values"].apply(
                    lambda a: pd.Series([a[0][1], pd.Timestamp(a[0][0], unit="s").strftime("%Y-%m-%d %H:%M:%S")])
                )
                df.drop(columns=["values"], inplace=True)
            else:
                df[["value", "time"]] = df["value"].apply(
                    lambda a: pd.Series([a[1], pd.Timestamp(a[0], unit="s").strftime("%Y-%m-%d %H:%M:%S")])
                )

            def transform(input, non_metric_cols):
                x = {}
                y = []
                for col in non_metric_cols:
                    x[col] = input[col]
                y.append(x)
                return pd.Series(y)

            non_metric_cols = [col for col in list(df.columns) if col not in ["value", "time"]]
            df[["metrics_metadata"]] = df.apply(lambda x: transform(x, non_metric_cols), axis=1)
            df.drop(columns=non_metric_cols, inplace=True)
            return df
        except Exception as err:
            logger.exception(err)
            return pd.DataFrame()
