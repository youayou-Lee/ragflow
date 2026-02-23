# test/unit/test_scene_investigation_plugin.py
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
Unit tests for SceneInvestigationPlugin.
"""

import pytest

from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin


class TestSceneInvestigationPlugin:
    """Tests for SceneInvestigationPlugin basic functionality."""

    def test_doc_type(self):
        """Test that doc_type returns correct identifier."""
        plugin = SceneInvestigationPlugin()
        assert plugin.doc_type == "scene_investigation"

    def test_process_empty_blocks(self):
        """Test that empty blocks return empty chunks."""
        plugin = SceneInvestigationPlugin()
        chunks = plugin.process([], {"docnm_kwt": "test.pdf"})
        assert chunks == []
