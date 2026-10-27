# Official Microsoft Playwright image with Python and Chromium pre-installed
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

WORKDIR /app

# Install system fonts for Devanagari / Hindi statement rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-deva \
    fonts-indic \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot codebase
COPY bot/ .

ENV PORT=8080
EXPOSE 8080

# Run bot with FastAPI health check and auto-polling/webhook
CMD ["sh", "-c", "uvicorn webhook:app --host 0.0.0.0 --port ${PORT:-8080}"]
