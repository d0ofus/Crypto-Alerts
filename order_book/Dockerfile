FROM python:3.11.4

RUN apt-get update -qq -y && \
    apt-get install -y \
        libasound2 \
        libatk-bridge2.0-0 \
        libgtk-4-1 \
        libnss3 \
        xdg-utils \
        wget && \
    # Install chrome
    wget -q -O chrome-linux64.zip https://bit.ly/chrome-linux64-121-0-6167-85 && \
    unzip chrome-linux64.zip && \
    rm chrome-linux64.zip && \
    mv chrome-linux64 /opt/chrome/ && \
    ln -s /opt/chrome/chrome /usr/local/bin/ && \
    # Install chromedriver
    wget -q -O chromedriver-linux64.zip https://bit.ly/chromedriver-linux64-121-0-6167-85 && \
    unzip -j chromedriver-linux64.zip chromedriver-linux64/chromedriver && \
    rm chromedriver-linux64.zip && \
    mv chromedriver /usr/local/bin/

COPY . /app

WORKDIR /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "alert_depth.py"] 


#%% -----------------------------------------------------------------------------------------
# # Use an official Python runtime as a parent image
# FROM python:3.9-slim

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# # Install dependencies
# RUN apt-get update && \
#     apt-get install -y wget unzip curl xvfb libxi6 libgconf-2-4 && \
#     apt-get install -y --no-install-recommends \
#     fonts-liberation \
#     libappindicator3-1 \
#     xdg-utils \
#     gnupg \
#     libnss3 \
#     libatk-bridge2.0-0 \
#     libxss1 \
#     libgbm1 \
#     libgtk-3-0 \
#     libasound2 \
#     libnspr4 \
#     && apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# # Install Chrome for Testing
# # RUN CHROME_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
# RUN wget -q --continue -P /tmp/ "https://storage.googleapis.com/chrome-for-testing-public/128.0.6613.84/linux64/chrome-linux64.zip" && \
#     # wget -q --continue -P /tmp/ "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chrome-linux64.zip" && \
#     # wget -q --continue -P /tmp/ "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chrome-linux64.zip" && \
#     unzip /tmp/chrome-linux64.zip -d /opt/ && \
#     ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
#     rm /tmp/chrome-linux64.zip


# # Install matching ChromeDriver for Testing
# # RUN CHROME_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
#     # wget -q --continue -P /tmp/ "https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
#     # wget -q --continue -P /tmp/ "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
# RUN wget -q --continue -P /tmp/ "https://storage.googleapis.com/chrome-for-testing-public/128.0.6613.84/linux64/chromedriver-linux64.zip" && \
#     unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
#     # Move the chromedriver binary directly to /usr/local/bin/ and give it the correct name
#     mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \ 
#     rm /tmp/chromedriver-linux64.zip

# # Install other dependencies (e.g., Python libraries)
# COPY ./requirements.txt /app/requirements.txt
# WORKDIR /app
# RUN pip install --upgrade pip
# RUN pip install -r requirements.txt

# # Set display port to avoid crash
# ENV DISPLAY=:99

# # Copy project files
# COPY . /app

# # Command to run the scripts using Xvfb
# CMD ["bash", "-c", "Xvfb :99 -screen 0 1024x768x24 & python alert_aggTrade.py"]

# # Install latest stable Chrome browser
# RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
#     sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' && \
#     apt-get update && \
#     apt-get install -y google-chrome-stable && \
#     rm -rf /var/lib/apt/lists/*

# # Install ChromeDriver for a fixed version
# RUN CHROME_DRIVER_VERSION=114.0.5735.90 && \
#     wget -q -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip && \
#     unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
#     rm /tmp/chromedriver.zip

# # Download the latest ChromeDriver version
# RUN CHROMEDRIVER_VERSION=$(curl -sS https://chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
#     wget -q --continue -P /tmp/ "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
#     unzip /tmp/chromedriver_linux64.zip -d /usr/local/bin/ && \
#     rm /tmp/chromedriver_linux64.zip

# docker build -t tradingview-alert-bot .

#%% ----------------------------------------------------------------------------------------------------------------------------------
# # Use an official base image
# FROM ubuntu:20.04

# # Set environment variables
# ENV DEBIAN_FRONTEND=noninteractive

# # Install dependencies and update SSL certificates
# RUN apt-get update && apt-get install -y \
#     wget \
#     curl \
#     unzip \
#     gnupg \
#     libnss3 \
#     libgconf-2-4 \
#     libxss1 \
#     libasound2 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libgbm1 \
#     libnspr4 \
#     ca-certificates \
#     fonts-liberation \
#     xdg-utils \
#     --no-install-recommends && \
#     update-ca-certificates

# # Install Chrome for Testing
# RUN CHROME_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
#     wget -q --continue -P /tmp/ "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chrome-linux64.zip" && \
#     unzip /tmp/chrome-linux64.zip -d /opt/ && \
#     ln -s /opt/chrome-linux64/chrome /usr/bin/google-chrome && \
#     rm /tmp/chrome-linux64.zip

# # Install matching ChromeDriver for Testing
# RUN CHROME_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_STABLE) && \
#     wget -q --continue -P /tmp/ "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" && \
#     unzip /tmp/chromedriver-linux64.zip -d /opt/chrome-linux64/ && \
#     ln -s /opt/chrome-linux64/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
#     rm /tmp/chromedriver-linux64.zip

# # Verify installation
# RUN google-chrome --version && \
#     chromedriver --version

# # Clean up
# RUN apt-get clean && \
#     rm -rf /var/lib/apt/lists/*

# # Set the default command
# CMD ["bash"]

