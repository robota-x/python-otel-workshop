# This is an minimal example Image and ignores best practices on security
# And size such as multi-stage and non-root. Don't use in production.

FROM python:alpine

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT [ "python", "app.py"]