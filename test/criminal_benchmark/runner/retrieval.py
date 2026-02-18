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
"""Retrieval runner for criminal benchmark."""

import time
from typing import Optional

import requests

import sys
from pathlib import Path
# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.criminal_benchmark.models import ChunkInfo


class RetrievalRunner:
    """Handles retrieval operations for benchmark testing."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def retrieve(
        self,
        question: str,
        dataset_ids: list[str],
        document_ids: Optional[list[str]] = None,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> tuple[list[ChunkInfo], float]:
        """
        Perform retrieval and return chunks with timing.

        Returns:
            Tuple of (chunks, time_ms)
        """
        url = f"{self.base_url}/api/v1/retrieval"
        payload = {
            "question": question,
            "dataset_ids": dataset_ids,
            "top_k": top_k,
            # API expects "similarity_threshold", not "score_threshold"
            "similarity_threshold": score_threshold,
        }

        if document_ids:
            payload["document_ids"] = document_ids

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Retrieval failed: {data.get('message')}")

        # Parse chunks
        chunks = []
        for item in data.get("data", {}).get("chunks", []):
            chunks.append(ChunkInfo(
                chunk_id=item.get("chunk_id", ""),
                content=item.get("content_with_weight", "") or item.get("content", ""),
                score=item.get("similarity", 0.0),
                document_id=item.get("document_id", ""),
                document_name=item.get("docnm_kwt", "") or item.get("docnm_kwd", ""),
                page_num=item.get("page_num_int", [None])[0] if item.get("page_num_int") else None,
                bbox=item.get("bbox"),
            ))

        return chunks, elapsed_ms
