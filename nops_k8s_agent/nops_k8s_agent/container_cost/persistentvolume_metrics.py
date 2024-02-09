from base_metrics import BaseMetrics


class PersistentvolumeMetrics(BaseMetrics):
    # This class to get pod metrics from prometheus and put it in dictionary
    # List of metrics:
    list_of_metrics = {
        "kube_persistentvolume_capacity_bytes": [
            "persistentvolume",
        ],
        "kube_persistentvolume_status_phase": [
            "persistentvolume",
            "phase",
        ],
    }
    FILENAME = "persistentvolume_metrics.parquet"
