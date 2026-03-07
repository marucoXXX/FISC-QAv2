"""FISC-QAv2 テスト共通フィクスチャ"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
INPUT_DIR = FIXTURES_DIR / "input"
KB_DIR = FIXTURES_DIR / "kb"
EXPECTED_DIR = FIXTURES_DIR / "expected"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def input_dir() -> Path:
    return INPUT_DIR


@pytest.fixture
def kb_dir() -> Path:
    return KB_DIR


@pytest.fixture
def expected_dir() -> Path:
    return EXPECTED_DIR


@pytest.fixture
def questionnaire_path() -> Path:
    return INPUT_DIR / "questionnaire.xlsx"


@pytest.fixture
def expected_index(expected_dir: Path) -> list[dict]:
    return json.loads((expected_dir / "index.json").read_text(encoding="utf-8"))


@pytest.fixture
def expected_routing_map(expected_dir: Path) -> dict:
    return json.loads((expected_dir / "routing_map.json").read_text(encoding="utf-8"))


@pytest.fixture
def expected_final_answers(expected_dir: Path) -> dict:
    return json.loads((expected_dir / "final_answers.json").read_text(encoding="utf-8"))
