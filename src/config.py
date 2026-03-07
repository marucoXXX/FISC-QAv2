"""FISC-QAv2 設定管理"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    token_budget_per_reader: int = 80000
    max_reader_retries: int = 3
    model: str = "claude-sonnet-4-20250514"
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    output_dir: str = "output"
    index_cache_path: str = ".fisc_index_cache.json"
