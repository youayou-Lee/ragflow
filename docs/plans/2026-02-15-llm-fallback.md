# LLM Multi-Level Fallback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a multi-level LLM fallback mechanism that automatically switches to backup models when rate limits or recoverable errors occur.

**Architecture:**
- Extend `TenantLLM.api_key` field to store fallback configuration in JSON format
- Modify `LLM4Tenant` class to implement fallback logic with priority: same-factory models → cross-factory models
- Add frontend UI for users to configure fallback models per factory

**Tech Stack:** Python (Flask, Peewee), TypeScript (React, React Query, Ant Design)

---

## Part 1: Backend Implementation

### Task 1: Create Fallback Configuration Parser

**Files:**
- Create: `api/db/services/fallback_service.py`
- Test: `test/testcases/test_fallback_service.py`

**Step 1: Write the failing test**

```python
# test/testcases/test_fallback_service.py
import pytest
from api.db.services.fallback_service import FallbackConfig, parse_fallback_config


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
```

**Step 2: Run test to verify it fails**

```bash
cd /home/you/cs/proj/Superyou/ragflow
uv run pytest test/testcases/test_fallback_service.py -v
```
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Write minimal implementation**

```python
# api/db/services/fallback_service.py
import json
import logging
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FallbackModels:
    """Fallback configuration for a single factory"""
    models: list[str] = field(default_factory=list)
    factories: list[str] = field(default_factory=list)


@dataclass
class FallbackConfig:
    """Parsed API key configuration with optional fallback settings"""
    api_key: str
    fallback: Optional[FallbackModels] = None

    def has_fallback(self) -> bool:
        """Check if any fallback is configured"""
        return self.fallback is not None and (
            len(self.fallback.models) > 0 or len(self.fallback.factories) > 0
        )

    def to_json_str(self) -> str:
        """Convert back to JSON string for storage"""
        if not self.has_fallback():
            return self.api_key

        config = {"api_key": self.api_key}
        if self.fallback:
            config["fallback"] = {
                "models": self.fallback.models,
                "factories": self.fallback.factories,
            }
        return json.dumps(config)


def parse_fallback_config(api_key_str: str) -> FallbackConfig:
    """
    Parse API key string which may be:
    - Plain string: "sk-xxx"
    - JSON with fallback: '{"api_key": "sk-xxx", "fallback": {...}}'
    """
    if not api_key_str:
        return FallbackConfig(api_key="")

    # Try to parse as JSON
    try:
        data = json.loads(api_key_str)
        if isinstance(data, dict):
            api_key = data.get("api_key", api_key_str)
            fallback_data = data.get("fallback")

            fallback = None
            if fallback_data and isinstance(fallback_data, dict):
                fallback = FallbackModels(
                    models=fallback_data.get("models", []),
                    factories=fallback_data.get("factories", []),
                )

            return FallbackConfig(api_key=api_key, fallback=fallback)
    except (json.JSONDecodeError, TypeError):
        pass

    # Treat as plain string
    return FallbackConfig(api_key=api_key_str)
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/testcases/test_fallback_service.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add api/db/services/fallback_service.py test/testcases/test_fallback_service.py
git commit -m "feat: add fallback configuration parser for LLM API keys"
```

---

### Task 2: Add Recoverable Error Detection

**Files:**
- Modify: `rag/llm/chat_model.py`
- Test: `test/testcases/test_recoverable_errors.py`

**Step 1: Write the failing test**

```python
# test/testcases/test_recoverable_errors.py
import pytest
from rag.llm.chat_model import LLMErrorCode, is_recoverable_error


class TestRecoverableErrors:
    def test_rate_limit_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_RATE_LIMIT) is True

    def test_server_error_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_SERVER) is True

    def test_timeout_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_TIMEOUT) is True

    def test_connection_error_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_CONNECTION) is True

    def test_quota_exceeded_is_recoverable(self):
        assert is_recoverable_error(LLMErrorCode.ERROR_QUOTA) is True

    def test_auth_error_is_not_recoverable(self):
        """Authentication errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_AUTHENTICATION) is False

    def test_content_filter_is_not_recoverable(self):
        """Content filter errors should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_CONTENT_FILTER) is False

    def test_model_error_is_not_recoverable(self):
        """Model errors (like model not found) should not trigger fallback"""
        assert is_recoverable_error(LLMErrorCode.ERROR_MODEL) is False
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/testcases/test_recoverable_errors.py -v
```
Expected: FAIL with "cannot import name 'is_recoverable_error'"

