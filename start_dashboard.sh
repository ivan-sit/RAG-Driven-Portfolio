#!/bin/bash

echo "🚀 Starting Investment Portfolio Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run the setup first."
    exit 1
fi

# Activate virtual environment and start API server
echo "📡 Starting API server on http://localhost:8000"
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start web server for dashboard
echo "🌐 Starting web dashboard on http://localhost:8080"
python3 -m http.server 8080 &
WEB_PID=$!

echo ""
echo "✅ Investment Portfolio Dashboard is now running!"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo "🔌 API: http://localhost:8000"
echo ""
echo "📈 Available API endpoints:"
echo "   • GET /fetchInvestmentIdeas - Investment recommendations"
echo "   • GET /fetchSummaries - Industry summaries"
echo "   • GET /stats - System statistics"
echo "   • GET /health - Health check"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $API_PID 2>/dev/null
    kill $WEB_PID 2>/dev/null
    exit 0
}

# Set up signal handler
trap cleanup SIGINT SIGTERM

# Wait for user to stop
wait