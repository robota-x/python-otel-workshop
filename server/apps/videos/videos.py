import json
import math
import os
import random
import time


dirname = os.path.dirname(__file__)
DATABASE_JSON_LOCATION = os.path.join(dirname, "./db.json")


def init():
    pass  # TODO implement actual database


def list(title_filter):
    with open(DATABASE_JSON_LOCATION) as db:
        videos = json.load(db)

    return [
        video["id"]
        for video in videos
        if title_filter.lower() in video["title"].lower()
    ]


def get(id):
    with open(DATABASE_JSON_LOCATION) as db:
        videos = json.load(db)

    for video in videos:
        if video["id"] == id:
            return video
    raise ValueError(f"ID {id} does not exists")


def like(id):
    with open(DATABASE_JSON_LOCATION) as db:
        videos = json.load(db)

    for video in videos:
        if video["id"] == id:
            video["likes"] += 1
            continue
    time.sleep(math.fabs(random.gauss(mu=1, sigma=0.5)))

    with open(DATABASE_JSON_LOCATION, "w") as db:
        json.dump(videos, db, indent=2)


def dislike(id):
    with open(DATABASE_JSON_LOCATION) as db:
        videos = json.load(db)

    for video in videos:
        if video["id"] == id:
            video["dislikes"] += 1
            continue
    with open(DATABASE_JSON_LOCATION, "w") as db:
        json.dump(videos, db, indent=2)
