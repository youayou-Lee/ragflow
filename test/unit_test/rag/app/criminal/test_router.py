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

"""Tests for the plugin router module."""

import pytest

from rag.app.naive import UniversalBlock, BlockType


def make_block(text: str) -> UniversalBlock:
    """Helper to create a UniversalBlock for testing."""
    return UniversalBlock(
        block_type=BlockType.PARAGRAPH,
        text=text,
        page_no=0,
        bbox=(0, 0, 100, 50),
    )


class TestRouter:
    """Tests for plugin routing functionality."""

    def test_route_to_interrogation_plugin(self):
        """interrogation_record type should route to interrogation plugin."""
        from rag.app.criminal.router import route_to_plugin

        blocks = [make_block("问：你是谁？"), make_block("答：我是张三。")]
        chunks = route_to_plugin(blocks, "interrogation_record")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "qa_pair"

    def test_route_to_indictment_plugin(self):
        """indictment_opinion type should route to indictment plugin."""
        from rag.app.criminal.router import route_to_plugin

        # Use text that's at least MIN_CHUNK_SIZE (50 chars)
        blocks = [make_block("经依法侦查查明：犯罪嫌疑人张三涉嫌盗窃罪，经依法侦查终结，现已移送我院刑事检察部门审查起诉部门依法审查处理。")]
        chunks = route_to_plugin(blocks, "indictment_opinion")
        assert len(chunks) >= 1

    def test_route_to_generic_chunker(self):
        """Unknown type should route to generic chunker."""
        from rag.app.criminal.router import route_to_plugin

        blocks = [make_block("Some random content that is long enough to meet minimum chunk size requirements.")]
        chunks = route_to_plugin(blocks, "unknown_type")
        assert len(chunks) >= 1
        assert chunks[0].metadata.get("is_generic_chunked") is True

    def test_get_chunker_for_doc_type(self):
        """get_chunker_for_doc_type should return correct plugin instance."""
        from rag.app.criminal.router import get_chunker_for_doc_type
        from rag.app.criminal.plugins import InterrogationPlugin, IndictmentPlugin, GenericChunker

        assert isinstance(get_chunker_for_doc_type("interrogation_record"), InterrogationPlugin)
        assert isinstance(get_chunker_for_doc_type("indictment_opinion"), IndictmentPlugin)
        assert isinstance(get_chunker_for_doc_type("unknown"), GenericChunker)