**Step 3: Write minimal implementation**

```python
# Add to rag/llm/chat_model.py after LLMErrorCode definitions (around line 50)

# Recoverable errors that should trigger fallback
RECOVERABLE_ERRORS = {
    LLMErrorCode.ERROR_RATE_LIMIT,
    LLMErrorCode.ERROR_SERVER,
    LLMErrorCode.ERROR_TIMEOUT,
    LLMErrorCode.ERROR_CONNECTION,
    LLMErrorCode.ERROR_QUOTA,
}


def is_recoverable_error(error_code: str) -> bool:
    """
    Check if an error is recoverable and should trigger fallback.

    Recoverable errors:
    - Rate limit (429)
    - Server error (5xx)
    - Timeout
    - Connection error
    - Quota exceeded

    Non-recoverable errors (should not trigger fallback):
    - Authentication error (wrong API key)
    - Content filter (prompt blocked)
    - Model error (model not found)
    """
    return error_code in RECOVERABLE_ERRORS
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/testcases/test_recoverable_errors.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add rag/llm/chat_model.py test/testcases/test_recoverable_errors.py
git commit -m "feat: add is_recoverable_error function for fallback detection"
```

---

### Task 3: Implement Fallback Logic in LLM4Tenant

**Files:**
- Modify: `api/db/services/tenant_llm_service.py`
- Test: `test/testcases/test_llm_fallback.py`

**Step 1: Write the failing test**

```python
# test/testcases/test_llm_fallback.py
import pytest
from unittest.mock import Mock, patch, MagicMock
from api.db.services.fallback_service import FallbackConfig, FallbackModels
from api.db.services.tenant_llm_service import FallbackExecutor


class TestFallbackExecutor:
    def test_no_fallback_config_returns_original_result(self):
        """When no fallback is configured, return original result or raise error"""
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=FallbackConfig(api_key="sk-test", fallback=None),
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
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=FallbackConfig(api_key="sk-test", fallback=fallback_models),
        )

        call_count = [0]
        def mock_call(model_name, messages, gen_conf):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (gpt-4o) fails with rate limit
                raise Exception("rate limit exceeded (429)")
            # Second call (gpt-4o-mini) succeeds
            return "Success from fallback"

        with patch.object(executor, '_call_model_with_name', side_effect=mock_call):
            result = executor.execute([{"role": "user", "content": "Hello"}])
            assert result == "Success from fallback"
            assert call_count[0] == 2

    def test_fallback_to_cross_factory_when_all_models_fail(self):
        """Should fallback to another factory when all same-factory models fail"""
        fallback_models = FallbackModels(
            models=["gpt-4o-mini"],
            factories=["DeepSeek"]
        )
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=FallbackConfig(api_key="sk-test", fallback=fallback_models),
        )

        call_count = [0]
        def mock_call(model_name, factory, messages, gen_conf):
            call_count[0] += 1
            if call_count[0] <= 2:
                # OpenAI models fail
                raise Exception("rate limit exceeded")
            # DeepSeek succeeds
            return "Success from DeepSeek"

        with patch.object(executor, '_call_model_with_factory', side_effect=mock_call):
            result = executor.execute([{"role": "user", "content": "Hello"}])
            assert result == "Success from DeepSeek"

    def test_no_fallback_on_auth_error(self):
        """Authentication errors should not trigger fallback"""
        fallback_models = FallbackModels(models=["gpt-4o-mini"])
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=FallbackConfig(api_key="sk-test", fallback=fallback_models),
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
        executor = FallbackExecutor(
            tenant_id="test-tenant",
            llm_type="chat",
            llm_name="gpt-4o",
            fallback_config=FallbackConfig(api_key="sk-test", fallback=fallback_models),
        )

        def mock_fail(*args, **kwargs):
            raise Exception("Service unavailable")

        with patch.object(executor, '_call_model', side_effect=mock_fail):
            with pytest.raises(Exception) as exc_info:
                executor.execute([{"role": "user", "content": "Hello"}])
            assert "Service unavailable" in str(exc_info.value)
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/testcases/test_llm_fallback.py -v
```
Expected: FAIL with "cannot import name 'FallbackExecutor'"

