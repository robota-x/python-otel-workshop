# Instrumenting a Python app with OTEL - Pycon Italia 2024

You can find the slides for the initial overview of OTEL and of the workshop [here](https://docs.google.com/presentation/d/19sNl2inhuTlLwffgRKd9QFcVR9wd1V0UUiUG05xoKM8)

## Part 1 - Instrumenting the Python application

It's worth noting that OpenTelemetry has [very powerful auto-instrumentation](https://opentelemetry.io/docs/languages/python/automatic/) for Python, supporting multiple frameworks such as Flask. In this tutorial, we're eskewing them in favour of manually setting up a few custom metrics.

### Inspecting the Python App

1. Clone this repo locally and take a look around. The main application is under the `./server` folder, and consist of a simple Flask app to display a list of youtube videos, and a small api to like/dislike on each video. 

2. The app talks to a local "database" (a JSON file...) via the `videos` module, under `apps`

3. To set up and run locally, still from the server folder, you can create a virtualenvironment, activate it, and install the dependencies via `pip install -r requirements.txt`, then run via `python app.py`. The application should be available by default under http://127.0.0.1:5000

4. You can also build and run the application via the provided Dockerfile: `docker build -t "video-voter" .` (again, in the `./server` folder, and `docker run --rm -p 5000:5000 video-voter`.


### Integrating OTEL in the Python App

1. To start, we want to install a couple of OTEL packages: `pip install opentelemetry-api opentelemetry-sdk`. Remember to save them to the requirements file, for the Docker Build to be picked up - `pip freeze > requirements.txt`

2. Create a new module under `apps/instrumentation`: add the `__init__.py` file and an emptyu `instrumentation.py`. This is not strictly required, but good to segregate the fairly verbose init code.

3. In the new module, add the following imports, which is all the machinery we need to set up metrics via the OTEL SDK.
    ```python
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,  # Useful for debugging - exports the metrics to console
        PeriodicExportingMetricReader,  # Reader that batches metrics in configurable time intervals before sending it to the exporter
    )
    ```

4. Configure a batch exporter (`PeriodicExportingMetricReader`) that pushes to the standard output (`ConsoleMetricExporter`), and set it as a Meter provider.
    ```python
    def init():
        # Configure the provider with the exporter and reader
        exporter = ConsoleMetricExporter()
        reader = PeriodicExportingMetricReader(exporter)
        provider = MeterProvider(metric_readers=[reader])

        # Set the global meter provider, and create a Meter for usage
        metrics.set_meter_provider(provider)

        print("OTEL Metrics successfully initialised")
    ```

5. In the main `app.py` file, import the new module and call the init method as part of the app startup.
    ```python
    from apps.instrumentation import instrumentation

    #[...main app]

    if __name__ == "__main__":
    instrumentation.init()
    app.run(host="0.0.0.0")
    ```

6. Test the app again: `python app.py`. You should see a message about OTEL Metrics being initialised successfully as part of the startup.


### Setting up the first custom metrics in the Python App

1. Open the `app.py` file (or other file you want to instrument) and add yet another import, to be able to grab the meter provider
    ```python
    from opentelemetry.metrics import get_meter_provider
    ```

2. Further down, let's pull the global provider, declare a meter called default, and a counter metrics. Counters are monotonically increasing metrics, which are great for ever-increasing numbers such as visits to a page.
    ```python
    default_meter = get_meter_provider().get_meter("default")
    meter_likes = default_meter.create_counter("video_likes")
    ```

3. Now that we declared the first metric, we can finally use it. Locate the like endpoint and add to it the counter increment.
   ```python
    meter_likes.add(
        1,
        {
            "id": id,
        },
    )
    ```

4. We got our first custom metric! Hit `http://127.0.0.1:5000/api/v1/video/1/like` from your browser a few times, and wait (up to 60 seconds) for it to show in our console.   
It's worth noting how beside the increment of `1`, we've also added a dictionary of Attributes. These are ideal to be able to discriminate different events, but we must be thinking on how they are used by our Metrics backend, and any limitation. In Prometheus, for example, we want Attribute that have only a limited number of possible values, as [the total number of time series](https://www.robustperception.io/cardinality-is-key/) is multiplicative.


### Adding further metrics

1. You can further declare a metric for dislikes, or visits to the main page, and add it to the related endpoints. Deciding if it's going to be the same metric with different attributes or 2 different metrics depends on the use you want to make of it.

2. Once you're satisfied with counters, let's add a new type of metric, called histogram, to the `get_video_details` function. A histogram is good to record a spread of values to run statistics on - a classic example is the latency of a call.
    ```python
    from time import time # Import time at the top
   
    # [...other imports]
   
    meter_latency_get = default_meter.create_histogram("get_video_latency_milliseconds", unit="s")

    # [..various methods]

    @app.get("/api/v1/video/<id>")
    def get_video_details(id):
    start = time()
    video = videos.get(id)
    end = time()
    meter_latency_get.record(
        (end - start) * 1000,
        {
            "id": id,
        },
    )

    return video
    ```
3. Test your metrics again by hitting `http://127.0.0.1:5000/api/v1/video/1`

### Moving to a OTLP Exporter

1. More installing: run `pip install opentelemetry-exporter-otlp-proto-grpc` and `pip freeze > requirements.txt`
2. And more importing: update the `instrumentation.py` file to use the new exporter:
    ```python
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

    #[...existing setup]

    # Change this existing line from the existing exporter = ConsoleMetricExporter()
    exporter = OTLPMetricExporter(insecure=True) # Endpoint provided via Environment variable - OTEL_EXPORTER_OTLP_ENDPOINT
    ```
    This will move our exporter to a push endpoint, that we will provide in the next few steps.
3. Do a last test: build docker and run it, and then hit a instrumented endpoint a few times. In the server log, you should get some `Transient error StatusCode.UNAVAILABLE encountered while exporting metrics to localhost:4317, retrying in 1s.` Errors in your logs

## Part 2 - Setting up the Open Telemetry Collector

1. Create a new folder called `pipeline` or similar in your project root
2. in the folder, create a `compose.yaml` file and add the current configuration to it:
    ```yaml
    services:
        # Video Voter Application
        video-voter:
            build: ../server
            depends_on:
            - otel-collector # Depends on otel-collector to be running first
            environment:
                OTEL_EXPORTER_OTLP_ENDPOINT: otel-collector:4317
            ports:
            - "5000:5000"

        # OpenTelemetry Collector
        otel-collector:
            image: otel/opentelemetry-collector:0.100.0 # Use `otel/opentelemetry-collector-contrib` to support more backends.
            command:
            - "--config=/conf/otel-collector-config.yaml" # Autodiscovery folder changes between versions. Better to provide explicitly.
            volumes:
            - ./conf/otel-collector-config.yaml:/conf/otel-collector-config.yaml
            ports:
            - 8888:8888 # Prometheus metrics exposed by the collector
            - 8889:8889 # Prometheus exporter metrics
            - 13133:13133 # health_check extension
            - 4317:4317 # OTLP gRPC receiver
            - 4318:4318 # OTLP http receiver
            restart: unless-stopped
    ```
3. In the same folder, create a `conf` subfolder that will host the configuration for our components, and in a `otel-collector-config.yaml` file add:
    ```yaml
    receivers:
    otlp:
        protocols:
        grpc:
            endpoint: 0.0.0.0:4317

    processors:
    batch:

    exporters:
    prometheus:
        endpoint: 0.0.0.0:8889
        namespace: default
    debug:
        verbosity: detailed

    extensions:
    health_check:

    service:
        extensions: [health_check]
        pipelines:
            metrics:
                receivers: [otlp]
                processors: [batch]
                exporters: [prometheus]
    ```
4. Run `docker-compose up --build` from within the `pipeline` folder to start up the compose stack and ensure that the Python Docker image will build each time.
5. Verify that your stack is up and running `http://127.0.0.1:8888/metrics`. These are the self-reporting metrics for OTEL. 
6. Hit `http://127.0.0.1:5000/api/v1/video/1` a few times and check `http://127.0.0.1:8889/metrics` - these will be the re-exported metrics from our app.

## Part 3 - Setting up Prometheus

0. If still running, stop Docker Compose via CTRL+C.

1. Update the existing `compose.yaml` file inside the `pipeline` folder, to add Prometheus (nested under `services`):
    ```yaml
    # Prometheus
    prometheus:
        image: prom/prometheus:latest
        volumes:
        - ./conf/prometheus-config.yaml:/etc/prometheus/prometheus.yml
        depends_on:
        - otel-collector 
        ports:
        - "9090:9090"
    ```

2. As before, create a configuration file in the `pipeline/conf` folder, called `prometheus-config.yaml`:
    ```yaml
    scrape_configs:
      - job_name: "otel-collector-self-reporting"
        scrape_interval: 15s
        static_configs:
        - targets:
            - "otel-collector:8888"
      - job_name: "otel-collector-exporter"
        scrape_interval: 15s
        static_configs:
        - targets:
            - "otel-collector:8889"
    ```

3. Run `docker-compose up` from within the `pipeline` folder to start up the compose stack again. Prometheus should come online after

4. Navigate to `http://127.0.0.1:9090/` to load the Prometheus instance. Under the `targets` section you can see the current scrape status.

5. Generate a few metrics by using the Python app, and try to run a query on the main Prometheus instance. For example if you hit `http://127.0.0.1:5000/api/v1/video/1/like` and you instrumented with with a like counter, you can query for `default_video_likes_total`

## Part 4 - Grafana and queries

1. Add further to the stack, by editing the `compose.yaml` file and setting up Grafana
    ```yaml

    # Grafana
    grafana:
        image: grafana/grafana:latest
        volumes:
        - ./conf/grafana-datasources.yaml:/etc/grafana/provisioning/datasources/datasources.yaml
        ports:
        - "3000:3000"
    ```
2. Add the Datasource configuration to Grafana. While it can be set up manually from the Grafana interface, a static provisioning is foolprof and prevents accidental deletes. In the `conf` folder, create `grafana-datasources.yaml` and add to it:
    ```yaml
    datasources:
    - name: Prometheus
      type: prometheus
      uid: prometheus-1
      url: http://prometheus:9090
      access: server
    ```

3. Finally, go to `http://locahost:3000` and open the Grafana interface. By default the user and password are both `admin`.

4. Navigate to `Datasources` and `prometheus` should be already there, automatically configured

5. Repeat the metric generation via the PYthon app and then use either the `Explore` tab to graph them, or create new persistent Dashboards.

## Wrapup

That's it! Feel free to experiment further, and if you change instrumentation in the Python app, remember to provide the `--build` flag to docker-compose to ensure the changes propagate.

Some ideas:
* update the meter provider from `default` to the name of the app, to have better named apps
* explore other types of metrics, such as gauges, and build some more comprehensive dashboards.
* start putting some load to the system: [k6s](https://k6.io/) is a good tool, but even a simple [hey](https://github.com/rakyll/hey) session can work well
* look into integrating traces and logs in the stack.