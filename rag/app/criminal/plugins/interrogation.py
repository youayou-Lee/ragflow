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
Interrogation record parser plugin (讯问笔录解析插件).

Layer B plugin that processes UniversalBlock sequences from interrogation records
and produces semantic chunks for indexing.
"""

import json
import re
from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType
from rag.nlp import add_positions

# Pattern for detecting question start (at beginning or after newline)
# Handles OCR merging multiple lines into one block
QUESTION_START_PATTERN = re.compile(r'(^|\n)\s*问\s*[：:；;]')


class InterrogationPlugin(ParserPlugin):
    """
    Interrogation record parser plugin (讯问笔录解析插件).

    Processes UniversalBlock sequences from interrogation records
    and produces semantic chunks for indexing.
    """

    @property
    def doc_type(self) -> str:
        return "interrogation"

    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process blocks into chunks.

        Structure of interrogation record:
        [basicInfo blocks] [问：...] [答：...] [问：...] [答：...] ...
                            ↑
                      First "问：" position

        Note: "问：" may appear at block start OR after newline within a block
        (due to OCR merging multiple lines into one block).

        1. Find first "问：" position (at start or after newline)
        2. Everything before = basicInfo (single chunk)
        3. Everything after = QA pairs (multiple chunks)
        """
        if not blocks:
            return []

        chunks = []

        # 1. Find first question position
        # Check both startswith and newline-prefixed patterns
        first_q_index = None
        first_q_offset = 0  # Character offset within block if "问：" is not at start

        for i, block in enumerate(blocks):
            text = block.text.strip()
            # Check if block starts with "问："
            if text.startswith(("问：", "问:", "问；", "问;")):
                first_q_index = i
                first_q_offset = 0
                break
            # Check if "问：" appears after newline (OCR merged lines)
            match = QUESTION_START_PATTERN.search(text)
            if match:
                first_q_index = i
                first_q_offset = match.start() if match.group(1) == '\n' else 0
                break

        # 2. Process basicInfo (everything before first "问：")
        if first_q_index is not None:
            if first_q_index > 0:
                # All previous blocks are pure basicInfo
                header_blocks = blocks[:first_q_index]

                # Handle the block containing "问：" - split it if needed
                split_block = blocks[first_q_index]
                if first_q_offset > 0:
                    # Extract basicInfo portion from the split block
                    basicInfo_part = split_block.text[:first_q_offset].strip()
                    if basicInfo_part:
                        # Create a new block for the basicInfo part
                        header_blocks.append(UniversalBlock(
                            block_type=split_block.block_type,
                            text=basicInfo_part,
                            page_no=split_block.page_no,
                            bbox=split_block.bbox,
                        ))

                if header_blocks:
                    header_chunk = self._make_header_chunk(header_blocks, doc)
                    chunks.append(header_chunk)

            # QA section starts from the block containing "问："
            qa_blocks = blocks[first_q_index:]

            # If the first QA block was split, create a new block with only QA portion
            if first_q_offset > 0 and qa_blocks:
                split_block = qa_blocks[0]
                qa_part = split_block.text[first_q_offset:].strip()
                if qa_part:
                    qa_blocks[0] = UniversalBlock(
                        block_type=split_block.block_type,
                        text=qa_part,
                        page_no=split_block.page_no,
                        bbox=split_block.bbox,
                    )
                else:
                    qa_blocks = qa_blocks[1:]  # Remove empty block
        else:
            # No "问：" found - all content is basicInfo
            header_chunk = self._make_header_chunk(blocks, doc)
            chunks.append(header_chunk)
            qa_blocks = []

        # 3. Process QA pairs (maintaining original order)
        if qa_blocks:
            qa_chunks = self._merge_qa_pairs(qa_blocks, doc)
            chunks.extend(qa_chunks)

        return chunks

    def _make_header_chunk(self, blocks: List[UniversalBlock], doc: dict) -> dict:
        """Create header chunk from header blocks."""
        d = deepcopy(doc)
        d["chunk_type"] = "header"

        # Combine text (filter empty blocks)
        text = "\n".join(b.text.strip() for b in blocks if b.text.strip())
        d["content_with_weight"] = text

        # Filter blocks with valid bbox for position extraction
        valid_blocks = [b for b in blocks if b.bbox and b.text.strip()]

        # Extract and add position information for frontend highlighting
        if valid_blocks:
            poss = self._extract_positions(valid_blocks)
            if poss:
                add_positions(d, poss)

            # Use first block's position as fallback
            d["page_no"] = valid_blocks[0].page_no
            d["bbox"] = json.dumps(list(valid_blocks[0].bbox))

        # Merge entities
        entities = self._merge_entities(blocks)
        if entities:
            d["entities"] = json.dumps(entities)

        return d

    def _merge_qa_pairs(self, blocks: List[UniversalBlock], doc: dict) -> List[dict]:
        """Merge consecutive Q/A blocks into QA pair chunks."""
        chunks = []
        current_q = None
        current_a_blocks = []
        qa_index = 0

        for block in blocks:
            text = block.text.strip()
            if not text:
                continue  # Skip empty blocks

            if text.startswith(("问：", "问:", "问；", "问;")):
                # Save previous QA pair
                if current_q:
                    chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
                    if chunk and chunk.get("content_with_weight", "").strip():
                        chunks.append(chunk)
                        qa_index += 1
                current_q = block
                current_a_blocks = []
            elif text.startswith(("答：", "答:", "答；", "答;")):
                current_a_blocks.append(block)

        # Save last QA pair
        if current_q:
            chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
            if chunk and chunk.get("content_with_weight", "").strip():
                chunks.append(chunk)

        return chunks

    def _make_qa_chunk(
        self,
        q_block: UniversalBlock,
        a_blocks: List[UniversalBlock],
        doc: dict,
        qa_index: int
    ) -> dict:
        """Create QA pair chunk."""
        d = deepcopy(doc)
        d["chunk_type"] = "qa_pair"
        d["qa_index"] = qa_index

        # Combine question and answer
        q_text = q_block.text
        a_text = "\n".join(b.text for b in a_blocks)
        d["content_with_weight"] = f"{q_text}\t{a_text}"

        # Extract and add position information from all blocks (question + answers)
        all_blocks = [q_block] + a_blocks
        poss = self._extract_positions(all_blocks)
        if poss:
            add_positions(d, poss)

        # Use question block's position as fallback
        d["page_no"] = q_block.page_no
        d["bbox"] = json.dumps(list(q_block.bbox))

        # Merge entities
        entities = self._merge_entities(all_blocks)
        if entities:
            d["entities"] = json.dumps(entities)

        return d

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

    def _extract_positions(self, blocks: List[UniversalBlock]) -> list:
        """
        Extract position information from UniversalBlock list.

        UniversalBlock.bbox format: (x0, y0, x1, y1) where y0=top, y1=bottom
        add_positions expects: [(page, left, right, top, bottom), ...]

        Args:
            blocks: List of UniversalBlock objects

        Returns:
            List of position tuples for add_positions()
        """
        poss = []
        for block in blocks:
            if block.bbox:
                x0, y0, x1, y1 = block.bbox
                # Convert to (page, left, right, top, bottom)
                poss.append((block.page_no, x0, x1, y0, y1))
        return poss
