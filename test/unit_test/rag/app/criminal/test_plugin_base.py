# tests/unit/rag/app/criminal/test_plugin_base.py
import pytest
from rag.app.criminal.plugins.base import DocumentPlugin, Chunk, plugin_registry


class TestDocumentPlugin:
    def test_plugin_base_is_abstract(self):
        """DocumentPlugin should be an abstract class and cannot be directly instantiated"""
        with pytest.raises(TypeError):
            DocumentPlugin()

    def test_plugin_must_implement_transform(self):
        """Plugin must implement the transform method"""

        class IncompletePlugin(DocumentPlugin):
            @property
            def doc_type(self) -> str:
                return "test"

        with pytest.raises(TypeError):
            IncompletePlugin()


class TestPluginRegistry:
    def test_register_plugin(self):
        """Plugin can be registered to the registry"""

        @plugin_registry.register("test_doc")
        class TestPlugin(DocumentPlugin):
            @property
            def doc_type(self) -> str:
                return "test_doc"

            def transform(self, blocks):
                return []

        assert plugin_registry.get("test_doc") is not None

    def test_get_nonexistent_plugin_returns_none(self):
        """Getting a non-existent plugin returns None"""
        assert plugin_registry.get("nonexistent") is None


class TestChunk:
    def test_chunk_creation(self):
        """Chunk can be created normally"""
        chunk = Chunk(
            case_id="case1",
            doc_id="doc1",
            doc_type="test",
            chunk_id="chunk1",
            chunk_type="paragraph",
            text="test content",
            page_range=[1, 1],
            bbox_union=[0, 0, 100, 100],
            block_refs=[{"page_index": 1, "block_id": "b1"}],
        )
        assert chunk.case_id == "case1"
        assert chunk.text == "test content"
