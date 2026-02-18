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
"""Chat evaluator for RAG evaluation framework.

This module handles chat/conversation operations for evaluation.
"""

import time
from typing import Optional

import requests

import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.eval.models import Citation


class ChatEvaluator:
    """Handles chat operations for evaluation."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.session_id: Optional[str] = None

    def create_session(self, chat_id: str) -> str:
        """Create a new chat session."""
        url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
        resp = self.session.post(url, json={})
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create session failed: {data.get('message')}")

        self.session_id = data["data"]["id"]
        return self.session_id

    def chat(
        self,
        chat_id: str,
        question: str,
        doc_ids: Optional[list[str]] = None,
    ) -> tuple[str, dict, float]:
        """
        Send a chat message and get the answer.

        Args:
            chat_id: Chat assistant ID
            question: The question to ask
            doc_ids: Optional document IDs to filter

        Returns:
            Tuple of (answer text, raw response data, chat time in ms)
        """
        # Create session if needed
        if not self.session_id:
            self.create_session(chat_id)

        url = f"{self.base_url}/api/v1/chats/{chat_id}/completions"

        payload = {
            "question": question,
            "stream": False,
            "session_id": self.session_id,
        }

        if doc_ids:
            payload["doc_ids"] = doc_ids

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Chat failed: {data.get('message')}")

        answer = data.get("data", {}).get("answer", "")
        return answer, data.get("data", {}), elapsed_ms

    def extract_citations(self, chat_data: dict) -> list[Citation]:
        """Extract citations from chat response data."""
        citations = []

        # Extract from reference if available
        reference = chat_data.get("reference", {})
        chunks = reference.get("chunks", [])

        for chunk in chunks:
            citations.append(Citation(
                chunk_id=chunk.get("chunk_id", ""),
                excerpt=chunk.get("content", "")[:200],  # Truncate for readability
                page_index=chunk.get("page_num"),
                bbox=chunk.get("bbox"),
            ))

        return citations
