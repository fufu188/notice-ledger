"""Offline-only LLM configuration. Credentials live in the environment, never on disk.

Scope guard (user decision 2026-11-09, CONFIRM.md D2a):
this key is for OFFLINE ASSET CONSTRUCTION and the baseline control group ONLY.
The runtime answer path stays zero-dependency by default; --llm is an explicit
opt-in switch and is never enabled by the demo server.

Defaults are transcribed from the official docs (verified 2026-11-09):
https://api-docs.deepseek.com/zh-cn/  ->  base_url https://api.deepseek.com
                                          models  deepseek-flash / deepseek-v4-pro
Do NOT "correct" these from memory: the earlier model name deepseek-chat is not
what the current docs list.
"""
import os

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"


def resolve():
    """Return (api_key, base_url, model). The key is read, never logged or stored."""
    key = (
        os.environ.get("LLM_API_KEY", "").strip()
        or os.environ.get("DEEPSEEK_API_KEY", "").strip()
    )
    base = os.environ.get("LLM_BASE_URL", "").strip() or DEFAULT_BASE_URL
    model = os.environ.get("LLM_MODEL", "").strip() or DEFAULT_MODEL
    return key, base, model


def available():
    return bool(resolve()[0])


def online_allowed():
    """Hard gate for the runtime answer path (user decision: offline-only key).

    The key may be used by offline build tools at any time. It may generate a
    runtime answer ONLY when this env var is explicitly set. Default = denied,
    so a stray --llm flag or a crafted /ask request cannot silently turn the
    demo into a cloud-dependent system and break the 10-minute reproduction.
    """
    return os.environ.get("ALLOW_ONLINE_LLM", "").strip().lower() in ("1", "true", "yes")


def endpoint(base=None):
    base = base or resolve()[1]
    return base.rstrip("/") + "/chat/completions"
