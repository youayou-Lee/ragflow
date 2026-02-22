# rag/app/criminal/plugins/base.py
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
Base class for Layer B parser plugins.

Plugins receive UniversalBlock sequences and output semantic chunks.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..blocks import UniversalBlock, BlockType


class ParserPlugin(ABC):
    """
    Abstract base class for document-type specific parser plugins.

    Layer B plugins receive UniversalBlock sequences from Layer A
    and produce semantic chunks for indexing and retrieval.

    Attributes:
        doc_type: Document type identifier (e.g., "interrogation", "indictment")
    """

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """
        Return document type identifier.

        Returns:
            str: Document type (e.g., "interrogation", "indictment")
        """
        pass

    @abstractmethod
    def process(
        self,
        blocks: List[UniversalBlock],
        doc: dict,
        chat_mdl=None,
        **kwargs
    ) -> List[dict]:
        """
        Process block sequence and generate chunks.

        Args:
            blocks: UniversalBlock list from Layer A
            doc: Document metadata (filename, etc.)
            chat_mdl: Optional LLM model for metadata enhancement
            **kwargs: Additional arguments

        Returns:
            List of chunk dictionaries with keys:
            - content_with_weight: Text content
            - chunk_type: Semantic chunk type
            - page_no: Page number
            - bbox: Bounding box
            - entities: Extracted entities (optional)
            - metadata: Additional metadata (optional)
        """
        pass

    def get_header_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all header blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with HEADER type
        """
        return [b for b in blocks if b.block_type == BlockType.HEADER]

    def get_qa_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all Q/A pair blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with QA_PAIR type
        """
        return [b for b in blocks if b.block_type == BlockType.QA_PAIR]

    def get_paragraph_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all paragraph blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with PARAGRAPH type
        """
        return [b for b in blocks if b.block_type == BlockType.PARAGRAPH]

    def get_list_blocks(self, blocks: List[UniversalBlock]) -> List[UniversalBlock]:
        """
        Helper: Get all list blocks.

        Args:
            blocks: Block list

        Returns:
            List of blocks with LIST type
        """
        return [b for b in blocks if b.block_type == BlockType.LIST]
