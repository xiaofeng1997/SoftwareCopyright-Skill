#!/usr/bin/env python3
"""Detect which AI coding tool is currently running."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


TOOL_SIGNATURES: dict[str, dict[str, Any]] = {
    "trae-cn": {
        "name": "Trae CN",
        "env_vars": ["TRAE_API_KEY", "TRAE_SESSION"],
        "processes": ["trae", "Trae"],
        "files": ["~/.trae/config.json"],
        "description": "字节跳动出品的 AI 编程 IDE",
    },
    "opencode": {
        "name": "OpenCode",
        "env_vars": ["OPENCODE_API_KEY"],
        "processes": ["opencode"],
        "files": [],
        "description": "开源 AI 代码助手",
    },
    "cursor": {
        "name": "Cursor",
        "env_vars": ["CURSOR_API_KEY"],
        "processes": ["cursor", "Cursor"],
        "files": ["~/.cursor/settings.json"],
        "description": "AI 代码编辑器",
    },
    "claude-code": {
        "name": "Claude Code",
        "env_vars": ["CLAUDE_API_KEY", "ANTHROPIC_API_KEY"],
        "processes": ["claude"],
        "files": ["~/.claude/settings.json"],
        "description": "Anthropic Claude 命令行工具",
    },
    "codex": {
        "name": "Codex",
        "env_vars": ["OPENAI_API_KEY"],
        "processes": ["codex"],
        "files": [],
        "description": "OpenAI Codex",
    },
    "windsurf": {
        "name": "Windsurf",
        "env_vars": ["WINDSURF_API_KEY"],
        "processes": ["windsurf"],
        "files": ["~/.windsurf/config.json"],
        "description": "Codeium Windsurf AI 编辑器",
    },
    "copilot": {
        "name": "GitHub Copilot",
        "env_vars": ["GITHUB_TOKEN", "COPILOT_API_KEY"],
        "processes": ["copilot"],
        "files": [],
        "description": "GitHub Copilot",
    },
    "unknown": {
        "name": "Unknown",
        "env_vars": [],
        "processes": [],
        "files": [],
        "description": "未能识别的 AI 工具",
    },
}


def check_env_vars(tool_id: str) -> bool:
    sig = TOOL_SIGNATURES.get(tool_id)
    if not sig:
        return False
    return any(os.environ.get(var) for var in sig["env_vars"])


def check_processes(tool_id: str) -> bool:
    sig = TOOL_SIGNATURES.get(tool_id)
    if not sig:
        return False
    try:
        with open("/proc/cmdline", "r", encoding="utf-8", errors="ignore") as f:
            cmdline = f.read()
        for proc_name in sig["processes"]:
            if proc_name.lower() in cmdline.lower():
                return True
    except Exception:
        pass
    return False


def check_files(tool_id: str) -> bool:
    sig = TOOL_SIGNATURES.get(tool_id)
    if not sig:
        return False
    for file_pattern in sig["files"]:
        path = Path(file_pattern).expanduser()
        if path.exists():
            return True
    return False


def detect_tool() -> dict[str, Any]:
    scores: dict[str, int] = {tool_id: 0 for tool_id in TOOL_SIGNATURES if tool_id != "unknown"}

    for tool_id in scores:
        if check_env_vars(tool_id):
            scores[tool_id] += 3
        if check_processes(tool_id):
            scores[tool_id] += 2
        if check_files(tool_id):
            scores[tool_id] += 1

    detected = max(scores, key=scores.get)
    if scores.get(detected, 0) == 0:
        detected = "unknown"

    return {
        "tool_id": detected,
        "tool_name": TOOL_SIGNATURES[detected]["name"],
        "tool_name_cn": TOOL_SIGNATURES[detected]["description"],
        "confidence": scores.get(detected, 0),
        "all_scores": scores,
        "recommendation": get_recommendation(detected),
    }


def get_recommendation(tool_id: str) -> dict[str, str]:
    recommendations = {
        "trae-cn": {
            "config_file": "agents/trae.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "true",
        },
        "opencode": {
            "config_file": "agents/opencode.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "true",
        },
        "cursor": {
            "config_file": "agents/cursor.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "true",
        },
        "claude-code": {
            "config_file": "agents/claude.yaml",
            "screenshot_method": "chrome_devtools",
            "mcp_support": "true",
        },
        "codex": {
            "config_file": "agents/openai.yaml",
            "screenshot_method": "computer_use",
            "mcp_support": "true",
        },
        "windsurf": {
            "config_file": "agents/cursor.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "true",
        },
        "copilot": {
            "config_file": "agents/cursor.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "false",
        },
        "unknown": {
            "config_file": "agents/_base.yaml",
            "screenshot_method": "user_supplied",
            "mcp_support": "unknown",
        },
    }
    return recommendations.get(tool_id, recommendations["unknown"])


def main() -> None:
    result = detect_tool()
    print(f"Detected AI Tool: {result['tool_name']} ({result['tool_id']})")
    print(f"Confidence: {result['confidence']}")
    print(f"Recommendation: Use config {result['recommendation']['config_file']}")
    print(f"Screenshot method: {result['recommendation']['screenshot_method']}")
    print()
    print("All scores:", result["all_scores"])


if __name__ == "__main__":
    main()
