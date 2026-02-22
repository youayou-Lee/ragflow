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
Indictment document parser plugin (起诉意见书解析插件).

Layer B plugin that processes UniversalBlock sequences from indictment documents
and produces semantic chunks for indexing.
"""

import re
from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


# Section trigger phrases (in order of typical appearance)
SECTION_TRIGGERS = [
    r"经依法侦查查明",
    r"经依法审查查明",
    r"现查明",
    r"认定上述犯罪事实的证据如下",
    r"上述犯罪事实(?:，|，\s*)有(?:以下|下列)证据(?:予以)?证实",
    r"综上所述",
    r"本院认为",
    r"此致",
]

SECTION_TRIGGER_PATTERN = re.compile("|".join(f"({t})" for t in SECTION_TRIGGERS))

# Maximum length for section before splitting
MAX_SECTION_LENGTH = 800


class IndictmentPlugin(ParserPlugin):
    """
    Indictment document parser plugin (起诉意见书解析插件).

    Processes UniversalBlock sequences from indictment documents
    and produces semantic chunks for indexing.
    """

    @property
    def doc_type(self) -> str:
        return "indictment"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process blocks into chunks.

        1. Find section boundaries based on trigger phrases
        2. Build section chunks (split long sections into paragraphs)
        """
        if not blocks:
            return []

        # Find section boundaries
        sections = self._find_section_boundaries(blocks)

        # Build chunks from sections
        chunks = []
        for start_idx, end_idx, trigger in sections:
            section_blocks = blocks[start_idx:end_idx]
            section_chunks = self._build_section_chunks(section_blocks, doc, trigger)
            chunks.extend(section_chunks)

        return chunks

    def _find_section_boundaries(self, blocks: List[UniversalBlock]) -> List[tuple]:
        """Find section boundaries based on trigger phrases."""
        sections = []
        current_start = 0
        current_trigger = "header"

        for i, block in enumerate(blocks):
            match = SECTION_TRIGGER_PATTERN.search(block.text)
            if match:
                if i > current_start:
                    sections.append((current_start, i, current_trigger))
                current_start = i
                current_trigger = match.group(0)

        if current_start < len(blocks):
            sections.append((current_start, len(blocks), current_trigger))

        return sections

    def _build_section_chunks(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Build chunks from a section."""
        # Combine text for length check
        total_length = sum(len(b.text) for b in blocks)

        if total_length > MAX_SECTION_LENGTH:
            return self._split_into_paragraphs(blocks, doc, trigger)
        else:
            return [self._make_section_chunk(blocks, doc, trigger, "section")]

    def _make_section_chunk(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str,
        chunk_type: str
    ) -> dict:
        """Create a section or paragraph chunk."""
        d = deepcopy(doc)
        d["chunk_type"] = chunk_type
        d["section_trigger"] = trigger

        # Combine text
        text = "\n".join(b.text for b in blocks)
        d["content_with_weight"] = text

        # Use first block's position
        d["page_no"] = blocks[0].page_no
        d["bbox"] = list(blocks[0].bbox)

        # Merge entities
        entities = self._merge_entities(blocks)
        if entities:
            d["entities"] = entities

        return d

    def _split_into_paragraphs(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        trigger: str
    ) -> List[dict]:
        """Split a long section into paragraph chunks."""
        chunks = []
        current_blocks = []
        current_length = 0

        for block in blocks:
            block_length = len(block.text)

            if current_length + block_length > MAX_SECTION_LENGTH and current_blocks:
                chunk = self._make_section_chunk(
                    current_blocks, doc, trigger, "paragraph"
                )
                chunks.append(chunk)
                current_blocks = [block]
                current_length = block_length
            else:
                current_blocks.append(block)
                current_length += block_length

        if current_blocks:
            chunk_type = "paragraph" if chunks else "section"
            chunk = self._make_section_chunk(current_blocks, doc, trigger, chunk_type)
            chunks.append(chunk)

        return chunks

    def _merge_entities(self, blocks: List[UniversalBlock]) -> dict:
        """Merge entities from multiple blocks."""
        merged = {"amounts": [], "dates": []}
        for block in blocks:
            if block.entities:
                merged["amounts"].extend(block.entities.get("amounts", []))
                merged["dates"].extend(block.entities.get("dates", []))
        merged["amounts"] = list(set(merged["amounts"]))
        merged["dates"] = list(set(merged["dates"]))
        return merged if (merged["amounts"] or merged["dates"]) else {}
