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
from api.db.services.fallback_service import FallbackConfig, FallbackModels, parse_fallback_config


pytestmark = pytest.mark.p1


class TestFallbackConfigParser:
    def test_parse_plain_string_api_key(self):
        """Plain string API key should return None fallback config"""
        result = parse_fallback_config("sk-plain-api-key")
        assert result.api_key == "sk-plain-api-key"
        assert result.fallback is None

    def test_parse_json_without_fallback(self):
        """JSON API key without fallback field should work"""
        result = parse_fallback_config('{"api_key": "sk-test-key"}')
        assert result.api_key == "sk-test-key"
        assert result.fallback is None

    def test_parse_json_with_fallback_models(self):
        """JSON with fallback models should parse correctly"""
        json_str = '{"api_key": "sk-test", "fallback": {"models": ["gpt-4o-mini", "gpt-3.5-turbo"]}}'
        result = parse_fallback_config(json_str)
        assert result.api_key == "sk-test"
        assert result.fallback is not None
        assert result.fallback.models == ["gpt-4o-mini", "gpt-3.5-turbo"]
        assert result.fallback.factories == []

    def test_parse_json_with_fallback_factories(self):
        """JSON with fallback factories should parse correctly"""
        json_str = '{"api_key": "sk-test", "fallback": {"factories": ["DeepSeek", "Qwen"]}}'
        result = parse_fallback_config(json_str)
        assert result.api_key == "sk-test"
        assert result.fallback.factories == ["DeepSeek", "Qwen"]
        assert result.fallback.models == []

    def test_parse_json_with_full_fallback_config(self):
        """JSON with complete fallback config should parse correctly"""
        json_str = '''{
            "api_key": "sk-test",
            "fallback": {
                "models": ["gpt-4o-mini", "gpt-3.5-turbo"],
                "factories": ["DeepSeek", "Qwen"]
            }
        }'''
        result = parse_fallback_config(json_str)
        assert result.api_key == "sk-test"
        assert result.fallback.models == ["gpt-4o-mini", "gpt-3.5-turbo"]
        assert result.fallback.factories == ["DeepSeek", "Qwen"]

    def test_parse_invalid_json_returns_plain_string(self):
        """Invalid JSON should be treated as plain API key"""
        result = parse_fallback_config('not valid json {')
        assert result.api_key == 'not valid json {'
        assert result.fallback is None

    def test_parse_empty_string(self):
        """Empty string should return empty config"""
        result = parse_fallback_config("")
        assert result.api_key == ""
        assert result.fallback is None

    def test_parse_none_returns_empty_config(self):
        """None should return empty config"""
        result = parse_fallback_config(None)
        assert result.api_key == ""
        assert result.fallback is None


class TestFallbackConfigMethods:
    def test_has_fallback_with_models(self):
        """has_fallback should return True when models are configured"""
        config = FallbackConfig(
            api_key="sk-test",
            fallback=FallbackModels(models=["gpt-4o-mini"], factories=[])
        )
        assert config.has_fallback() is True

    def test_has_fallback_with_factories(self):
        """has_fallback should return True when factories are configured"""
        config = FallbackConfig(
            api_key="sk-test",
            fallback=FallbackModels(models=[], factories=["DeepSeek"])
        )
        assert config.has_fallback() is True

    def test_has_fallback_without_fallback(self):
        """has_fallback should return False when no fallback is set"""
        config = FallbackConfig(api_key="sk-test", fallback=None)
        assert config.has_fallback() is False

    def test_has_fallback_with_empty_fallback(self):
        """has_fallback should return False when fallback is empty"""
        config = FallbackConfig(
            api_key="sk-test",
            fallback=FallbackModels(models=[], factories=[])
        )
        assert config.has_fallback() is False

    def test_to_json_str_plain_api_key(self):
        """to_json_str should return plain API key when no fallback"""
        config = FallbackConfig(api_key="sk-test", fallback=None)
        assert config.to_json_str() == "sk-test"

    def test_to_json_str_with_fallback(self):
        """to_json_str should return JSON when fallback is configured"""
        config = FallbackConfig(
            api_key="sk-test",
            fallback=FallbackModels(models=["gpt-4o-mini"], factories=["DeepSeek"])
        )
        result = config.to_json_str()
        assert '"api_key": "sk-test"' in result
        assert '"models": ["gpt-4o-mini"]' in result
        assert '"factories": ["DeepSeek"]' in result
