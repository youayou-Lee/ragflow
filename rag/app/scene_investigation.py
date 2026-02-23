# rag/app/scene_investigation.py
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
Scene Investigation Record (现场勘验检查笔录) Parser.

Entry function for parsing police scene investigation records.
"""

import re

from rag.app.criminal.blocks import extract_universal_blocks
from rag.app.criminal.plugins.scene_investigation import SceneInvestigationPlugin
from rag.nlp import rag_tokenizer, tokenize, add_bbox_union, add_page_range, add_block_refs


def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    Parse Scene Investigation Record (现场勘验检查笔录) into chunks.

    Args:
        filename: File path to the PDF document
        binary: Binary content of the file (optional)
        from_page: Start page (0-indexed)
        to_page: End page (exclusive)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function(progress, message)
        **kwargs: Additional arguments including parser_config, tenant_id, kb_id, chat_mdl

    Returns:
        list: List of chunk dictionaries with content, positions, and entities
    """
    eng = lang.lower() == "english"

    # Base document info
    doc = {
        "docnm_kwt": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename))
    }

    # Check file format
    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        raise NotImplementedError("仅支持 PDF 格式文件")

    if callback:
        callback(0.1, "开始解析现场勘验笔录...")

    # Step 1: OCR using PaddleOCR
    from rag.app.naive import by_paddleocr
    parser_config = kwargs.get("parser_config", {})

    sections, tables, pdf_parser = by_paddleocr(
        filename=filename,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        parser_config=parser_config,
        tenant_id=kwargs.get("tenant_id"),
        kb_id=kwargs.get("kb_id"),
        doc_id=parser_config.get("doc_id", ""),
    )

    if callback:
        callback(0.4, "OCR 完成")

    # Step 2: Layer A - Universal Block extraction
    blocks = extract_universal_blocks(sections, "scene_investigation")
    if callback:
        callback(0.6, f"提取 {len(blocks)} 个版面块")

    # Step 3: Layer B - Scene Investigation Plugin processing
    plugin = SceneInvestigationPlugin()
    chunks = plugin.process(blocks, doc, chat_mdl=kwargs.get("chat_mdl"))
    if callback:
        callback(0.8, f"生成 {len(chunks)} 个语义块")

    # Step 4: Add RAG-required fields
    for c in chunks:
        content = c.get("content_with_weight", "")
        tokenize(c, content, eng)
        add_bbox_union(c)
        add_page_range(c)
        add_block_refs(c)

    if callback:
        callback(1.0, f"解析完成，共 {len(chunks)} 个语义块")

    return chunks
