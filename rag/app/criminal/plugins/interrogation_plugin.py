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
Interrogation Record Plugin - Handles police interrogation transcripts.

Output structure:
1. header_info chunk: All content from document start to first Q/A pair
2. qa_pair chunks: Each Q/A pair as a separate chunk
"""

import logging
from typing import List

from .base import Chunk, DocumentPlugin, plugin_registry
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


@plugin_registry.register("interrogation_record")
class InterrogationPlugin(DocumentPlugin):
    """Plugin for handling interrogation record documents."""

    @property
    def doc_type(self) -> str:
        return "interrogation_record"

    @property
    def priority(self) -> int:
        return 10  # High priority

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into header_info and qa_pair chunks.

        Output structure:
        1. header_info (1 chunk): All content before the first Q/A pair
           - Document title, time, location, participants, rights notice, etc.
        2. qa_pair (N chunks): Each Q/A pair as a separate chunk

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects: [header_info, qa_pair, qa_pair, ...]
        """
        if not blocks:
            return []

        chunks = []

        # Phase 1: Collect header_info blocks (before first "问：")
        header_blocks: List[UniversalBlock] = []
        first_qa_found = False

        for block in blocks:
            text = block.text.strip()

            # Skip empty blocks
            if not text:
                continue

            # Check if this starts a Q/A section
            if text.startswith(("问：", "问:")):
                first_qa_found = True
                break

            # Collect header info blocks
            header_blocks.append(block)

        # Create header_info chunk if there's content
        if header_blocks:
            header_chunk = self._create_chunk(
                header_blocks,
                "header_info"
            )
            if header_chunk:
                chunks.append(header_chunk)

        # Phase 2: Process Q/A pairs
        if not first_qa_found:
            return chunks

        # Find the index where Q/A section starts
        qa_start_idx = 0
        for i, block in enumerate(blocks):
            text = block.text.strip()
            if text.startswith(("问：", "问:")):
                qa_start_idx = i
                break

        # Process Q/A pairs from qa_start_idx
        current_qa_blocks: List[UniversalBlock] = []
        current_qa_text = ""

        for block in blocks[qa_start_idx:]:
            text = block.text.strip()

            # Skip empty blocks
            if not text:
                continue

            # Check if this is a new question
            if text.startswith(("问：", "问:")):
                # Flush previous QA pair
                if current_qa_blocks:
                    chunk = self._create_qa_chunk(current_qa_blocks, current_qa_text)
                    if chunk:
                        chunks.append(chunk)

                # Start new QA pair
                current_qa_blocks = [block]
                current_qa_text = text

            elif text.startswith(("答：", "答:")):
                # Add answer to current QA pair
                current_qa_blocks.append(block)
                current_qa_text += "\n" + text

            elif current_qa_blocks:
                # Continuation of previous answer
                current_qa_blocks.append(block)
                current_qa_text += "\n" + text

        # Flush final QA pair
        if current_qa_blocks:
            chunk = self._create_qa_chunk(current_qa_blocks, current_qa_text)
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        chunk_type: str,
        text_override: str = None
    ) -> Chunk | None:
        """Create a chunk from blocks."""
        if not blocks:
            return None

        # Build text from blocks if not provided
        if text_override:
            text = text_override
        else:
            text_parts = []
            for b in blocks:
                t = b.text.strip()
                if t:
                    text_parts.append(t)
            text = "\n".join(text_parts)

        if not text:
            return None

        # Build raw_text with position tags (for pdf_parser.crop)
        raw_text_parts = []
        for b in blocks:
            if b.raw_text:
                raw_text_parts.append(b.raw_text)
            else:
                # Fallback: construct from text and position
                raw_text_parts.append(b.text)
        raw_text = "\n".join(raw_text_parts)

        # Calculate page range
        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]

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
            case_id="",
            doc_id="",
            doc_type=self.doc_type,
            chunk_id="",
            chunk_type=chunk_type,
            text=text.strip(),
            raw_text=raw_text,
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata={},
        )

    def _create_qa_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str
    ) -> Chunk | None:
        """Create a qa_pair chunk from blocks."""
        return self._create_chunk(blocks, "qa_pair", text)
