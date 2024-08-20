#!/bin/bash

# Update package lists and install dependencies
apt-get update
apt-get install -y wget unzip ca-certificates fontconfig locales

# Download and install headless-chromium
wget https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-37/headless-chromium -O /usr/local/bin/headless-chromium
chmod +x /usr/local/bin/headless-chromium
