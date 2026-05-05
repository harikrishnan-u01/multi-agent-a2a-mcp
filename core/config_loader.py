"""
Central config loader — merges config/settings.yaml + .env into a typed AppConfig.
Every module imports get_config() from here instead of reading files themselves.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent


class ServerConfig:
    def __init__(self, d: dict):
        self.mcp_port: int = d.get("mcp_port", 8000)
        self.wellness_api_port: int = d.get("wellness_api_port", 8001)
        self.learning_api_port: int = d.get("learning_api_port", 8002)


class DomainAgentsConfig:
    def __init__(self, d: dict):
        self.wellness_url: str = d.get("wellness_url", "http://localhost:9001")
        self.learning_url: str = d.get("learning_url", "http://localhost:9002")
        self.planner_url: str = d.get("planner_url", "http://localhost:9003")


class ModelsConfig:
    def __init__(self, d: dict):
        self.primary: str = os.getenv("OLLAMA_MODEL") or d.get("primary", "llama3.2")
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL") or d.get("ollama_base_url", "http://localhost:11434")
        self.temperature: float = d.get("temperature", 0.7)
        self.intent_temperature: float = d.get("intent_temperature", 0.0)


class LoggingConfig:
    def __init__(self, d: dict):
        self.show_json_payloads: bool = d.get("show_json_payloads", True)
        self.agent_colors: dict[str, str] = d.get("agent_colors", {})


class AppConfig:
    def __init__(self, raw: dict):
        self.server = ServerConfig(raw.get("server", {}))
        self.models = ModelsConfig(raw.get("models", {}))
        self.logging = LoggingConfig(raw.get("logging", {}))
        self.tools: list[dict[str, Any]] = raw.get("tools", [])
        self.domain_agents = DomainAgentsConfig(raw.get("domain_agents", {}))


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    config_path = _ROOT / "config" / "settings.yaml"
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    return AppConfig(raw)
