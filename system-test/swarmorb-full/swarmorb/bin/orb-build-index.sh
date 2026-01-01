#!/bin/bash
# orb-build-index.sh
# Runs the indexer and copies orb/*.json into orb-ui public folder for dev preview

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

AUDIT_DIR="${1:-$ROOT_DIR/sample_data/audit}"
OUT_DIR="${2:-$ROOT_DIR/sample_data/orb}"
UI_DATA_DIR="$ROOT_DIR/apps/orb-ui/public/data"

echo "╔══════════════════════════════════════════╗"
echo "║       SwarmOrb Index Builder             ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if audit dir exists
if [ ! -d "$AUDIT_DIR" ]; then
    echo "Error: Audit directory not found: $AUDIT_DIR"
    exit 1
fi

# Run indexer
echo "→ Running indexer..."
cd "$ROOT_DIR/apps/orb-indexer"
python3 -m orb_indexer --audit-dir "$AUDIT_DIR" --out-dir "$OUT_DIR"

# Copy to UI public folder
echo ""
echo "→ Copying data to UI..."
mkdir -p "$UI_DATA_DIR/orb"
mkdir -p "$UI_DATA_DIR/audit"

# Copy orb/*.json
cp "$OUT_DIR"/*.json "$UI_DATA_DIR/orb/"

# Copy audit epochs
for epoch_dir in "$AUDIT_DIR"/epoch-*; do
    if [ -d "$epoch_dir" ]; then
        epoch_name=$(basename "$epoch_dir")
        mkdir -p "$UI_DATA_DIR/audit/$epoch_name"
        cp "$epoch_dir"/* "$UI_DATA_DIR/audit/$epoch_name/"
        echo "  Copied: $epoch_name"
    fi
done

echo ""
echo "✓ Index built and data copied to UI"
echo "  UI data: $UI_DATA_DIR"
echo ""
echo "Run 'make dev' to preview the UI"
