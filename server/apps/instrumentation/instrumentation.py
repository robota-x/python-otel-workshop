from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,  # Useful for debugging - exports the metrics to console
    PeriodicExportingMetricReader,  # Reader that batches metrics in configurable time intervals before sending it to the exporter
)
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def init():
    # Create a unique identifier for this App
    resource = Resource(attributes={SERVICE_NAME: "video-voter"})

    # Configure the provider with the exporter and reader
    exporter = OTLPMetricExporter(insecure=True) # Endpoint provided via Environment variable - OTEL_EXPORTER_OTLP_ENDPOINT
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=15000, export_timeout_millis=5000
    )
    provider = MeterProvider(resource=resource, metric_readers=[reader])

    # Set the global meter provider, and create a Meter for usage
    metrics.set_meter_provider(provider)

    print("OTEL Metrics successfully initialised")
