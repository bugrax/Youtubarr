FROM python:3.12-slim

# ffmpeg/ffprobe: yt-dlp stream merge + import duration verification
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY poc ./poc

ENV YTA_DB_PATH=/config/youtubarr.db \
    YTA_LIBRARY_PATH=/movies \
    YTA_DOWNLOAD_PATH=/downloads/youtubarr \
    YTA_SYNC_INTERVAL_MIN=360

EXPOSE 8585
VOLUME ["/config"]

# keep yt-dlp current at start (YouTube changes break old versions)
CMD ["sh", "-c", "pip install -q --no-cache-dir -U yt-dlp; exec uvicorn app.main:app --host 0.0.0.0 --port 8585"]
