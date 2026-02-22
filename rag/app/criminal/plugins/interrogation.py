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

from typing import List
from copy import deepcopy

from .base import ParserPlugin
from ..blocks import UniversalBlock, BlockType


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

        1. Extract header blocks -> single header chunk
        2. Merge consecutive Q/A blocks -> QA pair chunks
        """
        chunks = []

        # 1. Process header blocks
        header_blocks = self.get_header_blocks(blocks)
        if header_blocks:
            header_chunk = self._make_header_chunk(header_blocks, doc)
            chunks.append(header_chunk)

        # 2. Process QA blocks
        qa_blocks = self.get_qa_blocks(blocks)
        if qa_blocks:
            qa_chunks = self._merge_qa_pairs(qa_blocks, doc)
            chunks.extend(qa_chunks)

        return chunks

    def _make_header_chunk(self, blocks: List[UniversalBlock], doc: dict) -> dict:
        """Create header chunk from header blocks."""
        d = deepcopy(doc)
        d["chunk_type"] = "header"

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

    def _merge_qa_pairs(self, blocks: List[UniversalBlock], doc: dict) -> List[dict]:
        """Merge consecutive Q/A blocks into QA pair chunks."""
        chunks = []
        current_q = None
        current_a_blocks = []
        qa_index = 0

        for block in blocks:
            text = block.text
            if text.startswith(("问：", "问:", "问；", "问;")):
                # Save previous QA pair
                if current_q:
                    chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
                    chunks.append(chunk)
                    qa_index += 1
                current_q = block
                current_a_blocks = []
            elif text.startswith(("答：", "答:", "答；", "答;")):
                current_a_blocks.append(block)

        # Save last QA pair
        if current_q:
            chunk = self._make_qa_chunk(current_q, current_a_blocks, doc, qa_index)
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

        # Use question block's position
        d["page_no"] = q_block.page_no
        d["bbox"] = list(q_block.bbox)

        # Merge entities
        all_blocks = [q_block] + a_blocks
        entities = self._merge_entities(all_blocks)
        if entities:
            d["entities"] = entities

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
