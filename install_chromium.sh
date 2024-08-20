#!/bin/bash

# Create a directory for the Chromium binary
mkdir -p /tmp/chromium

# Download the pre-built headless-chromium binary
wget https://github.com/adieuadieu/serverless-chrome/releases/download/v1.0.0-37/headless-chromium -O /tmp/chromium/headless-chromium

# Make the binary executable
chmod +x /tmp/chromium/headless-chromium
