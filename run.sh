#!/bin/bash

# Finn.no Deal Finder - Quick Start Script
# ==========================================

echo "🔍 Finn.no Deal Finder Pro"
echo "=========================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1)
echo "📍 Python: $python_version"

# Create data directory if it doesn't exist
mkdir -p data

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt --quiet

# Start the application
echo ""
echo "🚀 Starting Finn.no Deal Finder..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Open your browser at: http://localhost:5000"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python app.py
