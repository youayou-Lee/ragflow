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
Unit tests for FallbackExecutor class.

These tests verify the fallback logic when LLM calls fail with
recoverable errors like rate limits or server errors.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from api.db.services.fallback_service import FallbackConfig, FallbackModels
from api.db.services.tenant_llm_service import FallbackExecutor, TenantLLMService


pytestmark = pytest.mark.p1


class TestFallbackExecutorInit:
    """Test cases for FallbackExecutor initialization."""

    def test_init_with_valid_config(self):
        """FallbackExecutor should initialize with valid config"""
        fallback_models = FallbackModels(models=["gpt-4o-mini"], factories=[])
        config = FallbackConfig(api_key="sk-test", fallback=fallback_models)

        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        assert executor.tenant_id == "test-tenant"
        assert executor.llm_type == "chat"
        assert executor.original_llm_name == "gpt-4o"
        assert executor.fallback_config == config

    def test_init_with_no_fallback(self):
        """FallbackExecutor should work with no fallback config"""
        config = FallbackConfig(api_key="sk-test", fallback=None)

        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        assert executor.fallback_config.has_fallback() is False


class TestFallbackExecutorShouldFallback:
    """Test cases for _should_fallback method."""

    @pytest.fixture
    def executor(self):
        """Create a FallbackExecutor for testing"""
        config = FallbackConfig(api_key="sk-test", fallback=FallbackModels())
        return FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

    def test_rate_limit_should_fallback(self, executor):
        """Rate limit errors should trigger fallback"""
        assert executor._should_fallback(Exception("rate limit exceeded (429)")) is True
        assert executor._should_fallback(Exception("429 Too Many Requests")) is True

    def test_server_error_should_fallback(self, executor):
        """Server errors should trigger fallback"""
        assert executor._should_fallback(Exception("503 Service Unavailable")) is True
        assert executor._should_fallback(Exception("500 Internal Server Error")) is True
        assert executor._should_fallback(Exception("502 Bad Gateway")) is True

    def test_timeout_should_fallback(self, executor):
        """Timeout errors should trigger fallback"""
        assert executor._should_fallback(Exception("Request timeout")) is True

    def test_connection_error_should_fallback(self, executor):
        """Connection errors should trigger fallback"""
        assert executor._should_fallback(Exception("Connection refused")) is True

    def test_quota_error_should_fallback(self, executor):
        """Quota exceeded errors should trigger fallback"""
        assert executor._should_fallback(Exception("quota exceeded")) is True

    def test_auth_error_should_not_fallback(self, executor):
        """Authentication errors should not trigger fallback"""
        assert executor._should_fallback(Exception("401 Unauthorized")) is False
        assert executor._should_fallback(Exception("Authentication error")) is False
        assert executor._should_fallback(Exception("invalid api key")) is False

    def test_content_filter_should_not_fallback(self, executor):
        """Content filter errors should not trigger fallback"""
        assert executor._should_fallback(Exception("content filter blocked")) is False


