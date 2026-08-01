FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir . fastapi "uvicorn[standard]" python-multipart

COPY src/ src/
COPY *.pdf ./

RUN mkdir -p /app/pdfs

EXPOSE 8000

ENV PYTHONPATH=/app/src

CMD ["uvicorn", "flashpdf.web_server:app", "--host", "0.0.0.0", "--port", "8000"]
