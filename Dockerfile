FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# /data holds config.json, queue/watcher state, logs and the Widevine .wvd (searched in the cwd).
ENV CRUNCHYROLLER_HOST=0.0.0.0 \
    CRUNCHYROLLER_DATA_DIR=/data \
    XDG_STATE_HOME=/data \
    HOME=/data \
    PYTHONUNBUFFERED=1
RUN mkdir -p /data /downloads && chmod 777 /data /downloads
WORKDIR /data
VOLUME ["/data", "/downloads"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"

# --browser = headless web server + watcher (no pywebview window inside the container).
CMD ["python", "/app/main.py", "--gui", "--browser", "--port", "8000"]
