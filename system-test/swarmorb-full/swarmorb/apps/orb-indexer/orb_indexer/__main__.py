"""
SwarmOrb Indexer CLI

Usage:
    python3 -m orb_indexer --audit-dir ./audit --out-dir ./orb
"""

import argparse
import sys
from pathlib import Path

from .indexer import build_index, write_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SwarmOrb Indexer - Build index.json from audit epochs"
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=Path("./audit"),
        help="Path to audit directory containing epoch-* folders (default: ./audit)"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("./orb"),
        help="Output directory for index.json (default: ./orb)"
    )
    parser.add_argument(
        "--coordinator",
        type=str,
        default="swarmos.eth",
        help="Coordinator ENS name (default: swarmos.eth)"
    )
    
    args = parser.parse_args()
    
    try:
        # Build index
        index = build_index(args.audit_dir, args.coordinator)
        
        # Write output
        output_path = args.out_dir / "index.json"
        write_index(index, output_path)
        
        print("\n✓ Index generated successfully")
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
