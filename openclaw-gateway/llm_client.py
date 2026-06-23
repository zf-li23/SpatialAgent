# ============================================================
# SpatialAgent — LLM 客户端工厂
# 参考: Biomni 的 get_llm() 多提供商工厂模式
#       deepseek-v4-for-copilot 的 DeepSeek API 适配
# ============================================================

import os
import sys
import json
import logging
from typing import Optional

logger = logging.getLogger("spatialagent.llm")

# 尝试导入 openai
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class LLMClient:
    """统一的 LLM 客户端，支持 DeepSeek / OpenAI 兼容 API"""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1",
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        # API Key 多层回退策略（参考 deepseek-v4-for-copilot 的 AuthManager）
        self.api_key = (
            api_key
            or os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or ""
        )
        self.base_url = base_url

        if OpenAI is None:
            raise ImportError("请安装 openai: pip install openai")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=120.0,
        )

    def chat(
        self,
        messages: list[dict],
        response_format: Optional[dict] = None,
        stream: bool = False,
    ) -> str:
        """发送聊天请求，返回文本响应"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        if stream:
            return self._stream_chat(kwargs)

        try:
            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise

    def chat_json(
        self,
        messages: list[dict],
        fallback: Optional[dict] = None,
    ) -> dict:
        """发送聊天请求，强制返回 JSON"""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,  # JSON 模式用低温
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
            }
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or "{}"
            return json.loads(content)
        except json.JSONDecodeError:
            # 回退：尝试从文本中提取 JSON
            content = response.choices[0].message.content or ""
            return _extract_json(content) or fallback or {}
        except Exception as e:
            logger.error(f"LLM JSON 调用失败: {e}")
            return fallback or {"error": str(e)}

    def _stream_chat(self, kwargs: dict) -> str:
        """流式聊天"""
        kwargs["stream"] = True
        chunks = []
        try:
            response = self.client.chat.completions.create(**kwargs)
            for chunk in response:
                delta = chunk.choices[0].delta
                if delta.content:
                    chunks.append(delta.content)
                    print(delta.content, end="", flush=True)
            print()
            return "".join(chunks)
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise


def _extract_json(text: str) -> Optional[dict]:
    """从文本中提取 JSON 块"""
    import re
    # 尝试匹配 ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # 尝试匹配裸 JSON
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ============================================================
# 工厂函数（兼容无 API Key 时的模拟模式）
# ============================================================

_llm_client: Optional[LLMClient] = None


def get_llm_client(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    config_path: Optional[str] = None,
) -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    # 尝试从配置文件读取
    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")

    # 环境变量优先
    api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    model = model or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    _llm_client = LLMClient(
        model=model,
        api_key=api_key,
    )
    return _llm_client


def has_api_key() -> bool:
    """检查是否有可用的 API Key"""
    return bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"))
