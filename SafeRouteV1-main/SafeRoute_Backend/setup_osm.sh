#!/bin/bash
# SafeRoute Real Road Network System - Quick Start Script
# =====================================================

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     SafeRoute OSM Road Network System - Quick Start            ║"
echo "║     Real Hyderabad road network from OpenStreetMap            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Backend directory: $BACKEND_DIR"
echo ""

# Step 1: Check Python
echo "━━━ Step 1: Checking Python ━━━"
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Install it first."
    exit 1
fi
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYTHON_VERSION found"
echo ""

# Step 2: Check/Create virtual environment
echo "━━━ Step 2: Virtual Environment ━━━"
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$BACKEND_DIR/venv"
fi
source "$BACKEND_DIR/venv/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Step 3: Install dependencies
echo "━━━ Step 3: Installing Dependencies ━━━"
echo "This may take 2-3 minutes..."
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"
echo "✓ Dependencies installed"
echo ""

# Step 4: Generate road network
echo "━━━ Step 4: Generating Road Network ━━━"
echo "This downloads from OpenStreetMap and may take 2-5 minutes..."
echo "Location: Gachibowli, Hyderabad"
echo "Radius: 5 km"
echo ""
cd "$BACKEND_DIR"
python3 generate_graph.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Road network generation failed."
    echo "See error messages above."
    exit 1
fi

echo ""
echo "✓ Road network generated successfully!"
echo ""

# Step 5: Verify files
echo "━━━ Step 5: Verifying Generated Files ━━━"
FILES=(
    "data/gachibowli_junctions.json"
    "data/gachibowli_edges.json"
    "data/gachibowli_road_graph.json"
    "data/gachibowli_complete.json"
)

for file in "${FILES[@]}"; do
    if [ -f "$BACKEND_DIR/$file" ]; then
        SIZE=$(ls -lh "$BACKEND_DIR/$file" | awk '{print $5}')
        echo "  ✓ $file ($SIZE)"
    else
        echo "  ❌ $file NOT FOUND"
    fi
done
echo ""

# Step 6: Show next steps
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ Setup Complete!                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

echo "NEXT STEPS:"
echo ""
echo "1. Start the backend server:"
echo "   cd $BACKEND_DIR"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""

echo "2. In another terminal, test the routing endpoints:"
echo ""
echo "   # Safest route"
echo "   curl -X POST http://localhost:8000/routes/osm/safest \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"start\": {\"lat\": 17.440, \"lng\": 78.345}, \"end\": {\"lat\": 17.448, \"lng\": 78.355}}'"
echo ""

echo "   # Shortest route"
echo "   curl -X POST http://localhost:8000/routes/osm/shortest \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"start\": {\"lat\": 17.440, \"lng\": 78.345}, \"end\": {\"lat\": 17.448, \"lng\": 78.355}}'"
echo ""

echo "   # Balanced route (60% safety, 40% distance)"
echo "   curl -X POST 'http://localhost:8000/routes/osm/balanced?safety_weight=0.6' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"start\": {\"lat\": 17.440, \"lng\": 78.345}, \"end\": {\"lat\": 17.448, \"lng\": 78.355}}'"
echo ""

echo "DOCUMENTATION:"
echo "  • ROUTING_GUIDE.md         - Complete usage guide"
echo "  • JSON_STRUCTURE.md        - Data format documentation"
echo "  • OSM_SYSTEM_SUMMARY.md    - Architecture overview"
echo "  • IMPLEMENTATION_CHECKLIST.md - Status and checklist"
echo ""

echo "Ready to deploy SafeRoute with real Hyderabad road network! 🚀"
