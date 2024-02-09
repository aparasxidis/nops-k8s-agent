from base_metrics import BaseMetrics


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
    FILENAME = "deployment_metrics.parquet"