**Step 3: Write minimal implementation**

```python
# Add to api/db/services/tenant_llm_service.py (after imports, before LLM4Tenant class)

import logging
from typing import Optional, Generator, Any
from api.db.services.fallback_service import FallbackConfig, parse_fallback_config
from rag.llm.chat_model import is_recoverable_error, LLMErrorCode


class FallbackExecutor:
    """
    Executes LLM calls with fallback support.
    Priority: original model -> same factory models -> cross factory models
    """

    def __init__(
        self,
        tenant_id: str,
        llm_type: str,
        llm_name: str,
        fallback_config: FallbackConfig,
        lang: str = "Chinese",
        **kwargs
    ):
        self.tenant_id = tenant_id
        self.llm_type = llm_type
        self.original_llm_name = llm_name
        self.fallback_config = fallback_config
        self.lang = lang
        self.kwargs = kwargs
        self._last_error: Optional[Exception] = None

    def execute(self, messages: list, gen_conf: dict = None) -> str:
        """
        Execute chat with fallback logic.
        Try order: original model -> fallback models -> cross-factory models
        """
        gen_conf = gen_conf or {}

        # Try original model first
        try:
            return self._call_model(messages, gen_conf)
        except Exception as e:
            if not self._should_fallback(e):
                raise
            self._last_error = e
            logging.warning(f"Primary model {self.original_llm_name} failed: {e}")

        # Try same-factory fallback models
        if self.fallback_config.has_fallback():
            for model_name in self.fallback_config.fallback.models:
                try:
                    logging.info(f"Fallback to same-factory model: {model_name}")
                    return self._call_model_with_name(model_name, messages, gen_conf)
                except Exception as e:
                    if not self._should_fallback(e):
                        raise
                    self._last_error = e
                    logging.warning(f"Fallback model {model_name} failed: {e}")

            # Try cross-factory fallbacks
            for factory in self.fallback_config.fallback.factories:
                try:
                    logging.info(f"Fallback to cross-factory: {factory}")
                    return self._call_model_with_factory(
                        factory, messages, gen_conf
                    )
                except Exception as e:
                    if not self._should_fallback(e):
                        raise
                    self._last_error = e
                    logging.warning(f"Cross-factory {factory} failed: {e}")

        # All fallbacks failed, raise last error
        if self._last_error:
            raise self._last_error
        raise Exception("All fallback attempts failed")

    def _should_fallback(self, error: Exception) -> bool:
        """Check if error should trigger fallback"""
        error_str = str(error).lower()

        # Check for non-recoverable errors
        non_recoverable_keywords = ["401", "authentication", "unauthorized", "invalid api key", "content filter"]
        for keyword in non_recoverable_keywords:
            if keyword in error_str:
                return False

        # Check for recoverable errors
        recoverable_keywords = ["429", "rate limit", "timeout", "connection", "server error", "503", "502", "500", "quota"]
        for keyword in recoverable_keywords:
            if keyword in error_str:
                return True

        return False

    def _call_model(self, messages: list, gen_conf: dict) -> str:
        """Call the original model"""
        mdl = TenantLLMService.model_instance(
            self.tenant_id,
            self.llm_type,
            self.original_llm_name,
            self.lang,
            **self.kwargs
        )
        result = mdl.chat(None, messages, gen_conf)
        if result.find("**ERROR**") >= 0:
            raise Exception(result)
        return result

    def _call_model_with_name(self, model_name: str, messages: list, gen_conf: dict) -> str:
        """Call a specific model (same factory)"""
        mdl = TenantLLMService.model_instance(
            self.tenant_id,
            self.llm_type,
            model_name,
            self.lang,
            **self.kwargs
        )
        result = mdl.chat(None, messages, gen_conf)
        if result.find("**ERROR**") >= 0:
            raise Exception(result)
        return result

    def _call_model_with_factory(self, factory: str, messages: list, gen_conf: dict) -> str:
        """Call primary model from another factory"""
        # Get the primary model for this factory
        factory_config = TenantLLMService.get_factory_primary_model(
            self.tenant_id, factory, self.llm_type
        )
        if not factory_config:
            raise Exception(f"No configured model found for factory: {factory}")

        mdl = TenantLLMService.model_instance(
            self.tenant_id,
            self.llm_type,
            factory_config["llm_name"],
            self.lang,
            **self.kwargs
        )
        result = mdl.chat(None, messages, gen_conf)
        if result.find("**ERROR**") >= 0:
            raise Exception(result)
        return result
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/testcases/test_llm_fallback.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add api/db/services/tenant_llm_service.py test/testcases/test_llm_fallback.py
git commit -m "feat: implement FallbackExecutor for multi-level LLM fallback"
```

