FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY app.py .

# Gunicorn for WSGI server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8050", "app:server"]
