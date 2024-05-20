from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,  # Useful for debugging - exports the metrics to console
    PeriodicExportingMetricReader,  # Reader that batches metrics in configurable time intervals before sending it to the exporter
)

def init():

    # Configure the provider with the exporter and reader
    exporter = ConsoleMetricExporter()
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=15000, export_timeout_millis=5000
    )
    provider = MeterProvider(metric_readers=[reader])

    # Set the global meter provider, and create a Meter for usage
    metrics.set_meter_provider(provider)

    print("OTEL Metrics successfully initialised")