---

### Task 4: Add get_factory_primary_model Service Method

**Files:**
- Modify: `api/db/services/tenant_llm_service.py`
- Test: `test/testcases/test_llm_fallback.py`

**Step 1: Write the failing test**

Add to `test/testcases/test_llm_fallback.py`:

```python
class TestGetFactoryPrimaryModel:
    def test_returns_first_chat_model_for_factory(self):
        """Should return first available chat model for a factory"""
        with patch('api.db.services.tenant_llm_service.TenantLLMService.query') as mock_query:
            mock_query.return_value = [
                Mock(llm_name="deepseek-chat", model_type="chat", api_key="sk-deepseek"),
                Mock(llm_name="deepseek-coder", model_type="chat", api_key="sk-deepseek"),
            ]

            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "DeepSeek", "chat"
            )
            assert result["llm_name"] == "deepseek-chat"

    def test_returns_none_for_unconfigured_factory(self):
        """Should return None if factory has no configured models"""
        with patch('api.db.services.tenant_llm_service.TenantLLMService.query') as mock_query:
            mock_query.return_value = []

            result = TenantLLMService.get_factory_primary_model(
                "test-tenant", "UnknownFactory", "chat"
            )
            assert result is None
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/testcases/test_llm_fallback.py::TestGetFactoryPrimaryModel -v
```
Expected: FAIL

**Step 3: Write minimal implementation**

Add to `TenantLLMService` class in `api/db/services/tenant_llm_service.py`:

```python
@classmethod
@DB.connection_context()
def get_factory_primary_model(cls, tenant_id: str, factory: str, llm_type: str) -> Optional[dict]:
    """
    Get the first available model for a factory.
    Used for cross-factory fallback.
    """
    objs = cls.query(
        tenant_id=tenant_id,
        llm_factory=factory,
        model_type=llm_type,
    )

    # Filter to only return models with valid API keys
    for obj in objs:
        if obj.api_key:
            return {
                "llm_name": obj.llm_name,
                "api_key": obj.api_key,
                "api_base": obj.api_base,
            }

    return None
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/testcases/test_llm_fallback.py::TestGetFactoryPrimaryModel -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add api/db/services/tenant_llm_service.py test/testcases/test_llm_fallback.py
git commit -m "feat: add get_factory_primary_model method for cross-factory fallback"
```

---

### Task 5: Add Fallback API Endpoint

**Files:**
- Modify: `api/apps/llm_app.py`
- Test: `test/testcases/test_web_api/test_llm_app/test_fallback_api.py`

**Step 1: Write the failing test**

