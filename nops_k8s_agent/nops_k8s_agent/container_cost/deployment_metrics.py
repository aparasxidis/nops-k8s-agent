from nops_k8s_agent.container_cost.base_metrics import BaseMetrics


class DeploymentMetrics(BaseMetrics):
    # This class to get pod metrics from prometheus and put it in dictionary
    # List of metrics:
    list_of_metrics = {
        "kube_deployment_spec_replicas": [
            "deployment",
            "namespace",
        ],
        "kube_deployment_status_replicas_available": [
            "deployment",
            "namespace",
        ],
    }
    FILE_PREFIX = "deployment_metrics"
    FILENAME = "deployment_metrics_0.parquet"
