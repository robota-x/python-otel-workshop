from flask import Flask, request, render_template

from apps.videos import videos

app = Flask(__name__)


@app.get("/api/v1/video")
def get_videos():
    title_filter = request.args.get("filter", default="")  # TODO: instrument

    return videos.list(title_filter=title_filter)


@app.get("/api/v1/video/<id>")
def get_video_details(id):
    return videos.get(id)  # Unhandled exception on purpose


@app.get("/api/v1/video/<id>/like")
def like_video(id):
    videos.like(id)

    return ("OK", 200)


@app.get("/api/v1/video/<id>/dislike")
def dislike_video(id):
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
    # TODO: init Open Telemetry
    app.run(host="0.0.0.0")