```python
# test/testcases/test_web_api/test_llm_app/test_fallback_api.py
import pytest
from unittest.mock import patch


class TestFallbackConfigAPI:
    @pytest.mark.asyncio
    async def test_set_fallback_config_success(self, auth_client):
        """Should save fallback configuration for a factory"""
        response = await auth_client.post(
            "/api/llm/set_fallback_config",
            json={
                "llm_factory": "OpenAI",
                "fallback_models": ["gpt-4o-mini", "gpt-3.5-turbo"],
                "fallback_factories": ["DeepSeek", "Qwen"],
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_get_fallback_config(self, auth_client):
        """Should retrieve fallback configuration for a factory"""
        # First set the config
        await auth_client.post(
            "/api/llm/set_fallback_config",
            json={
                "llm_factory": "OpenAI",
                "fallback_models": ["gpt-4o-mini"],
                "fallback_factories": ["DeepSeek"],
            }
        )

        # Then get it
        response = await auth_client.get(
            "/api/llm/get_fallback_config",
            params={"llm_factory": "OpenAI"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["fallback_models"] == ["gpt-4o-mini"]
        assert data["data"]["fallback_factories"] == ["DeepSeek"]

    @pytest.mark.asyncio
    async def test_get_fallback_config_not_found(self, auth_client):
        """Should return empty config for unconfigured factory"""
        response = await auth_client.get(
            "/api/llm/get_fallback_config",
            params={"llm_factory": "UnknownFactory"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["fallback_models"] == []
        assert data["data"]["fallback_factories"] == []
```

**Step 2: Run test to verify it fails**

```bash
uv run pytest test/testcases/test_web_api/test_llm_app/test_fallback_api.py -v
```
Expected: FAIL with 404

**Step 3: Write minimal implementation**

Add to `api/apps/llm_app.py`:

```python
@manager.route("/set_fallback_config", methods=["POST"])  # noqa: F821
@login_required
@validate_request("llm_factory")
async def set_fallback_config():
    """Set fallback configuration for a factory"""
    from api.db.services.fallback_service import FallbackConfig, FallbackModels
    from api.db.db_models import TenantLLM

    req = await get_request_json()
    factory = req["llm_factory"]
    fallback_models = req.get("fallback_models", [])
    fallback_factories = req.get("fallback_factories", [])

    # Get existing API key for this factory
    existing = TenantLLMService.query(
        tenant_id=current_user.id,
        llm_factory=factory,
    )

    if not existing:
        return get_data_error_result(message=f"No API key configured for {factory}")

    # Update all models for this factory with new fallback config
    for record in existing:
        parsed = parse_fallback_config(record.api_key) if record.api_key else FallbackConfig(api_key="")

        # Build new config
        new_config = FallbackConfig(
            api_key=parsed.api_key,
            fallback=FallbackModels(
                models=fallback_models,
                factories=fallback_factories,
            )
        )

        TenantLLMService.filter_update(
            [TenantLLM.tenant_id == current_user.id,
             TenantLLM.llm_factory == factory,
             TenantLLM.llm_name == record.llm_name],
            {"api_key": new_config.to_json_str()}
        )

    return get_json_result(data=True)


@manager.route("/get_fallback_config", methods=["GET"])  # noqa: F821
@login_required
async def get_fallback_config():
    """Get fallback configuration for a factory"""
    from api.db.services.fallback_service import parse_fallback_config

    factory = request.args.get("llm_factory")

    records = TenantLLMService.query(
        tenant_id=current_user.id,
        llm_factory=factory,
    )

    if not records:
        return get_json_result(data={"fallback_models": [], "fallback_factories": []})

    # Parse fallback config from first record
    parsed = parse_fallback_config(records[0].api_key or "")

    if parsed.fallback:
        return get_json_result(data={
            "fallback_models": parsed.fallback.models,
            "fallback_factories": parsed.fallback.factories,
        })

    return get_json_result(data={"fallback_models": [], "fallback_factories": []})
```

**Step 4: Run test to verify it passes**

```bash
uv run pytest test/testcases/test_web_api/test_llm_app/test_fallback_api.py -v
```
Expected: PASS

**Step 5: Commit**

```bash
git add api/apps/llm_app.py test/testcases/test_web_api/test_llm_app/test_fallback_api.py
git commit -m "feat: add API endpoints for fallback configuration"
```

---

## Part 2: Frontend Implementation

### Task 6: Add Fallback API Service Functions

**Files:**
- Modify: `web/src/services/user-service.ts`
- Modify: `web/src/hooks/use-llm-request.tsx`

**Step 1: Add API functions to user-service.ts**

