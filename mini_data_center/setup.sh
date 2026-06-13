#!/bin/bash

echo "🚀 Starting Mini Data Center setup..."

echo "📦 Creating virtual environment..."
python3 -m venv --system-site-packages my_iot_env

echo "🔄 Activating environment and installing packages..."
source my_iot_env/bin/activate
pip install pipreqs
pip install -r requirements.txt

echo "✅ Setup complete!"
echo "👉 To start using your project, just type: source my_iot_env/bin/activate"
