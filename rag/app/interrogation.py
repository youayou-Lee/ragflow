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
Interrogation Record Chunker - Uses InterrogationPlugin for Q/A parsing.

This module provides a chunk function that integrates with the RAGFlow task executor.
"""

import copy
import logging
import re

from rag.app.criminal import route_to_plugin
from rag.app.criminal.plugins.base import Chunk
from rag.app.naive import (
    extract_universal_blocks,
    rag_tokenizer,
    PARSERS,
)
from rag.nlp import tokenize, add_positions

logger = logging.getLogger(__name__)


def chunk(filename, binary=None, from_page=0, to_page=100000, lang="Chinese", callback=None, **kwargs):
    """
    Parse interrogation record PDFs using the two-layer architecture.

    Layer A: Extract UniversalBlocks from PDF using PaddleOCR
    Layer B: Transform blocks to chunks using InterrogationPlugin

    Args:
        filename: File name
        binary: File binary content
        from_page: Start page (0-indexed)
        to_page: End page (exclusive)
        lang: Language ("Chinese" or "English")
        callback: Progress callback function
        **kwargs: Additional arguments (parser_config, kb_id, tenant_id, etc.)

    Returns:
        List of chunk dictionaries compatible with RAGFlow indexing
    """
    is_english = lang.lower() == "english"
    parser_config = kwargs.get("parser_config", {})

    # Document metadata
    doc = {
        "docnm_kwd": filename,
        "title_tks": rag_tokenizer.tokenize(re.sub(r"\.[a-zA-Z]+$", "", filename)),
    }
    doc["title_sm_tks"] = rag_tokenizer.fine_grained_tokenize(doc["title_tks"])

    res = []

    # Only support PDF for interrogation records
    if not re.search(r"\.pdf$", filename, re.IGNORECASE):
        callback(-1, "Interrogation parser only supports PDF files.")
        return res

    callback(0.1, "Start to parse interrogation record.")

    # Get layout recognizer (parser type)
    layout_recognizer = parser_config.get("layout_recognize", "PaddleOCR")
    parser_model_name = parser_config.get("parser_model_name", "")

    if isinstance(layout_recognizer, bool):
        layout_recognizer = "DeepDOC" if layout_recognizer else "Plain Text"

    name = layout_recognizer.strip().lower()
    parser = PARSERS.get(name, PARSERS["paddleocr"])

    callback(0.3, "Parsing PDF with OCR...")

    # Parse PDF to get sections and tables
    sections, tables, pdf_parser = parser(
        filename=filename,
        binary=binary,
        from_page=from_page,
        to_page=to_page,
        lang=lang,
        callback=callback,
        layout_recognizer=layout_recognizer,
        paddleocr_llm_name=parser_model_name,
        **kwargs,
    )

    if not sections and not tables:
        callback(-1, "No content extracted from PDF.")
        return res

    callback(0.6, "OCR complete. Starting block extraction...")

    # Layer A: Extract universal blocks from sections
    blocks = extract_universal_blocks(sections, doc_type_hint="interrogation_record")

    if not blocks:
        callback(-1, "No blocks extracted from sections.")
        return res

    callback(0.7, f"Extracted {len(blocks)} blocks. Starting chunking...")

    # Layer B: Route to InterrogationPlugin
    chunks = route_to_plugin(blocks, "interrogation_record")

    if not chunks:
        callback(-1, "No chunks created from blocks.")
        return res

    callback(0.85, f"Created {len(chunks)} chunks. Finalizing...")

    # Convert Chunk objects to RAGFlow format
    for ii, chunk in enumerate(chunks):
        d = copy.deepcopy(doc)
        tokenize(d, chunk.text, is_english)

        # Try to get image and position from pdf_parser
        position_added = False
        if pdf_parser and chunk.raw_text:
            try:
                result = pdf_parser.crop(chunk.raw_text, need_position=True)
                if result is not None:
                    img, poss = result
                    # Add image to chunk for PDF highlighting
                    if img:
                        d["image"] = img
                    if poss:
                        add_positions(d, poss)
                        position_added = True
            except Exception as e:
                logger.warning(f"Failed to get position for chunk {ii}: {e}")

        # Fallback to index-based position
        if not position_added:
            add_positions(d, [[ii] * 5])

        res.append(d)

    callback(1.0, f"Complete. Created {len(res)} chunks.")
    logger.info(f"Interrogation chunking complete: {len(res)} chunks from {filename}")

    return res