```typescript
// Add to web/src/services/user-service.ts

export interface FallbackConfig {
  fallback_models: string[];
  fallback_factories: string[];
}

export interface SetFallbackConfigParams {
  llm_factory: string;
  fallback_models?: string[];
  fallback_factories?: string[];
}

const setFallbackConfig = (params: SetFallbackConfigParams) =>
  request.post('/api/llm/set_fallback_config', params);

const getFallbackConfig = (llm_factory: string) =>
  request.get('/api/llm/get_fallback_config', { params: { llm_factory } });

// Add to userService export
export default {
  // ... existing methods
  setFallbackConfig,
  getFallbackConfig,
};
```

**Step 2: Add React Query hooks to use-llm-request.tsx**

```typescript
// Add to web/src/hooks/use-llm-request.tsx

export const useSetFallbackConfig = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params: SetFallbackConfigParams) => {
      const { data } = await userService.setFallbackConfig(params);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [LLMApiAction.MyLlmList] });
    },
  });
};

export const useGetFallbackConfig = (llmFactory: string) => {
  return useQuery<FallbackConfig>({
    queryKey: ['fallbackConfig', llmFactory],
    queryFn: async () => {
      const { data } = await userService.getFallbackConfig(llmFactory);
      return data?.data ?? { fallback_models: [], fallback_factories: [] };
    },
    enabled: !!llmFactory,
  });
};
```

**Step 3: Commit**

```bash
git add web/src/services/user-service.ts web/src/hooks/use-llm-request.tsx
git commit -m "feat: add frontend API functions for fallback configuration"
```

---

### Task 7: Create Fallback Configuration Modal

**Files:**
- Create: `web/src/pages/user-setting/setting-model/modal/fallback-config-modal/index.tsx`

**Step 1: Create the modal component**

```tsx
// web/src/pages/user-setting/setting-model/modal/fallback-config-modal/index.tsx
import { IModalManagerChildrenProps } from '@/components/modal-manager';
import { Button } from '@/components/ui/button';
import { Modal } from '@/components/ui/modal/modal';
import { useGetFallbackConfig, useSetFallbackConfig } from '@/hooks/use-llm-request';
import { useFetchLlmList } from '@/hooks/use-llm-request';
import { LlmModelType } from '@/constants/knowledge';
import { getRealModelName } from '@/utils/llm-util';
import { useEffect, useState } from 'react';
import { Select, Space, Tag, message } from 'antd';
import { useTranslate } from '@/hooks/common-hooks';

interface IProps extends Omit<IModalManagerChildrenProps, 'showModal'> {
  llmFactory: string;
}

const FallbackConfigModal = ({ visible, hideModal, llmFactory }: IProps) => {
  const { t } = useTranslate('setting');
  const [fallbackModels, setFallbackModels] = useState<string[]>([]);
  const [fallbackFactories, setFallbackFactories] = useState<string[]>([]);

  const { data: config, isLoading: configLoading } = useGetFallbackConfig(llmFactory);
  const { mutate: saveConfig, isPending: saving } = useSetFallbackConfig();

  // Get available models for this factory
  const llmList = useFetchLlmList(LlmModelType.Chat);
  const factoryModels = llmList[llmFactory] || [];

  // Get all factories that user has configured
  const configuredFactories = Object.keys(llmList).filter(
    (f) => f !== llmFactory && llmList[f]?.length > 0
  );

  useEffect(() => {
    if (config) {
      setFallbackModels(config.fallback_models || []);
      setFallbackFactories(config.fallback_factories || []);
    }
  }, [config]);

  const handleOk = async () => {
    saveConfig(
      {
        llm_factory: llmFactory,
        fallback_models: fallbackModels,
        fallback_factories: fallbackFactories,
      },
      {
        onSuccess: () => {
          message.success(t('savedSuccessfully'));
          hideModal();
        },
        onError: () => {
          message.error(t('saveFailed'));
        },
      }
    );
  };

  return (
    <Modal
      title={`Fallback Configuration - ${llmFactory}`}
      open={visible}
      onOpenChange={(open) => !open && hideModal()}
      onOk={handleOk}
      onCancel={hideModal}
      confirmLoading={saving}
      okText={t('save')}
      cancelText={t('cancel')}
      className="!w-[600px]"
    >
      <div className="space-y-6 py-4">
        {/* Same-factory fallback models */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Fallback Models (Same Factory)
          </label>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder="Select models to fallback to within same factory"
            value={fallbackModels}
            onChange={setFallbackModels}
            options={factoryModels.map((m: any) => ({
              label: getRealModelName(m.llm_name),
              value: m.llm_name,
            }))}
          />
          <p className="text-xs text-text-muted mt-1">
            When rate limited, try these models from {llmFactory} first
          </p>
        </div>

        {/* Cross-factory fallback */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Fallback Factories (Cross-Factory)
          </label>
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            placeholder="Select other factories to fallback to"
            value={fallbackFactories}
            onChange={setFallbackFactories}
            options={configuredFactories.map((f) => ({
              label: f,
              value: f,
            }))}
          />
          <p className="text-xs text-text-muted mt-1">
            When all same-factory models fail, try the primary model from these factories
          </p>
        </div>

        {/* Current configuration preview */}
        {(fallbackModels.length > 0 || fallbackFactories.length > 0) && (
          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Fallback Order
            </label>
            <div className="bg-slate-50 rounded p-3 text-sm">
              <div className="flex flex-wrap gap-2">
                <Tag color="blue">{llmFactory} (Primary)</Tag>
                {fallbackModels.map((m) => (
                  <Tag key={m} color="green">{getRealModelName(m)}</Tag>
                ))}
                {fallbackFactories.map((f) => (
                  <Tag key={f} color="orange">{f}</Tag>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default FallbackConfigModal;
```

