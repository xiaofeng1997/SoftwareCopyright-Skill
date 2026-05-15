#!/usr/bin/env python3
"""Check runtime capabilities at the beginning of the workflow."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import ensure_dir, write_json


def command_version(command: list[str]) -> tuple[bool, str]:
    if not shutil.which(command[0]):
        return False, "not found"
    try:
        completed = subprocess.run(command, text=True, capture_output=True, timeout=20)
        output = (completed.stdout or completed.stderr).strip().splitlines()
        return completed.returncode == 0, output[0] if output else "available"
    except Exception as exc:
        return False, str(exc)


def run_docx_env(skill_dir: Path) -> tuple[bool, str]:
    env_script = skill_dir / "vendor/docx-toolkit/scripts/env_check.sh"
    if not env_script.exists():
        return False, "vendor/docx-toolkit/scripts/env_check.sh not found"
    try:
        completed = subprocess.run(["bash", str(env_script)], text=True, capture_output=True, timeout=40)
        return completed.returncode == 0, (completed.stdout + completed.stderr).strip()
    except Exception as exc:
        return False, str(exc)


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def detect_ai_tool() -> dict[str, Any]:
    tool_signatures = {
        "trae-cn": {
            "name": "Trae CN",
            "env_vars": ["TRAE_API_KEY", "TRAE_SESSION"],
            "files": [Path.home() / ".trae" / "config.json"],
        },
        "opencode": {
            "name": "OpenCode",
            "env_vars": ["OPENCODE_API_KEY"],
            "files": [],
        },
        "cursor": {
            "name": "Cursor",
            "env_vars": ["CURSOR_API_KEY"],
            "files": [Path.home() / ".cursor" / "settings.json"],
        },
        "claude-code": {
            "name": "Claude Code",
            "env_vars": ["CLAUDE_API_KEY", "ANTHROPIC_API_KEY"],
            "files": [Path.home() / ".claude" / "settings.json"],
        },
        "codex": {
            "name": "Codex",
            "env_vars": ["OPENAI_API_KEY"],
            "files": [],
        },
    }

    scores: dict[str, int] = {}
    for tool_id, sig in tool_signatures.items():
        score = 0
        if any(os.environ.get(var) for var in sig["env_vars"]):
            score += 3
        if any(f.expanduser().exists() for f in sig["files"]):
            score += 1
        scores[tool_id] = score

    detected = max(scores, key=scores.get) if scores else "unknown"
    if scores.get(detected, 0) == 0:
        detected = "unknown"

    return {
        "detected": detected,
        "name": tool_signatures.get(detected, {}).get("name", "Unknown"),
        "scores": scores,
    }


def check_environment(skill_dir: Path) -> dict[str, Any]:
    python_docx = module_available("docx")
    pandoc_ok, pandoc_version = command_version(["pandoc", "--version"])
    dotnet_ok, dotnet_version = command_version(["dotnet", "--version"])
    docx_ready, docx_output = run_docx_env(skill_dir)
    ai_tool = detect_ai_tool()

    final_docx_mode = "docx-openxml" if docx_ready else ("python-docx" if python_docx else "basic-ooxml")
    requires_user_input = not docx_ready
    next_action = (
        "请选择：1) 安装完整 DOCX 环境；2) 使用基础 DOCX 兜底继续。回复选择后再进入项目分析。"
        if requires_user_input
        else "完整 DOCX 环境可用，可以进入项目分析。"
    )

    screenshot_recommendation = "user_supplied"
    if ai_tool["detected"] == "claude-code":
        screenshot_recommendation = "chrome_devtools"
    elif ai_tool["detected"] == "codex":
        screenshot_recommendation = "computer_use"

    return {
        "output_directory": "当前目录/软件著作权申请资料",
        "ai_tool_detected": ai_tool,
        "capabilities": {
            "markdown_drafts": True,
            "application_txt": True,
            "basic_docx": python_docx or True,
            "python_docx": python_docx,
            "pandoc_preview": pandoc_ok,
            "docx_openxml_full": docx_ready,
            "dotnet_sdk": dotnet_ok,
        },
        "versions": {
            "pandoc": pandoc_version,
            "dotnet": dotnet_version,
        },
        "final_docx_mode": final_docx_mode,
        "recommendation": (
            "完整 DOCX OpenXML 环境已就绪，建议使用完整 Word 生成和校验流程。"
            if docx_ready
            else "完整 DOCX OpenXML 环境未就绪。可以继续使用兜底 DOCX 生成；如需更规范的 Word 结构和校验，请先安装 .NET SDK 并运行 vendor/docx-toolkit/scripts/setup.sh。"
        ),
        "install_prompt": (
            "是否安装完整 DOCX 环境？安装后文档生成和校验更规范；不安装也可以继续生成 Markdown、TXT 和基础 DOCX。"
            if not docx_ready
            else "无需安装，完整环境可用。"
        ),
        "requires_user_input": requires_user_input,
        "confirmation_stage": "environment" if requires_user_input else None,
        "next_action": next_action,
        "docx_env_output": docx_output,
        "screenshot_recommendation": screenshot_recommendation,
        "tool_config_hint": f"检测到 {ai_tool['name']}，建议使用 agents/{ai_tool['detected']}.yaml 配置文件" if ai_tool["detected"] != "unknown" else "未检测到特定 AI 工具，使用通用配置",
    }


def write_markdown(path: Path, data: dict[str, Any]) -> None:
    caps = data["capabilities"]
    ai_tool = data["ai_tool_detected"]
    lines = [
        "# 软著申请资料生成环境检查",
        "",
        f"- 输出目录：`{data['output_directory']}`",
        f"- 最终 Word 模式：`{data['final_docx_mode']}`",
        "",
        "## AI 工具检测",
        "",
        f"- 检测到的工具：{ai_tool['name']}（{ai_tool['detected']}）",
        f"- 建议配置文件：`agents/{ai_tool['detected']}.yaml`",
        f"- 建议截图方式：`{data['screenshot_recommendation']}`",
        "",
        "## 能力状态",
        "",
        f"- Markdown 草稿：{'可用' if caps['markdown_drafts'] else '不可用'}",
        f"- 申请表 TXT：{'可用' if caps['application_txt'] else '不可用'}",
        f"- 基础 DOCX 生成：{'可用' if caps['basic_docx'] else '不可用'}",
        f"- python-docx：{'可用' if caps['python_docx'] else '不可用'}",
        f"- pandoc 预览：{'可用' if caps['pandoc_preview'] else '不可用'}（{data['versions']['pandoc']}）",
        f"- .NET SDK：{'可用' if caps['dotnet_sdk'] else '不可用'}（{data['versions']['dotnet']}）",
        f"- DOCX OpenXML 完整环境：{'可用' if caps['docx_openxml_full'] else '不可用'}",
        "",
        "## 建议",
        "",
        data["recommendation"],
        "",
        "## 用户选择",
        "",
        data["install_prompt"],
        "",
        "如果完整 DOCX 环境不可用，必须先等待用户选择，并记录 `environment` 门禁后再继续。",
        "",
        "```text" if data.get("requires_user_input") else "",
        "STOP_FOR_USER" if data.get("requires_user_input") else "",
        f"NEXT_ACTION: {data['next_action']}" if data.get("requires_user_input") else "",
        "```" if data.get("requires_user_input") else "",
        "",
        "## DOCX 环境输出摘要",
        "",
        "```text",
        "\n".join(data["docx_env_output"].splitlines()[:40]),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="软件著作权申请资料")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parents[1]
    out_dir = ensure_dir(Path(args.out_dir))
    data = check_environment(skill_dir)
    write_json(out_dir / "环境检查.json", data)
    write_markdown(out_dir / "环境检查.md", data)
    print(f"OK environment check: {out_dir}")
    print(f"Detected AI tool: {data['ai_tool_detected']['name']}")
    print(f"Final DOCX mode: {data['final_docx_mode']}")
    print(data["recommendation"])
    if data.get("requires_user_input"):
        print("STOP_FOR_USER")
        print(f"NEXT_ACTION: {data['next_action']}")


if __name__ == "__main__":
    main()
