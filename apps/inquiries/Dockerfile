# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY server.py ./

RUN useradd --create-home --uid 10001 inquiries \
 && mkdir -p /data && chown inquiries:inquiries /data
USER inquiries

ENV PORT=8080 INQUIRIES_DB=/data/inquiries.db
EXPOSE 8080
CMD ["python", "server.py"]