**Step 2: Commit**

```bash
git add web/src/pages/user-setting/setting-model/modal/fallback-config-modal/index.tsx
git commit -m "feat: add fallback configuration modal component"
```

---

### Task 8: Integrate Fallback Modal into Model Settings

**Files:**
- Modify: `web/src/pages/user-setting/setting-model/components/used-model.tsx`
- Modify: `web/src/pages/user-setting/setting-model/hooks.tsx`
- Modify: `web/src/pages/user-setting/setting-model/index.tsx`

**Step 1: Add fallback modal hook to hooks.tsx**

```typescript
// Add to web/src/pages/user-setting/setting-model/hooks.tsx

export const useSubmitFallbackConfig = () => {
  const {
    visible: fallbackVisible,
    hideModal: hideFallbackModal,
    showModal: showFallbackModal,
  } = useSetModalState();
  const [selectedFactory, setSelectedFactory] = useState<string>('');

  const onShowFallbackModal = useCallback((factory: string) => {
    setSelectedFactory(factory);
    showFallbackModal();
  }, [showFallbackModal]);

  return {
    fallbackVisible,
    hideFallbackModal,
    showFallbackModal: onShowFallbackModal,
    selectedFactory,
  };
};
```

**Step 2: Add fallback button to used-model.tsx**

```tsx
// Add button in used-model.tsx after the edit/delete buttons
<Button
  type="text"
  size="small"
  onClick={() => onShowFallback(record.llm_factory)}
  icon={<SettingOutlined />}
>
  Fallback
</Button>
```

**Step 3: Integrate modal in index.tsx**

```tsx
// Add to imports
import FallbackConfigModal from './modal/fallback-config-modal';

// Add hook usage
const {
  fallbackVisible,
  hideFallbackModal,
  showFallbackModal,
  selectedFactory,
} = useSubmitFallbackConfig();

// Add modal in JSX (after other modals)
<FallbackConfigModal
  visible={fallbackVisible}
  hideModal={hideFallbackModal}
  llmFactory={selectedFactory}
/>
```

**Step 4: Commit**

```bash
git add web/src/pages/user-setting/setting-model/components/used-model.tsx web/src/pages/user-setting/setting-model/hooks.tsx web/src/pages/user-setting/setting-model/index.tsx
git commit -m "feat: integrate fallback configuration modal into model settings"
```

---

### Task 9: Add i18n Translations

**Files:**
- Modify: `web/src/locales/en-us/setting.json`
- Modify: `web/src/locales/zh-cn/setting.json`

**Step 1: Add English translations**

```json
{
  "fallback": {
    "title": "Fallback Configuration",
    "models": "Fallback Models",
    "modelsDesc": "When rate limited, try these models from the same factory first",
    "factories": "Fallback Factories",
    "factoriesDesc": "When all same-factory models fail, try the primary model from these factories",
    "order": "Fallback Order",
    "savedSuccessfully": "Fallback configuration saved successfully",
    "saveFailed": "Failed to save fallback configuration"
  }
}
```

