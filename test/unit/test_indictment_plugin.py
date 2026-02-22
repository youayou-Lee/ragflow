# test/unit/test_indictment_plugin.py
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

import pytest
from rag.app.criminal.plugins.indictment import IndictmentPlugin
from rag.app.criminal.blocks import UniversalBlock, BlockType


class TestIndictmentPlugin:
    """Test IndictmentPlugin."""

    def test_doc_type(self):
        """Test doc_type property."""
        plugin = IndictmentPlugin()
        assert plugin.doc_type == "indictment"

    def test_process_empty_blocks(self):
        """Test processing empty block list."""
        plugin = IndictmentPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []

    def test_process_paragraph_blocks(self):
        """Test processing paragraph blocks."""
        plugin = IndictmentPlugin()
        blocks = [
            UniversalBlock(BlockType.PARAGRAPH, "起诉意见书", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "犯罪嫌疑人张三", 0, (0, 50, 100, 100)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        assert len(chunks) >= 1

    def test_process_with_section_trigger(self):
        """Test blocks containing section triggers."""
        plugin = IndictmentPlugin()
        blocks = [
            UniversalBlock(BlockType.HEADER, "起诉意见书", 0, (0, 0, 100, 50)),
            UniversalBlock(BlockType.PARAGRAPH, "经依法侦查查明，事实如下", 0, (0, 50, 100, 100)),
            UniversalBlock(BlockType.PARAGRAPH, "具体犯罪事实描述", 0, (0, 100, 100, 150)),
        ]
        chunks = plugin.process(blocks, {"docnm_kwt": "test.pdf"})
        # Should create section chunks based on triggers
        assert len(chunks) >= 1
