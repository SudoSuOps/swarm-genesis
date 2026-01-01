# SwarmOrb Makefile
# Usage:
#   make dev     - Run UI with sample data
#   make build   - Build static export
#   make index   - Regenerate index from audit folder

.PHONY: help dev build index install clean

SHELL := /bin/bash

# Paths
ROOT_DIR := $(shell pwd)
UI_DIR := $(ROOT_DIR)/apps/orb-ui
INDEXER_DIR := $(ROOT_DIR)/apps/orb-indexer
SAMPLE_DATA := $(ROOT_DIR)/sample_data
UI_DATA_DIR := $(UI_DIR)/public/data
DIST_DIR := $(ROOT_DIR)/dist

help:
	@echo "SwarmOrb - Read-only SwarmOS Explorer"
	@echo ""
	@echo "Commands:"
	@echo "  make install  - Install dependencies"
	@echo "  make dev      - Run UI dev server with sample data"
	@echo "  make build    - Build static export to ./dist"
	@echo "  make index    - Regenerate index.json from audit folder"
	@echo "  make clean    - Remove build artifacts"
	@echo ""

# Install dependencies
install:
	@echo "→ Installing UI dependencies..."
	cd $(UI_DIR) && npm install
	@echo "→ Installing indexer dependencies..."
	cd $(INDEXER_DIR) && pip install -e . --break-system-packages
	@echo "✓ Dependencies installed"

# Copy sample data and run dev server
dev: _copy-sample-data
	@echo "→ Starting dev server..."
	cd $(UI_DIR) && npm run dev

# Build static export
build: _copy-sample-data
	@echo "→ Building static export..."
	cd $(UI_DIR) && npm run build
	@echo "→ Copying to dist..."
	rm -rf $(DIST_DIR)
	cp -r $(UI_DIR)/dist $(DIST_DIR)
	@echo ""
	@echo "✓ Build complete: $(DIST_DIR)"
	@echo "  Deploy this folder to IPFS or Cloudflare Pages"

# Regenerate index from audit folder
index:
	@echo "→ Running indexer..."
	cd $(INDEXER_DIR) && python3 -m orb_indexer \
		--audit-dir $(SAMPLE_DATA)/audit \
		--out-dir $(SAMPLE_DATA)/orb
	@echo "→ Copying to UI..."
	$(MAKE) _copy-sample-data
	@echo "✓ Index regenerated"

# Internal: copy sample data to UI public folder
_copy-sample-data:
	@echo "→ Copying sample data to UI..."
	@mkdir -p $(UI_DATA_DIR)/orb
	@mkdir -p $(UI_DATA_DIR)/audit
	@cp -r $(SAMPLE_DATA)/orb/* $(UI_DATA_DIR)/orb/ 2>/dev/null || true
	@cp -r $(SAMPLE_DATA)/audit/* $(UI_DATA_DIR)/audit/ 2>/dev/null || true

# Clean build artifacts
clean:
	rm -rf $(DIST_DIR)
	rm -rf $(UI_DIR)/dist
	rm -rf $(UI_DATA_DIR)
	rm -rf $(UI_DIR)/node_modules/.cache
	@echo "✓ Cleaned"

# Deploy to IPFS (requires ipfs-deploy or similar)
deploy-ipfs: build
	@echo "→ Deploying to IPFS..."
	@echo "  Run: ipfs add -r $(DIST_DIR)"
	@echo "  Or use: npx ipfs-deploy $(DIST_DIR)"