**Step 2: Add Chinese translations**

```json
{
  "fallback": {
    "title": "备用配置",
    "models": "备用模型",
    "modelsDesc": "当触发速率限制时，优先尝试同厂商的这些模型",
    "factories": "备用厂商",
    "factoriesDesc": "当同厂商所有模型都失败时，尝试这些厂商的首选模型",
    "order": "回退顺序",
    "savedSuccessfully": "备用配置保存成功",
    "saveFailed": "备用配置保存失败"
  }
}
```

**Step 3: Commit**

```bash
git add web/src/locales/en-us/setting.json web/src/locales/zh-cn/setting.json
git commit -m "feat: add i18n translations for fallback configuration"
```

---

## Task 10: Integration Test and Documentation

**Files:**
- Create: `test/testcases/test_llm_fallback_integration.py`
- Create: `docs/guides/llm-fallback.md`

**Step 1: Write integration test**

```python
# test/testcases/test_llm_fallback_integration.py
"""
Integration test for LLM fallback mechanism.

This test verifies the complete fallback flow:
1. Primary model fails with rate limit
2. Fallback to same-factory model
3. If all same-factory models fail, fallback to cross-factory
"""
import pytest
from unittest.mock import patch, Mock


@pytest.mark.integration
class TestLLMFallbackIntegration:
    @pytest.mark.asyncio
    async def test_complete_fallback_flow(self, test_tenant, mock_llm_responses):
        """Test complete fallback flow from primary to cross-factory"""
        # This would be a real integration test with mocked LLM responses
        pass

    @pytest.mark.asyncio
    async def test_fallback_logs_properly(self, test_tenant, caplog):
        """Test that fallback attempts are properly logged"""
        pass
```

**Step 2: Write user documentation**

```markdown
# docs/guides/llm-fallback.md

# LLM Fallback Configuration Guide

## Overview

RAGFlow supports multi-level fallback for LLM calls to handle rate limits and other recoverable errors automatically.

## Configuration

### Via Frontend UI

1. Go to **Settings > Model Providers**
2. Click the **Fallback** button on a configured provider
3. Select fallback models (same factory) and/or fallback factories (cross-factory)
4. Save the configuration

### Via API

```bash
curl -X POST /api/llm/set_fallback_config \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "llm_factory": "OpenAI",
    "fallback_models": ["gpt-4o-mini", "gpt-3.5-turbo"],
    "fallback_factories": ["DeepSeek", "Qwen"]
  }'
```

## Fallback Order

1. Primary model (e.g., gpt-4o)
2. Same-factory fallback models (e.g., gpt-4o-mini, gpt-3.5-turbo)
3. Cross-factory fallbacks (e.g., DeepSeek primary model, Qwen primary model)

## Error Handling

Fallback is triggered for these errors:
- Rate limit (429)
- Server errors (500, 502, 503)
- Timeout
- Connection errors
- Quota exceeded

Fallback is NOT triggered for:
- Authentication errors (401)
- Content filter errors
- Model not found errors
```

**Step 3: Commit**

```bash
git add test/testcases/test_llm_fallback_integration.py docs/guides/llm-fallback.md
git commit -m "docs: add integration tests and user guide for LLM fallback"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Fallback config parser | `api/db/services/fallback_service.py` |
| 2 | Recoverable error detection | `rag/llm/chat_model.py` |
| 3 | FallbackExecutor class | `api/db/services/tenant_llm_service.py` |
| 4 | get_factory_primary_model | `api/db/services/tenant_llm_service.py` |
| 5 | API endpoints | `api/apps/llm_app.py` |
| 6 | Frontend API functions | `web/src/services/user-service.ts` |
| 7 | Fallback config modal | `web/src/pages/user-setting/setting-model/modal/` |
| 8 | Integrate modal | `web/src/pages/user-setting/setting-model/` |
| 9 | i18n translations | `web/src/locales/` |
| 10 | Integration tests & docs | `test/`, `docs/` |
