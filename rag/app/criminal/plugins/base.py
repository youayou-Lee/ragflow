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
Layer B plugin infrastructure.

Provides the base class for document type plugins and the plugin registry.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class Chunk:
    """
    Chunk structure - Layer B output.

    Attributes:
        case_id: Case identifier
        doc_id: Document identifier
        doc_type: Document type (e.g., "interrogation_record")
        chunk_id: Unique chunk identifier
        chunk_type: Type of chunk (paragraph, qa_pair, section, table, image)
        text: Text content (without position tags)
        raw_text: Text content with position tags (for pdf_parser.crop)
        page_range: [start_page, end_page] (1-indexed)
        bbox_union: Bounding box union [x0, y0, x1, y1]
        block_refs: List of block references [{"page_index": 1, "block_id": "xxx"}]
        metadata: Additional metadata
    """

    case_id: str
    doc_id: str
    doc_type: str
    chunk_id: str
    chunk_type: str
    text: str
    raw_text: str = ""  # Text with position tags for pdf_parser.crop
    page_range: List[int] = field(default_factory=list)
    bbox_union: List[float] = field(default_factory=list)
    block_refs: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentPlugin(ABC):
    """
    Base class for document type plugins.

    Each plugin handles a specific document type and transforms
    Block sequences into Chunk sequences.
    """

    @property
    @abstractmethod
    def doc_type(self) -> str:
        """Return the document type this plugin handles."""
        pass

    @property
    def priority(self) -> int:
        """Priority for plugin selection (lower = higher priority)."""
        return 100

    @abstractmethod
    def transform(self, blocks: List[Any]) -> List[Chunk]:
        """
        Transform Block sequence into Chunk sequence.

        Args:
            blocks: List of UniversalBlock objects from Layer A

        Returns:
            List of Chunk objects
        """
        pass


class PluginRegistry:
    """Registry for document type plugins."""

    def __init__(self) -> None:
        self._plugins: Dict[str, Type[DocumentPlugin]] = {}

    def register(self, doc_type: str) -> Callable[[Type[DocumentPlugin]], Type[DocumentPlugin]]:
        """
        Decorator to register a plugin for a document type.

        Usage:
            @plugin_registry.register("interrogation_record")
            class InterrogationPlugin(DocumentPlugin):
                ...
        """

        def decorator(plugin_class: Type[DocumentPlugin]) -> Type[DocumentPlugin]:
            self._plugins[doc_type] = plugin_class
            return plugin_class

        return decorator

    def get(self, doc_type: str) -> Optional[DocumentPlugin]:
        """Get plugin instance for document type."""
        plugin_class = self._plugins.get(doc_type)
        if plugin_class:
            return plugin_class()
        return None

    def list_plugins(self) -> List[str]:
        """List all registered document types."""
        return list(self._plugins.keys())


# Global plugin registry
plugin_registry = PluginRegistry()
