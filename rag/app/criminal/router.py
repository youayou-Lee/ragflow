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
Plugin router - Routes blocks to appropriate chunker based on doc_type.

This module provides the main entry point for Layer B processing,
routing UniversalBlock sequences to the appropriate document plugin.
"""

from typing import List, Any

from .plugins import (
    DocumentPlugin,
    Chunk,
    plugin_registry,
    GenericChunker,
)
from rag.app.naive import UniversalBlock


# Global generic chunker instance (singleton for fallback)
_generic_chunker = GenericChunker()


def get_chunker_for_doc_type(doc_type: str) -> DocumentPlugin:
    """
    Get the appropriate chunker for a document type.

    Looks up the plugin in the registry. If no specific plugin is registered
    for the document type, returns the GenericChunker as a fallback.

    Args:
        doc_type: Document type identifier (e.g., "interrogation_record",
                  "indictment_opinion")

    Returns:
        DocumentPlugin instance (specific plugin or generic fallback)
    """
    plugin = plugin_registry.get(doc_type)
    if plugin:
        return plugin
    return _generic_chunker


def route_to_plugin(blocks: List[UniversalBlock], doc_type: str) -> List[Chunk]:
    """
    Route blocks to appropriate plugin and return chunks.

    This is the main entry point for Layer B processing. It:
    1. Looks up the appropriate plugin for the document type
    2. Falls back to GenericChunker if no specific plugin exists
    3. Transforms the blocks into chunks

    Args:
        blocks: List of UniversalBlock from Layer A (layout analysis)
        doc_type: Document type (e.g., "interrogation_record",
                  "indictment_opinion")

    Returns:
        List of Chunk objects ready for embedding and indexing
    """
    chunker = get_chunker_for_doc_type(doc_type)
    return chunker.transform(blocks)
