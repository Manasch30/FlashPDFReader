FROM python:3.11-slim

# Install system dependencies for PySide6 (Qt GUI), Qt Multimedia, and Audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libegl1 \
    libdbus-1-3 \
    libfontconfig1 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libpulse0 \
    pulseaudio \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "flashpdf.app"]
