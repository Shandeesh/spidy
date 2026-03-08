#!/bin/bash

echo "🕷️ Spidy Shoonya Cloud Deploy 🕷️"
echo "-----------------------------------"

# 1. Install System Deps
# sudo apt-get update && sudo apt-get install -y python3-pip git screen

# 2. Install Python Deps
echo "📦 Installing Dependencies..."
pip install -r requirements.txt

# 3. Install NorenRestApiPy (Official)
echo "📦 Installing Shoonya API..."
pip install NorenRestApiPy --upgrade

# 4. Run Server
echo "🚀 Launching Shoonya Bridge..."
# Use screen to keep it running in background if needed, or just run directly
# screen -dmS spidy_shoonya python3 shoonya_server.py

python3 shoonya_server.py
