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

Recognizes Q/A patterns and groups them into qa_pair chunks.
"""

import logging
from typing import List

from .base import Chunk, DocumentPlugin
from rag.app.naive import UniversalBlock, BlockType


logger = logging.getLogger(__name__)


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
        Transform blocks into qa_pair chunks.

        Grouping logic:
        - Each "问：" starts a new QA pair
        - Following "答：" blocks are merged with the question
        - Multiple "答：" blocks are concatenated

        Args:
            blocks: List of UniversalBlock from Layer A

        Returns:
            List of Chunk objects with chunk_type="qa_pair"
        """
        if not blocks:
            return []

        chunks = []
        current_qa_blocks: List[UniversalBlock] = []
        current_qa_text = ""
        header_text = ""

        for block in blocks:
            text = block.text.strip()

            # Handle header blocks
            if block.block_type == BlockType.HEADER:
                header_text = text
                continue

            # Skip empty blocks
            if not text:
                continue

            # Check if this is a new question
            if text.startswith(("问：", "问:")):
                # Flush previous QA pair
                if current_qa_blocks:
                    chunk = self._create_qa_chunk(
                        current_qa_blocks,
                        current_qa_text,
                        header_text
                    )
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
            chunk = self._create_qa_chunk(
                current_qa_blocks,
                current_qa_text,
                header_text
            )
            if chunk:
                chunks.append(chunk)

        return chunks

    def _create_qa_chunk(
        self,
        blocks: List[UniversalBlock],
        text: str,
        header: str = ""
    ) -> Chunk | None:
        """Create a qa_pair chunk from blocks."""
        if not blocks or not text:
            return None

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

        metadata = {}
        if header:
            metadata["doc_title"] = header

        return Chunk(
            case_id="",
            doc_id="",
            doc_type=self.doc_type,
            chunk_id="",
            chunk_type="qa_pair",
            text=text.strip(),
            page_range=page_range,
            bbox_union=[x0, y0, x1, y1],
            block_refs=block_refs,
            metadata=metadata,
        )
