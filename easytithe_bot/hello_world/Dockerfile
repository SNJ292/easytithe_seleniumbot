FROM python:3.11-bullseye

# Install Chromium, Chromedriver, and required runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libdrm2 \
    libx11-6 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libxss1 \
    libglib2.0-0 \
    libxshmfence1 \
    libcups2 \
    libasound2 \
    libxkbcommon0 \
    at-spi2-core \
    wget \
    curl \
    unzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /var/task

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app.py .

# Lambda runtime interface
ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["app.lambda_handler"]
