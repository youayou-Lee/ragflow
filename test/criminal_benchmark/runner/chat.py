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
"""Chat runner for criminal benchmark."""

import time
from typing import Optional

import requests


class ChatRunner:
    """Handles chat operations for benchmark testing."""

    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url.rstrip("/")

    def chat(
        self,
        chat_id: str,
        question: str,
        session_id: Optional[str] = None,
        stream: bool = False,
    ) -> tuple[str, dict, float]:
        """
        Send a chat message and get response.

        Returns:
            Tuple of (answer, raw_response, time_ms)
        """
        url = f"{self.base_url}/api/v1/chats/{chat_id}/completions"
        payload = {
            "question": question,
            "stream": stream,
        }

        if session_id:
            payload["session_id"] = session_id

        start_time = time.perf_counter()
        resp = self.session.post(url, json=payload)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Chat failed: {data.get('message')}")

        # Extract answer
        answer = data.get("data", {}).get("answer", "")

        return answer, data.get("data", {}), elapsed_ms

    def create_session(self, chat_id: str, name: str = "benchmark_session") -> str:
        """Create a new chat session."""
        url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
        payload = {"name": name}

        resp = self.session.post(url, json=payload)
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Create session failed: {data.get('message')}")

        return data["data"]["id"]
