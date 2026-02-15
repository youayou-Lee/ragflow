#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
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
import os
import json
import logging
from peewee import IntegrityError
from langfuse import Langfuse
from common import settings
from common.constants import MINERU_DEFAULT_CONFIG, MINERU_ENV_KEYS, PADDLEOCR_DEFAULT_CONFIG, PADDLEOCR_ENV_KEYS, LLMType
from api.db.db_models import DB, LLMFactories, TenantLLM
from api.db.services.common_service import CommonService
from api.db.services.langfuse_service import TenantLangfuseService
from api.db.services.user_service import TenantService
from rag.llm import ChatModel, CvModel, EmbeddingModel, OcrModel, RerankModel, Seq2txtModel, TTSModel


class LLMFactoriesService(CommonService):
    model = LLMFactories


class TenantLLMService(CommonService):
    model = TenantLLM

    @classmethod
    @DB.connection_context()
    def get_api_key(cls, tenant_id, model_name):
        mdlnm, fid = TenantLLMService.split_model_name_and_factory(model_name)
        if not fid:
            objs = cls.query(tenant_id=tenant_id, llm_name=mdlnm)
        else:
            objs = cls.query(tenant_id=tenant_id, llm_name=mdlnm, llm_factory=fid)

        if (not objs) and fid:
            if fid == "LocalAI":
                mdlnm += "___LocalAI"
            elif fid == "HuggingFace":
                mdlnm += "___HuggingFace"
            elif fid == "OpenAI-API-Compatible":
                mdlnm += "___OpenAI-API"
            elif fid == "VLLM":
                mdlnm += "___VLLM"
            objs = cls.query(tenant_id=tenant_id, llm_name=mdlnm, llm_factory=fid)
        if not objs:
            return None
        return objs[0]

    @classmethod
    @DB.connection_context()
    def get_my_llms(cls, tenant_id):
        fields = [cls.model.llm_factory, LLMFactories.logo, LLMFactories.tags, cls.model.model_type, cls.model.llm_name, cls.model.used_tokens, cls.model.status]
        objs = cls.model.select(*fields).join(LLMFactories, on=(cls.model.llm_factory == LLMFactories.name)).where(cls.model.tenant_id == tenant_id, ~cls.model.api_key.is_null()).dicts()

        return list(objs)

    @staticmethod
    def split_model_name_and_factory(model_name):
        arr = model_name.split("@")
        if len(arr) < 2:
            return model_name, None
        if len(arr) > 2:
            return "@".join(arr[0:-1]), arr[-1]

        # model name must be xxx@yyy
        try:
            model_factories = settings.FACTORY_LLM_INFOS
            model_providers = set([f["name"] for f in model_factories])
            if arr[-1] not in model_providers:
                return model_name, None
            return arr[0], arr[-1]
        except Exception as e:
            logging.exception(f"TenantLLMService.split_model_name_and_factory got exception: {e}")
        return model_name, None

    @classmethod
    @DB.connection_context()
    def get_model_config(cls, tenant_id, llm_type, llm_name=None):
        from api.db.services.llm_service import LLMService

        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            raise LookupError("Tenant not found")

        if llm_type == LLMType.EMBEDDING.value:
            mdlnm = tenant.embd_id if not llm_name else llm_name
        elif llm_type == LLMType.SPEECH2TEXT.value:
            mdlnm = tenant.asr_id if not llm_name else llm_name
        elif llm_type == LLMType.IMAGE2TEXT.value:
            mdlnm = tenant.img2txt_id if not llm_name else llm_name
        elif llm_type == LLMType.CHAT.value:
            mdlnm = tenant.llm_id if not llm_name else llm_name
        elif llm_type == LLMType.RERANK:
            mdlnm = tenant.rerank_id if not llm_name else llm_name
        elif llm_type == LLMType.TTS:
            mdlnm = tenant.tts_id if not llm_name else llm_name
        elif llm_type == LLMType.OCR:
            if not llm_name:
                raise LookupError("OCR model name is required")
            mdlnm = llm_name
        else:
            assert False, "LLM type error"

        model_config = cls.get_api_key(tenant_id, mdlnm)
        mdlnm, fid = TenantLLMService.split_model_name_and_factory(mdlnm)
        if not model_config:  # for some cases seems fid mismatch
            model_config = cls.get_api_key(tenant_id, mdlnm)
        if model_config:
            model_config = model_config.to_dict()
        elif llm_type == LLMType.EMBEDDING and fid == "Builtin" and "tei-" in os.getenv("COMPOSE_PROFILES", "") and mdlnm == os.getenv("TEI_MODEL", ""):
            embedding_cfg = settings.EMBEDDING_CFG
            model_config = {"llm_factory": "Builtin", "api_key": embedding_cfg["api_key"], "llm_name": mdlnm, "api_base": embedding_cfg["base_url"]}
        else:
            raise LookupError(f"Model({mdlnm}@{fid}) not authorized")

        llm = LLMService.query(llm_name=mdlnm) if not fid else LLMService.query(llm_name=mdlnm, fid=fid)
        if not llm and fid:  # for some cases seems fid mismatch
            llm = LLMService.query(llm_name=mdlnm)
        if llm:
            model_config["is_tools"] = llm[0].is_tools
        return model_config

    @classmethod
    @DB.connection_context()
    def model_instance(cls, tenant_id, llm_type, llm_name=None, lang="Chinese", **kwargs):
        model_config = TenantLLMService.get_model_config(tenant_id, llm_type, llm_name)
        kwargs.update({"provider": model_config["llm_factory"]})
        if llm_type == LLMType.EMBEDDING.value:
            if model_config["llm_factory"] not in EmbeddingModel:
                return None
            return EmbeddingModel[model_config["llm_factory"]](model_config["api_key"], model_config["llm_name"], base_url=model_config["api_base"])

        elif llm_type == LLMType.RERANK:
            if model_config["llm_factory"] not in RerankModel:
                return None
            return RerankModel[model_config["llm_factory"]](model_config["api_key"], model_config["llm_name"], base_url=model_config["api_base"])

        elif llm_type == LLMType.IMAGE2TEXT.value:
            if model_config["llm_factory"] not in CvModel:
                return None
            return CvModel[model_config["llm_factory"]](model_config["api_key"], model_config["llm_name"], lang, base_url=model_config["api_base"], **kwargs)

        elif llm_type == LLMType.CHAT.value:
            if model_config["llm_factory"] not in ChatModel:
                return None
            return ChatModel[model_config["llm_factory"]](model_config["api_key"], model_config["llm_name"], base_url=model_config["api_base"], **kwargs)

        elif llm_type == LLMType.SPEECH2TEXT:
            if model_config["llm_factory"] not in Seq2txtModel:
                return None
            return Seq2txtModel[model_config["llm_factory"]](key=model_config["api_key"], model_name=model_config["llm_name"], lang=lang, base_url=model_config["api_base"])
        elif llm_type == LLMType.TTS:
            if model_config["llm_factory"] not in TTSModel:
                return None
            return TTSModel[model_config["llm_factory"]](
                model_config["api_key"],
                model_config["llm_name"],
                base_url=model_config["api_base"],
            )

        elif llm_type == LLMType.OCR:
            if model_config["llm_factory"] not in OcrModel:
                return None
            return OcrModel[model_config["llm_factory"]](
                key=model_config["api_key"],
                model_name=model_config["llm_name"],
                base_url=model_config.get("api_base", ""),
                **kwargs,
            )

        return None

    @classmethod
    @DB.connection_context()
    def increase_usage(cls, tenant_id, llm_type, used_tokens, llm_name=None):
        e, tenant = TenantService.get_by_id(tenant_id)
        if not e:
            logging.error(f"Tenant not found: {tenant_id}")
            return 0

        llm_map = {
            LLMType.EMBEDDING.value: tenant.embd_id if not llm_name else llm_name,
            LLMType.SPEECH2TEXT.value: tenant.asr_id,
            LLMType.IMAGE2TEXT.value: tenant.img2txt_id,
            LLMType.CHAT.value: tenant.llm_id if not llm_name else llm_name,
            LLMType.RERANK.value: tenant.rerank_id if not llm_name else llm_name,
            LLMType.TTS.value: tenant.tts_id if not llm_name else llm_name,
            LLMType.OCR.value: llm_name,
        }

        mdlnm = llm_map.get(llm_type)
        if mdlnm is None:
            logging.error(f"LLM type error: {llm_type}")
            return 0

        llm_name, llm_factory = TenantLLMService.split_model_name_and_factory(mdlnm)

        try:
            num = (
                cls.model.update(used_tokens=cls.model.used_tokens + used_tokens)
                .where(cls.model.tenant_id == tenant_id, cls.model.llm_name == llm_name, cls.model.llm_factory == llm_factory if llm_factory else True)
                .execute()
            )
        except Exception:
            logging.exception("TenantLLMService.increase_usage got exception,Failed to update used_tokens for tenant_id=%s, llm_name=%s", tenant_id, llm_name)
            return 0

        return num

    @classmethod
    @DB.connection_context()
    def get_openai_models(cls):
        objs = cls.model.select().where((cls.model.llm_factory == "OpenAI"), ~(cls.model.llm_name == "text-embedding-3-small"), ~(cls.model.llm_name == "text-embedding-3-large")).dicts()
        return list(objs)

    @classmethod
    def _collect_mineru_env_config(cls) -> dict | None:
        cfg = MINERU_DEFAULT_CONFIG
        found = False
        for key in MINERU_ENV_KEYS:
            val = os.environ.get(key)
            if val:
                found = True
                cfg[key] = val
        return cfg if found else None

    @classmethod
    @DB.connection_context()
    def ensure_mineru_from_env(cls, tenant_id: str) -> str | None:
        """
        Ensure a MinerU OCR model exists for the tenant if env variables are present.
        Return the existing or newly created llm_name, or None if env not set.
        """
        cfg = cls._collect_mineru_env_config()
        if not cfg:
            return None

        saved_mineru_models = cls.query(tenant_id=tenant_id, llm_factory="MinerU", model_type=LLMType.OCR.value)

        def _parse_api_key(raw: str) -> dict:
            try:
                return json.loads(raw or "{}")
            except Exception:
                return {}

        for item in saved_mineru_models:
            api_cfg = _parse_api_key(item.api_key)
            normalized = {k: api_cfg.get(k, MINERU_DEFAULT_CONFIG.get(k)) for k in MINERU_ENV_KEYS}
            if normalized == cfg:
                return item.llm_name

        used_names = {item.llm_name for item in saved_mineru_models}
        idx = 1
        base_name = "mineru-from-env"
        while True:
            candidate = f"{base_name}-{idx}"
            if candidate in used_names:
                idx += 1
                continue

            try:
                cls.save(
                    tenant_id=tenant_id,
                    llm_factory="MinerU",
                    llm_name=candidate,
                    model_type=LLMType.OCR.value,
                    api_key=json.dumps(cfg),
                    api_base="",
                    max_tokens=0,
                )
                return candidate
            except IntegrityError:
                logging.warning("MinerU env model %s already exists for tenant %s, retry with next name", candidate, tenant_id)
                used_names.add(candidate)
                idx += 1
                continue

    @classmethod
    def _collect_paddleocr_env_config(cls) -> dict | None:
        cfg = PADDLEOCR_DEFAULT_CONFIG
        found = False
        for key in PADDLEOCR_ENV_KEYS:
            val = os.environ.get(key)
            if val:
                found = True
                cfg[key] = val
        return cfg if found else None

    @classmethod
    @DB.connection_context()
    def ensure_paddleocr_from_env(cls, tenant_id: str) -> str | None:
        """
        Ensure a PaddleOCR model exists for the tenant if env variables are present.
        Return the existing or newly created llm_name, or None if env not set.
        """
        cfg = cls._collect_paddleocr_env_config()
        if not cfg:
            return None

        saved_paddleocr_models = cls.query(tenant_id=tenant_id, llm_factory="PaddleOCR", model_type=LLMType.OCR.value)

        def _parse_api_key(raw: str) -> dict:
            try:
                return json.loads(raw or "{}")
            except Exception:
                return {}

        for item in saved_paddleocr_models:
            api_cfg = _parse_api_key(item.api_key)
            normalized = {k: api_cfg.get(k, PADDLEOCR_DEFAULT_CONFIG.get(k)) for k in PADDLEOCR_ENV_KEYS}
            if normalized == cfg:
                return item.llm_name

        used_names = {item.llm_name for item in saved_paddleocr_models}
        idx = 1
        base_name = "paddleocr-from-env"
        while True:
            candidate = f"{base_name}-{idx}"
            if candidate in used_names:
                idx += 1
                continue

            try:
                cls.save(
                    tenant_id=tenant_id,
                    llm_factory="PaddleOCR",
                    llm_name=candidate,
                    model_type=LLMType.OCR.value,
                    api_key=json.dumps(cfg),
                    api_base="",
                    max_tokens=0,
                )
                return candidate
            except IntegrityError:
                logging.warning("PaddleOCR env model %s already exists for tenant %s, retry with next name", candidate, tenant_id)
                used_names.add(candidate)
                idx += 1
                continue

    @classmethod
    @DB.connection_context()
    def delete_by_tenant_id(cls, tenant_id):
        return cls.model.delete().where(cls.model.tenant_id == tenant_id).execute()

    @staticmethod
    def llm_id2llm_type(llm_id: str) -> str | None:
        from api.db.services.llm_service import LLMService

        llm_id, *_ = TenantLLMService.split_model_name_and_factory(llm_id)
        llm_factories = settings.FACTORY_LLM_INFOS
        for llm_factory in llm_factories:
            for llm in llm_factory["llm"]:
                if llm_id == llm["llm_name"]:
                    return llm["model_type"].split(",")[-1]

        for llm in LLMService.query(llm_name=llm_id):
            return llm.model_type

        llm = TenantLLMService.get_or_none(llm_name=llm_id)
        if llm:
            return llm.model_type
        for llm in TenantLLMService.query(llm_name=llm_id):
            return llm.model_type
        return None

    @classmethod
    @DB.connection_context()
    def get_factory_primary_model(cls, tenant_id: str, factory: str, llm_type: str) -> dict | None:
        """
        Get the first available model for a factory.
        Used for cross-factory fallback.

        Args:
            tenant_id: The tenant ID
            factory: The LLM factory name
            llm_type: The model type (chat, embedding, etc.)

        Returns:
            Dictionary with llm_name, api_key, api_base or None if not found
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
        fallback_config,
        lang: str = "Chinese",
        **kwargs
    ):
        from api.db.services.fallback_service import FallbackConfig
        self.tenant_id = tenant_id
        self.llm_type = llm_type
        self.original_llm_name = llm_name
        self.fallback_config = fallback_config
        self.lang = lang
        self.kwargs = kwargs
        self._last_error: Exception | None = None

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


class LLM4Tenant:
    def __init__(self, tenant_id, llm_type, llm_name=None, lang="Chinese", **kwargs):
        self.tenant_id = tenant_id
        self.llm_type = llm_type
        self.llm_name = llm_name
        self.mdl = TenantLLMService.model_instance(tenant_id, llm_type, llm_name, lang=lang, **kwargs)
        assert self.mdl, "Can't find model for {}/{}/{}".format(tenant_id, llm_type, llm_name)
        model_config = TenantLLMService.get_model_config(tenant_id, llm_type, llm_name)
        self.max_length = model_config.get("max_tokens", 8192)

        self.is_tools = model_config.get("is_tools", False)
        self.verbose_tool_use = kwargs.get("verbose_tool_use")

        langfuse_keys = TenantLangfuseService.filter_by_tenant(tenant_id=tenant_id)
        self.langfuse = None
        if langfuse_keys:
            langfuse = Langfuse(public_key=langfuse_keys.public_key, secret_key=langfuse_keys.secret_key, host=langfuse_keys.host)
            try:
                if langfuse.auth_check():
                    self.langfuse = langfuse
                    trace_id = self.langfuse.create_trace_id()
                    self.trace_context = {"trace_id": trace_id}
            except Exception:
                # Skip langfuse tracing if connection fails
                pass
