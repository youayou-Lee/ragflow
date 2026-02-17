#!/usr/bin/env python3
"""
PDF to Positioned Text Converter

Converts PDF documents to structured JSON with text positions using PaddleOCR API.
The output can be used to generate benchmark question banks with precise location tags.

Usage:
    uv run python pdf_to_positioned_text.py <pdf_path> [--output <output_dir>] [--save-json]

Examples:
    # Parse PDF and save JSON to benchmark directory
    uv run python pdf_to_positioned_text.py indictment.pdf --output benchmark/起诉意见书/案件名称/原始数据 --save-json

    # Parse PDF and print blocks to stdout
    uv run python pdf_to_positioned_text.py indictment.pdf
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from deepdoc.parser.paddleocr_parser import PaddleOCRParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Default PaddleOCR configuration (can be overridden via env vars or CLI args)
DEFAULT_PADDLEOCR_API_URL = "https://lbxcbea0u3qdpcpe.aistudio-app.com/layout-parsing"
DEFAULT_PADDLEOCR_ACCESS_TOKEN = "5d5004a26c83d0d9451c754d016a55494a0b3955"

ZOOMIN = 2  # Same as PaddleOCRParser._ZOOMIN


@dataclass
class TextBlock:
    """A text block with content and position information."""

    page: int  # 1-indexed page number
    block_id: int
    label: str
    content: str
    bbox: list[int]  # [x0, y0, x1, y1] original coordinates
    location_tag: str  # Formatted position tag
    order: Optional[int] = None


@dataclass
class PageInfo:
    """Page dimension information."""

    page_number: int
    width: int
    height: int


@dataclass
class PositionedDocument:
    """A document with positioned text blocks."""

    source_file: str
    parsed_at: str
    page_count: int
    pages: list[PageInfo]
    blocks: list[TextBlock]
    raw_response: Optional[dict[str, Any]] = None


def bbox_to_location_tag(page: int, bbox: list[int]) -> str:
    """Convert bbox coordinates to location tag format.

    Args:
        page: 1-indexed page number
        bbox: [x0, y0, x1, y1] original coordinates from PaddleOCR

    Returns:
        Location tag string: @@{page}\\t{x0 // 2}\\t{x1 // 2}\\t{y0 // 2}\\t{y1 // 2}##
    """
    x0, y0, x1, y1 = bbox
    return f"@@{page}\t{x0 // ZOOMIN}\t{x1 // ZOOMIN}\t{y0 // ZOOMIN}\t{y1 // ZOOMIN}##"


def parse_json_to_blocks(json_path: Path) -> PositionedDocument:
    """Parse existing PaddleOCR JSON response and extract text blocks with positions.

    Args:
        json_path: Path to paddleocr_response.json file

    Returns:
        PositionedDocument with all text blocks and their positions
    """
    logger.info(f"Loading JSON: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        response = json.load(f)

    # Handle wrapped response format
    if "result" in response:
        result = response["result"]
    else:
        result = response

    # Extract document info
    data_info = result.get("dataInfo", {})
    layout_results = result.get("layoutParsingResults", [])

    pages = []
    for i, page_info in enumerate(data_info.get("pages", []), start=1):
        pages.append(
            PageInfo(
                page_number=i,
                width=page_info.get("width", 0),
                height=page_info.get("height", 0),
            )
        )

    # Extract blocks
    blocks = []
    for page_idx, layout_result in enumerate(layout_results):
        pruned_result = layout_result.get("prunedResult", {})
        parsing_res_list = pruned_result.get("parsing_res_list", [])

        for block in parsing_res_list:
            block_content = block.get("block_content", "").strip()
            if not block_content:
                continue

            block_id = block.get("block_id", 0)
            label = block.get("block_label", "")
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            order = block.get("block_order")

            # Convert to location tag
            page = page_idx + 1  # 1-indexed
            location_tag = bbox_to_location_tag(page, bbox)

            blocks.append(
                TextBlock(
                    page=page,
                    block_id=block_id,
                    label=label,
                    content=block_content,
                    bbox=bbox,
                    location_tag=location_tag,
                    order=order,
                )
            )

    return PositionedDocument(
        source_file=str(json_path),
        parsed_at=datetime.now().isoformat(),
        page_count=data_info.get("numPages", len(pages)),
        pages=pages,
        blocks=blocks,
        raw_response=result,
    )


def parse_pdf_to_blocks(
    pdf_path: Path,
    api_url: Optional[str] = None,
    access_token: Optional[str] = None,
) -> PositionedDocument:
    """Parse PDF and extract text blocks with positions.

    Args:
        pdf_path: Path to PDF file
        api_url: PaddleOCR API URL (defaults to DEFAULT_PADDLEOCR_API_URL)
        access_token: PaddleOCR access token (defaults to DEFAULT_PADDLEOCR_ACCESS_TOKEN)

    Returns:
        PositionedDocument with all text blocks and their positions
    """
    # Use provided values, then env vars, then defaults
    final_api_url = api_url or os.getenv("PADDLEOCR_API_URL") or DEFAULT_PADDLEOCR_API_URL
    final_access_token = access_token or os.getenv("PADDLEOCR_ACCESS_TOKEN") or DEFAULT_PADDLEOCR_ACCESS_TOKEN

    # Initialize parser
    parser = PaddleOCRParser(
        api_url=final_api_url,
        access_token=final_access_token,
    )

    # Check configuration
    ok, reason = parser.check_installation()
    if not ok:
        raise RuntimeError(f"PaddleOCR not configured: {reason}")

    logger.info(f"Parsing PDF: {pdf_path}")

    # Read file and send request directly to get raw response
    data_bytes = pdf_path.read_bytes()

    # Build minimal config for API call
    from deepdoc.parser.paddleocr_parser import PaddleOCRConfig

    config = PaddleOCRConfig(
        api_url=parser.api_url,
        access_token=parser.access_token,
        algorithm=parser.algorithm,
    )

    # Send request and get raw result
    result = parser._send_request(data_bytes, config, callback=lambda p, m: logger.info(f"[{p:.0%}] {m}"))

    # Extract document info
    data_info = result.get("dataInfo", {})
    layout_results = result.get("layoutParsingResults", [])

    pages = []
    for i, page_info in enumerate(data_info.get("pages", []), start=1):
        pages.append(
            PageInfo(
                page_number=i,
                width=page_info.get("width", 0),
                height=page_info.get("height", 0),
            )
        )

    # Extract blocks
    blocks = []
    for page_idx, layout_result in enumerate(layout_results):
        pruned_result = layout_result.get("prunedResult", {})
        parsing_res_list = pruned_result.get("parsing_res_list", [])

        for block in parsing_res_list:
            block_content = block.get("block_content", "").strip()
            if not block_content:
                continue

            block_id = block.get("block_id", 0)
            label = block.get("block_label", "")
            bbox = block.get("block_bbox", [0, 0, 0, 0])
            order = block.get("block_order")

            # Convert to location tag
            page = page_idx + 1  # 1-indexed
            location_tag = bbox_to_location_tag(page, bbox)

            blocks.append(
                TextBlock(
                    page=page,
                    block_id=block_id,
                    label=label,
                    content=block_content,
                    bbox=bbox,
                    location_tag=location_tag,
                    order=order,
                )
            )

    return PositionedDocument(
        source_file=str(pdf_path),
        parsed_at=datetime.now().isoformat(),
        page_count=data_info.get("numPages", len(pages)),
        pages=pages,
        blocks=blocks,
        raw_response=result,
    )


def save_result(doc: PositionedDocument, output_dir: Path, save_raw: bool = True) -> Path:
    """Save parsing result to output directory.

    Args:
        doc: PositionedDocument to save
        output_dir: Directory to save files
        save_raw: Whether to save raw API response

    Returns:
        Path to the saved JSON file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save blocks as simplified JSON
    blocks_file = output_dir / "blocks.json"
    blocks_data = {
        "source_file": doc.source_file,
        "parsed_at": doc.parsed_at,
        "page_count": doc.page_count,
        "pages": [asdict(p) for p in doc.pages],
        "blocks": [asdict(b) for b in doc.blocks],
    }
    with open(blocks_file, "w", encoding="utf-8") as f:
        json.dump(blocks_data, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved blocks to: {blocks_file}")

    # Save raw response if requested
    if save_raw and doc.raw_response:
        raw_file = output_dir / "paddleocr_response.json"
        with open(raw_file, "w", encoding="utf-8") as f:
            json.dump(doc.raw_response, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved raw response to: {raw_file}")

    return blocks_file


def print_blocks(doc: PositionedDocument, show_content: bool = True):
    """Print blocks to stdout in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"Document: {doc.source_file}")
    print(f"Pages: {doc.page_count}")
    print(f"Blocks: {len(doc.blocks)}")
    print(f"{'=' * 60}\n")

    for block in doc.blocks:
        print(f"Page {block.page} | Block {block.block_id} | {block.label}")
        print(f"Location: {block.location_tag}")
        print(f"BBox: {block.bbox}")
        if show_content:
            content = block.content[:200] + "..." if len(block.content) > 200 else block.content
            print(f"Content: {content}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Convert PDF to positioned text blocks using PaddleOCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input_path", type=Path, help="Path to PDF file or paddleocr_response.json")
    parser.add_argument("--output", "-o", type=Path, help="Output directory for JSON files")
    parser.add_argument("--save-json", action="store_true", help="Save JSON output files")
    parser.add_argument("--save-raw", action="store_true", default=True, help="Save raw PaddleOCR response")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress block output to stdout")
    parser.add_argument("--api-url", type=str, help="PaddleOCR API URL (overrides env var)")
    parser.add_argument("--access-token", type=str, help="PaddleOCR access token (overrides env var)")

    args = parser.parse_args()

    if not args.input_path.exists():
        print(f"Error: File not found: {args.input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # Detect input type and parse
        if args.input_path.suffix.lower() == ".json":
            logger.info("Detected JSON input, parsing existing PaddleOCR response")
            doc = parse_json_to_blocks(args.input_path)
        else:
            # Parse PDF via API
            doc = parse_pdf_to_blocks(
                args.input_path,
                api_url=args.api_url,
                access_token=args.access_token,
            )

        # Print blocks unless quiet
        if not args.quiet:
            print_blocks(doc)

        # Save if output directory specified
        if args.output or args.save_json:
            output_dir = args.output or args.input_path.parent / "positioned_output"
            save_result(doc, output_dir, save_raw=args.save_raw)

        # Print summary
        print(f"\nSummary: {len(doc.blocks)} blocks extracted from {doc.page_count} pages")

    except Exception as e:
        logger.error(f"Failed to parse input: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
