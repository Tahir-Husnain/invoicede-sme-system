#!/bin/bash
# SME Invoice System — Startup Script
# =====================================

cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║         InvoiceDE — SME Invoice System               ║"
echo "║         Germany-focused · FastAPI · SQLite           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt --break-system-packages -q
fi

# Fix bcrypt version if needed
pip install bcrypt==4.0.1 --break-system-packages -q 2>/dev/null

echo "✅ Dependencies ready"
echo ""
echo "🚀 Starting server at http://localhost:8000"
echo ""
echo "   Demo login:  username = demo"
echo "                password = demo1234"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
