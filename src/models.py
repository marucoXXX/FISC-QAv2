"""FISC-QAv2 共通データモデル"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Question:
    no: int
    major: str
    minor: str
    question: str


@dataclass
class IndexEntry:
    file_name: str
    path: str
    category: str
    summary: str
    estimated_tokens: int
    last_modified: str = ""
    updated: bool = False


@dataclass
class ReaderAssignment:
    reader_id: str
    questions: list[int]
    files: list[str]
    estimated_tokens: int = 0


@dataclass
class RoutingResult:
    readers: list[ReaderAssignment]


@dataclass
class Answer:
    question_no: int
    answer: str
    status: str
    source_references: list[str] = field(default_factory=list)
    confidence: str = Confidence.LOW.value
    key_excerpt: str = ""
    flag: str | None = None


@dataclass
class ReviewNote:
    question_no: int
    issue_type: str
    severity: str
    description: str
    suggestion: str = ""
