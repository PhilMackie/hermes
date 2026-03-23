#!/usr/bin/env python3
"""
Run Mimiran CSV import from the command line.
Usage: python scripts/import_mimiran.py [path/to/file.csv]
"""
import sys
import os

# Add parent dir to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daemons.contacts import init_schema
from daemons.importer import import_csv
import config

def main():
    init_schema()

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Default: bundled Mimiran export in project root
        filepath = str(config.BASE_DIR / "Mimiran Export - mimiran-contact-details-20240615 (1).csv")

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    print(f"Importing from: {filepath}")
    result = import_csv(filepath)
    print(f"Imported: {result['imported']}")
    print(f"Skipped:  {result['skipped']}")
    if result['errors']:
        print(f"Errors ({len(result['errors'])}):")
        for e in result['errors']:
            print(f"  {e}")

if __name__ == "__main__":
    main()
