# Official Microsoft Playwright image with Python and Chromium pre-installed
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Install system fonts for Devanagari / Hindi statement rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-deva \
    fonts-indic \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot codebase
COPY . .

# Run bot in polling mode (or override with webhook command)
CMD ["python", "-u", "bot.py"]
