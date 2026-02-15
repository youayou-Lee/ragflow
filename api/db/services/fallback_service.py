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
Fallback configuration parser for LLM multi-level fallback mechanism.

This module provides dataclasses and parsing functions for configuring
fallback behavior when LLM API calls fail with recoverable errors.

Data structure (stored in TenantLLM.api_key as JSON):
{
    "api_key": "sk-xxx",
    "fallback_by_type": {
        "chat": {"models": ["glm-4-flash"], "factories": ["DeepSeek"]},
        "embedding": {"models": ["embedding-2"], "factories": []}
    }
}
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional


# Model type constants
MODEL_TYPE_CHAT = "chat"
MODEL_TYPE_EMBEDDING = "embedding"
MODEL_TYPE_RERANK = "rerank"
MODEL_TYPE_IMAGE2TEXT = "image2text"
MODEL_TYPE_TTS = "tts"
MODEL_TYPE_SPEECH2TEXT = "speech2text"

ALL_MODEL_TYPES = [
    MODEL_TYPE_CHAT,
    MODEL_TYPE_EMBEDDING,
    MODEL_TYPE_RERANK,
    MODEL_TYPE_IMAGE2TEXT,
    MODEL_TYPE_TTS,
    MODEL_TYPE_SPEECH2TEXT,
]


@dataclass
class FallbackModels:
    """Fallback configuration for a single model type."""
    models: list[str] = field(default_factory=list)
    factories: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if this fallback config is empty."""
        return len(self.models) == 0 and len(self.factories) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "models": self.models,
            "factories": self.factories,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FallbackModels":
        """Create from dictionary."""
        return cls(
            models=data.get("models", []),
            factories=data.get("factories", []),
        )


@dataclass
class FallbackConfig:
    """Parsed API key configuration with optional fallback settings per model type."""
    api_key: str
    # Key: model type (chat, embedding, etc.), Value: FallbackModels
    fallback_by_type: dict[str, FallbackModels] = field(default_factory=dict)

    def has_fallback(self, model_type: str = None) -> bool:
        """Check if any fallback is configured for a specific type or all types."""
        if model_type:
            fb = self.fallback_by_type.get(model_type)
            return fb is not None and not fb.is_empty()

        # Check if any type has fallback configured
        for fb in self.fallback_by_type.values():
            if not fb.is_empty():
                return True
        return False

    def get_fallback(self, model_type: str) -> FallbackModels:
        """Get fallback config for a specific model type."""
        return self.fallback_by_type.get(model_type, FallbackModels())

    def set_fallback(self, model_type: str, fallback: FallbackModels):
        """Set fallback config for a specific model type."""
        if fallback.is_empty():
            # Remove empty config
            self.fallback_by_type.pop(model_type, None)
        else:
            self.fallback_by_type[model_type] = fallback

    def to_json_str(self) -> str:
        """Convert back to JSON string for storage."""
        if not self.has_fallback():
            return self.api_key

        config = {"api_key": self.api_key}
        if self.fallback_by_type:
            config["fallback_by_type"] = {
                mt: fb.to_dict()
                for mt, fb in self.fallback_by_type.items()
                if not fb.is_empty()
            }
        return json.dumps(config)

    def to_legacy_json_str(self) -> str:
        """Convert to legacy format for backward compatibility."""
        # Use chat fallback as the default for legacy format
        chat_fallback = self.fallback_by_type.get(MODEL_TYPE_CHAT)
        if not chat_fallback or chat_fallback.is_empty():
            return self.api_key

        config = {"api_key": self.api_key}
        config["fallback"] = chat_fallback.to_dict()
        return json.dumps(config)


def parse_fallback_config(api_key_str: str) -> FallbackConfig:
    """
    Parse API key string which may be:
    - Plain string: "sk-xxx"
    - JSON with fallback_by_type: '{"api_key": "sk-xxx", "fallback_by_type": {...}}'
    - Legacy JSON with fallback: '{"api_key": "sk-xxx", "fallback": {...}}'

    Args:
        api_key_str: The API key string to parse

    Returns:
        FallbackConfig with parsed api_key and optional fallback settings
    """
    if not api_key_str:
        return FallbackConfig(api_key="")

    # Try to parse as JSON
    try:
        data = json.loads(api_key_str)
        if isinstance(data, dict):
            api_key = data.get("api_key", api_key_str)

            fallback_by_type = {}

            # New format: fallback_by_type
            if "fallback_by_type" in data:
                for model_type, fb_data in data["fallback_by_type"].items():
                    if isinstance(fb_data, dict):
                        fallback_by_type[model_type] = FallbackModels.from_dict(fb_data)

            # Legacy format: fallback (treat as chat fallback)
            elif "fallback" in data:
                fb_data = data["fallback"]
                if isinstance(fb_data, dict):
                    fallback_by_type[MODEL_TYPE_CHAT] = FallbackModels.from_dict(fb_data)

            return FallbackConfig(api_key=api_key, fallback_by_type=fallback_by_type)
    except (json.JSONDecodeError, TypeError):
        pass

    # Treat as plain string
    return FallbackConfig(api_key=api_key_str)
