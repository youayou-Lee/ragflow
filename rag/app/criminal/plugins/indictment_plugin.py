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
Indictment Opinion Plugin - Handles prosecution opinion documents.

Implements section-based chunking with key trigger phrases.
"""

import logging
from typing import List

from .base import Chunk, DocumentPlugin, plugin_registry
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


# Section trigger phrases (start of major sections)
SECTION_TRIGGERS = [
    "经依法侦查查明",
    "认定上述犯罪事实的证据如下",
    "综上所述",
    "此致",
    "检察员",
]

# Maximum chunk size
MAX_CHUNK_SIZE = 1500
MIN_CHUNK_SIZE = 50


@plugin_registry.register("indictment_opinion")
class IndictmentPlugin(DocumentPlugin):
    """Plugin for handling indictment opinion documents."""

    @property
    def doc_type(self) -> str:
        return "indictment_opinion"

    @property
    def priority(self) -> int:
        return 10

    def transform(self, blocks: List[UniversalBlock]) -> List[Chunk]:
        """
        Transform blocks into section and paragraph chunks.

        Strategy:
        1. Detect section boundaries using trigger phrases
        2. Within sections, merge consecutive paragraphs
        3. Split if chunk exceeds max size

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects
        """
        if not blocks:
            return []

        chunks = []
        current_section_blocks: List[UniversalBlock] = []
        current_text = ""
        current_section_title = ""

        for block in blocks:
            text = block.text.strip()

            # Skip empty blocks
            if not text:
                continue

            # Check for section trigger
            is_section_start = any(text.startswith(trigger) for trigger in SECTION_TRIGGERS)

            if is_section_start:
                # Flush current chunk
                if current_section_blocks and current_text:
                    chunk = self._create_chunk(
                        current_section_blocks,
                        current_text,
                        "section" if current_section_title else "paragraph",
                        current_section_title
                    )
                    if chunk:
                        chunks.append(chunk)

                # Start new section
                current_section_blocks = [block]
                current_text = text
                current_section_title = text[:50]  # Use first 50 chars as title
                continue

            # Check size limit
            if len(current_text) + len(text) + 1 > MAX_CHUNK_SIZE:
                # Flush current chunk
                if current_section_blocks and current_text:
                    chunk = self._create_chunk(
                        current_section_blocks,
                        current_text,
                        "paragraph",
                        current_section_title
                    )
                    if chunk:
                        chunks.append(chunk)
                current_section_blocks = []
                current_text = ""

            # Accumulate
            current_section_blocks.append(block)
            current_text = current_text + "\n" + text if current_text else text

        # Flush remaining
        if current_section_blocks and current_text:
            chunk = self._create_chunk(
                current_section_blocks,
                current_text,
                "section" if current_section_title else "paragraph",
                current_section_title
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        chunk_type: str,
        section_title: str = ""
    ) -> Chunk | None:
        """Create a chunk from blocks."""
        if not blocks or not text:
            return None

        if len(text) < MIN_CHUNK_SIZE:
            return None

        pages = sorted(set(b.page_no for b in blocks))
        page_range = [pages[0] + 1, pages[-1] + 1]

        x0 = min(b.bbox[0] for b in blocks)
        y0 = min(b.bbox[1] for b in blocks)
        x1 = max(b.bbox[2] for b in blocks)
        y1 = max(b.bbox[3] for b in blocks)

        block_refs = [
            {"page_index": b.page_no, "block_id": str(id(b))}
            for b in blocks
        ]

        metadata = {}
        if section_title:
            metadata["section_title"] = section_title

        return Chunk(
            case_id="",
            doc_id="",
            doc_type=self.doc_type,
            chunk_id="",
            chunk_type=chunk_type,
            text=text.strip(),
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata=metadata,
        )
