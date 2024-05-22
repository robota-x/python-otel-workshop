from apps.videos import videos
from apps.instrumentation import instrumentation
from flask import Flask, request, render_template
from time import time

from opentelemetry.metrics import get_meter_provider


app = Flask(__name__)

default_meter = get_meter_provider().get_meter("default")
meter_likes = default_meter.create_counter("video_likes", description="Calls to the Like Endpoint")
meter_dislikes = default_meter.create_counter("video_dislikes", description="Calls to the Dislike Endpoint")
meter_latency_get = default_meter.create_histogram("get_video_latency_milliseconds", unit="ms", description="Latency of Video information retrieval")


@app.get("/api/v1/video")
def get_videos():
    title_filter = request.args.get("filter", default="")  # TODO: instrument

    return videos.list(title_filter=title_filter)


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


@app.get("/api/v1/video/<id>/like")
def like_video(id):
    meter_likes.add(
        1,
        {
            "id": id,
        },
    )
    videos.like(id)

    return ("OK", 200)


@app.get("/api/v1/video/<id>/dislike")
def dislike_video(id):
    meter_dislikes.add(
        1,
        {
            "id": id,
        },
    )
    videos.dislike(id)

    return ("OK", 200)


@app.route("/")
def index():
    all_videos = [
        get_video_details(video_id) for video_id in videos.list(title_filter="")
    ]

    sorted_videos = sorted(
        all_videos,
        key=lambda video: int(video["likes"] - video["dislikes"]),
        reverse=True,
    )

    return render_template("home.html", videos=sorted_videos)


if __name__ == "__main__":
    instrumentation.init()
    app.run(host="0.0.0.0")
