#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Plugin Development Test Tool.

A command-line tool for quickly testing document parsing plugins
without requiring the full backend environment.

Usage:
    uv run python test/test_plugin_dev.py <pdf_path> --doc-type <type> [--json] [--refresh]

Examples:
    # First run (calls OCR API, caches result)
    uv run python test/test_plugin_dev.py benchmark/讯问笔录/陈明飞诈骗案/原始数据/讯问笔录_sample.pdf --doc-type interrogation_record

    # Subsequent runs (uses cache)
    uv run python test/test_plugin_dev.py benchmark/讯问笔录/陈明飞诈骗案/原始数据/讯问笔录_sample.pdf --doc-type interrogation_record

    # JSON output
    uv run python test/test_plugin_dev.py <pdf_path> --doc-type <type> --json

    # Force refresh cache
    uv run python test/test_plugin_dev.py <pdf_path> --doc-type <type> --refresh
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Test document parsing plugins quickly with OCR caching",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Supported document types:
  interrogation_record  - 讯问/询问笔录
  indictment_opinion    - 起诉意见书

Examples:
  # Test interrogation record parsing
  uv run python test/test_plugin_dev.py sample.pdf --doc-type interrogation_record

  # Output as JSON for AI parsing
  uv run python test/test_plugin_dev.py sample.pdf --doc-type interrogation_record --json

  # Force refresh OCR cache
  uv run python test/test_plugin_dev.py sample.pdf --doc-type interrogation_record --refresh
"""
    )

    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file to test"
    )

    parser.add_argument(
        "--doc-type",
        type=str,
        required=True,
        help="Document type (e.g., interrogation_record, indictment_opinion)"
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON format"
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh OCR cache by calling API again"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    pdf_path = Path(args.pdf_path)

    # Validate PDF exists
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Lazy imports to avoid loading dependencies for --help
    from deepdoc.parser.paddleocr_parser import PaddleOCRParser
    from rag.app.naive import extract_universal_blocks
    from rag.app.criminal.router import route_to_plugin

    # TODO: Implement the rest of the flow
    print(f"PDF: {pdf_path}")
    print(f"Doc Type: {args.doc_type}")
    print(f"JSON Output: {args.json}")
    print(f"Refresh Cache: {args.refresh}")


if __name__ == "__main__":
    main()
