#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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
Generic Chunker - Fallback plugin for unsupported document types.

Implements a layered chunking strategy:
1. Filter: Remove ignored block types (footer, seal)
2. Boundary: Identify chunk boundaries (header blocks)
3. Merge: Combine consecutive text blocks
4. Size Control: Split chunks that exceed max size
"""

import logging
from typing import List, Any

from .base import Chunk, DocumentPlugin
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


# Block types to filter out (not included in chunks)
IGNORED_BLOCK_TYPES = {
    BlockType.FOOTER,
    BlockType.SEAL,
}

# Block types that should be preserved as standalone chunks
PRESERVED_BLOCK_TYPES = {
    BlockType.TABLE,
}

# Block types that can be merged together
MERGEABLE_BLOCK_TYPES = {
    BlockType.PARAGRAPH,
    BlockType.QA_PAIR,
    BlockType.LIST,
}

# Maximum chunk size in characters
MAX_CHUNK_SIZE = 1500
# Target minimum chunk size
MIN_CHUNK_SIZE = 50


class GenericChunker(DocumentPlugin):
    """Generic chunker for unsupported document types."""

    @property
    def doc_type(self) -> str:
        return "*"  # Wildcard - handles all types

    @property
    def priority(self) -> int:
        return 1000  # Lowest priority - used as fallback

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into chunks using layered strategy.

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects
        """
        if not blocks:
            return []

        chunks = []
        current_chunk_blocks: List[UniversalBlock] = []
        current_text = ""

        for block in blocks:
            # Step 1: Filter ignored blocks
            if block.block_type in IGNORED_BLOCK_TYPES:
                continue

            # Step 2: Handle preserved blocks (table)
            if block.block_type in PRESERVED_BLOCK_TYPES:
                # Flush current accumulated blocks first
                if current_chunk_blocks:
                    chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                    if chunk:
                        chunks.append(chunk)
                    current_chunk_blocks = []
                    current_text = ""

                # Create standalone chunk for preserved block
                chunk = self._create_chunk([block], block.text, chunk_type="table")
                if chunk:
                    chunks.append(chunk)
                continue

            # Step 3: Check for boundary (HEADER acts as section marker)
            if block.block_type == BlockType.HEADER and current_chunk_blocks:
                # Flush current chunk and start new one
                chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                if chunk:
                    chunks.append(chunk)
                current_chunk_blocks = []
                current_text = ""

            # Step 4: Accumulate text (only mergeable types)
            if block.block_type not in MERGEABLE_BLOCK_TYPES and block.block_type != BlockType.HEADER:
                # Non-mergeable, non-header, non-preserved block - skip
                continue

            block_text = block.text.strip()
            if not block_text:
                continue

            # Check size limit
            if len(current_text) + len(block_text) + 1 > MAX_CHUNK_SIZE:
                # Flush current chunk
                if current_chunk_blocks:
                    chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
                    if chunk:
                        chunks.append(chunk)
                    current_chunk_blocks = []
                    current_text = ""

                # If single block exceeds max size, split it
                if len(block_text) > MAX_CHUNK_SIZE:
                    split_chunks = self._split_oversized_block(block, block_text)
                    chunks.extend(split_chunks)
                    continue

            current_chunk_blocks.append(block)
            current_text = current_text + "\n" + block_text if current_text else block_text

        # Flush remaining blocks
        if current_chunk_blocks:
            chunk = self._create_chunk(current_chunk_blocks, current_text.strip())
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        chunk_type: str = "paragraph"
    ) -> Chunk | None:
        """Create a chunk from a list of blocks."""
        if not blocks or not text:
            return None

        # Skip if text too short
        if len(text) < MIN_CHUNK_SIZE:
            return None

        # Calculate page range and bbox union
        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]  # Convert to 1-indexed

        # Calculate bbox union
        x0 = min(b.bbox[0] for b in blocks)
        y0 = min(b.bbox[1] for b in blocks)
        x1 = max(b.bbox[2] for b in blocks)
        y1 = max(b.bbox[3] for b in blocks)

        # Create block refs
        block_refs = [
            {"page_index": b.page_no, "block_id": str(id(b))}
            for b in blocks
        ]

        return Chunk(
            case_id="",  # Will be filled by caller
            doc_id="",   # Will be filled by caller
            doc_type="", # Will be filled by caller
            chunk_id="", # Will be filled by caller
            chunk_type=chunk_type,
            text=text,
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata={"is_generic_chunked": True},
        )

    def _split_oversized_block(
        self,
        block: UniversalBlock,
        text: str
    ) -> List[Chunk]:
        """
        Split a block that exceeds MAX_CHUNK_SIZE into smaller chunks.

        For Chinese/Japanese/Korean text without spaces, splits at fixed intervals.
        For text with spaces, tries to break at word boundaries.

        Args:
            block: The oversized block
            text: The text content to split

        Returns:
            List of Chunk objects from the split
        """
        chunks = []
        text_len = len(text)
        target_size = MAX_CHUNK_SIZE - 10  # Leave some margin

        # Simple character-based splitting
        # For better results, could use sentence boundaries or semantic splitting
        start = 0
        part_index = 0

        while start < text_len:
            end = min(start + target_size, text_len)
            part = text[start:end]

            # Try to find a good break point (period, newline) within the last 100 chars
            if end < text_len:
                # Look for sentence boundaries
                last_period = part.rfind('。')
                last_newline = part.rfind('\n')
                last_question = part.rfind('？')
                last_exclaim = part.rfind('！')

                # Find the best break point
                break_point = max(last_period, last_newline, last_question, last_exclaim)

                if break_point > target_size // 2:
                    # Found a good break point in the second half
                    part = part[:break_point + 1]
                    end = start + break_point + 1

            if len(part) >= MIN_CHUNK_SIZE:
                chunk = Chunk(
                    case_id="",
                    doc_id="",
                    doc_type="",
                    chunk_id="",
                    chunk_type="paragraph",
                    text=part,
                    page_range=[block.page_no + 1, block.page_no + 1],
                    bbox_union=list(block.bbox),
                    block_refs=[{"page_index": block.page_no, "block_id": str(id(block))}],
                    metadata={"is_generic_chunked": True, "split_part": True, "split_index": part_index},
                )
                chunks.append(chunk)
                part_index += 1

            start = end

        return chunks
