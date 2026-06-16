FROM python:3.10-slim

# Install system dependencies for OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install deps first (cache optimization)
# Use the optimized requirements file from the backend directory
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project backend
COPY backend ./backend

# run app using the backend module
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app", "--bind", "0.0.0.0:10000"]
