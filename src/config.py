"""FISC-QAv2 設定管理"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    kb_dir: str = field(default_factory=lambda: os.environ.get("FISC_KB_DIR", "kb"))
    token_budget_per_reader: int = field(
        default_factory=lambda: int(os.environ.get("FISC_TOKEN_BUDGET", "80000"))
    )
    max_reader_retries: int = 3
    model: str = field(
        default_factory=lambda: os.environ.get("FISC_MODEL", "claude-sonnet-4-20250514")
    )
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    output_dir: str = field(
        default_factory=lambda: os.environ.get("FISC_OUTPUT_DIR", "output")
    )
    index_cache_path: str = ".fisc_index_cache.json"
    use_llm_summary: bool = False
