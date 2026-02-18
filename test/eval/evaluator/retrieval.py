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
"""Retrieval evaluator for RAG evaluation framework.

This module handles retrieval operations without tuning parameters.
It uses server-side defaults for retrieval configuration.
"""

import time
from typing import Optional

import requests

import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import ChunkInfo


class RetrievalEvaluator:
    """Handles retrieval operations for evaluation."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def retrieve(
        self,
        question: str,
        dataset_ids: list[str],
        document_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> tuple[list[ChunkInfo], float]:
        """
        Perform retrieval and return chunks with timing.

        Args:
            question: The question to retrieve for
            dataset_ids: Dataset IDs to search in
            document_ids: Optional document IDs to filter
            top_k: Optional top_k override (None = use server default)
            similarity_threshold: Optional threshold override (None = use server default)

        Returns:
            Tuple of (list of ChunkInfo, retrieval time in ms)
        """
        url = f"{self.base_url}/api/v1/retrieval"

        payload = {
            "question": question,
            "dataset_ids": dataset_ids,
        }

        # Only add optional parameters if specified (otherwise use server defaults)
        if document_ids:
            payload["document_ids"] = document_ids
        if top_k is not None:
            payload["top_k"] = top_k
        if similarity_threshold is not None:
            payload["similarity_threshold"] = similarity_threshold

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Retrieval failed: {data.get('message')}")

        # Parse chunks
        chunks = []
        for chunk_data in data.get("data", {}).get("chunks", []):
            chunks.append(ChunkInfo(
                chunk_id=chunk_data.get("chunk_id", ""),
                content=chunk_data.get("content", ""),
                score=chunk_data.get("similarity", 0.0),
                document_id=chunk_data.get("document_id", ""),
                document_name=chunk_data.get("document_keyword", ""),
                page_num=chunk_data.get("page_num"),
                bbox=chunk_data.get("bbox"),
            ))

        return chunks, elapsed_ms
