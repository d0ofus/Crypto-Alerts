# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install dependencies
RUN apt-get update && \
    apt-get install -y wget unzip curl xvfb libxi6 libgconf-2-4 && \
    apt-get install -y --no-install-recommends \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    gnupg \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# # Install Chrome browser
# RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
#     sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
#     apt-get update && \
#     apt-get install -y google-chrome-stable && \
#     rm -rf /var/lib/apt/lists/*

ENV CHROME_VERSION=114.0.5735.198-1
RUN wget -q https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb
RUN apt-get -y update
RUN apt-get install -y ./google-chrome-stable_${CHROME_VERSION}_amd64.deb


# Install ChromeDriver for a fixed version
RUN CHROME_DRIVER_VERSION=114.0.5735.90 && \
    wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip

# Install other dependencies (e.g., Python libraries)
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Set display port to avoid crash
ENV DISPLAY=:99

# Copy project files
COPY . /app

# Command to run the scripts
CMD ["python", "alert_aggTrade.py"]