class TestFallbackExecutorExecute:
    """Test cases for execute method."""

    def test_no_fallback_config_returns_original_result(self):
        """When no fallback is configured, return original result or raise error"""
        config = FallbackConfig(api_key="sk-test", fallback=None)
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        # Mock successful call
        with patch.object(executor, '_call_model', return_value="Success"):
            result = executor.execute([{"role": "user", "content": "Hello"}])
            assert result == "Success"

    def test_fallback_to_same_factory_model_on_rate_limit(self):
        """Should fallback to next model in same factory on rate limit"""
        fallback_models = FallbackModels(
            models=["gpt-4o-mini", "gpt-3.5-turbo"],
            factories=[]
        )
        config = FallbackConfig(api_key="sk-test", fallback=fallback_models)
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        call_count = [0]

        def mock_call_with_name(model_name, messages, gen_conf):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call to _call_model (original) fails
                raise Exception("rate limit exceeded (429)")
            # Second call (fallback model) succeeds
            return "Success from fallback"

        # First call fails, then same-factory fallback succeeds
        with patch.object(executor, '_call_model', side_effect=Exception("rate limit exceeded (429)")):
            with patch.object(executor, '_call_model_with_name', side_effect=mock_call_with_name):
                result = executor.execute([{"role": "user", "content": "Hello"}])
                assert result == "Success from fallback"
                assert call_count[0] == 2

    def test_fallback_to_cross_factory_when_all_models_fail(self):
        """Should fallback to another factory when all same-factory models fail"""
        fallback_models = FallbackModels(
            models=["gpt-4o-mini"],
            factories=["DeepSeek"]
        )
        config = FallbackConfig(api_key="sk-test", fallback=fallback_models)
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        call_count = [0]

        def mock_call_with_factory(factory, messages, gen_conf):
            call_count[0] += 1
            # Cross-factory call succeeds
            return "Success from DeepSeek"

        # All same-factory calls fail, cross-factory succeeds
        with patch.object(executor, '_call_model', side_effect=Exception("rate limit exceeded")):
            with patch.object(executor, '_call_model_with_name', side_effect=Exception("rate limit exceeded")):
                with patch.object(executor, '_call_model_with_factory', side_effect=mock_call_with_factory):
                    result = executor.execute([{"role": "user", "content": "Hello"}])
                    assert result == "Success from DeepSeek"

    def test_no_fallback_on_auth_error(self):
        """Authentication errors should not trigger fallback"""
        fallback_models = FallbackModels(models=["gpt-4o-mini"])
        config = FallbackConfig(api_key="sk-test", fallback=fallback_models)
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        with patch.object(executor, '_call_model', side_effect=Exception("Authentication error (401)")):
            with pytest.raises(Exception) as exc_info:
                executor.execute([{"role": "user", "content": "Hello"}])
            assert "Authentication error" in str(exc_info.value)

    def test_raises_last_error_when_all_fallbacks_fail(self):
        """When all fallbacks fail, raise the last error"""
        fallback_models = FallbackModels(
            models=["gpt-4o-mini"],
            factories=["DeepSeek"]
        )
        config = FallbackConfig(api_key="sk-test", fallback=fallback_models)
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=config,
        )

        def mock_fail(*args, **kwargs):
            raise Exception("Service unavailable")

        with patch.object(executor, '_call_model', side_effect=mock_fail):
            with patch.object(executor, '_call_model_with_name', side_effect=mock_fail):
                with patch.object(executor, '_call_model_with_factory', side_effect=mock_fail):
                    with pytest.raises(Exception) as exc_info:
                        executor.execute([{"role": "user", "content": "Hello"}])
                    assert "Service unavailable" in str(exc_info.value)


class TestGetFactoryPrimaryModel:
    """Test cases for get_factory_primary_model service method."""

    def test_returns_first_chat_model_for_factory(self):
        """Should return first available chat model for a factory"""
        mock_records = [
            Mock(llm_name="deepseek-chat", model_type="chat", api_key="sk-deepseek", api_base=None),
            Mock(llm_name="deepseek-coder", model_type="chat", api_key="sk-deepseek", api_base=None),
        ]

        with patch.object(TenantLLMService, 'query', return_value=mock_records):
            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "DeepSeek", "chat"
            )
            assert result["llm_name"] == "deepseek-chat"
            assert result["api_key"] == "sk-deepseek"

    def test_returns_none_for_unconfigured_factory(self):
        """Should return None if factory has no configured models"""
        with patch.object(TenantLLMService, 'query', return_value=[]):
            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "UnknownFactory", "chat"
            )
            assert result is None

    def test_skips_models_without_api_key(self):
        """Should skip models that don't have an API key configured"""
        mock_records = [
            Mock(llm_name="model-without-key", model_type="chat", api_key=None, api_base=None),
            Mock(llm_name="model-with-key", model_type="chat", api_key="sk-test", api_base=None),
        ]

        with patch.object(TenantLLMService, 'query', return_value=mock_records):
            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "TestFactory", "chat"
            )
            assert result["llm_name"] == "model-with-key"

    def test_returns_none_when_all_models_missing_api_key(self):
        """Should return None if all models are missing API keys"""
        mock_records = [
            Mock(llm_name="model1", model_type="chat", api_key=None, api_base=None),
            Mock(llm_name="model2", model_type="chat", api_key="", api_base=None),
        ]

        with patch.object(TenantLLMService, 'query', return_value=mock_records):
            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "TestFactory", "chat"
            )
            assert result is None
