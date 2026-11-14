"""AnalysisReport contract (DRAFT, schema_version 0.1.0). See docs/adr/0003."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "0.1.0"


class FileKind(str, Enum):
    CLAUDE_MD = "claude_md"
    AGENTS_MD = "agents_md"
    README = "readme"
    RULE = "rule"
    SKILL = "skill"
    ADR = "adr"
    DOC = "doc"
    OTHER = "other"


class LoadMode(str, Enum):
    ALWAYS = "always"
    ON_DEMAND = "on_demand"
    UNKNOWN = "unknown"


class FindingType(str, Enum):
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    BROKEN_REFERENCE = "broken_reference"
    STALE = "stale"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Method(str, Enum):
    DETERMINISTIC = "deterministic"
    LLM = "llm"


class Evidence(BaseModel):
    file: str = Field(description="Path relative to repo root")
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    quote: str = Field(description="Exact text from the file")


class Finding(BaseModel):
    id: str
    type: FindingType
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    method: Method
    summary: str
    evidence: list[Evidence] = Field(min_length=1)
    recommendation: str | None = None


class ContextFile(BaseModel):
    path: str
    kind: FileKind
    token_estimate: int = Field(ge=0, description="ESTIMATE, not an exact tokenizer count")
    load_mode: LoadMode = LoadMode.UNKNOWN


class Metrics(BaseModel):
    files_scanned: int = 0
    est_tokens_total: int = Field(0, description="Estimated tokens across context files")
    est_tokens_duplicated: int = Field(0, description="Estimated tokens in duplicated passages")
    duration_ms: int = 0
    llm_input_tokens: int = 0
    llm_output_tokens: int = 0


class RepoInfo(BaseModel):
    name: str
    commit_sha: str | None = None


class AnalysisReport(BaseModel):
    schema_version: str = SCHEMA_VERSION
    engine_version: str
    repo: RepoInfo
    analyzed_at: datetime
    context_files: list[ContextFile] = []
    findings: list[Finding] = []
    metrics: Metrics = Metrics()
