import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from trashloop.models import AnalysisReport, Evidence, Finding, RepoInfo

SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "analysis_report.schema.json"


def test_committed_schema_matches_models():
    assert json.loads(SCHEMA_PATH.read_text()) == AnalysisReport.model_json_schema()


def test_finding_requires_evidence():
    with pytest.raises(ValidationError):
        Finding(id="f1", type="duplicate", severity="low", confidence=0.9,
                method="deterministic", summary="x", evidence=[])


def test_minimal_report_roundtrip():
    r = AnalysisReport(engine_version="0.0.1", repo=RepoInfo(name="x"),
                       analyzed_at=datetime.now(timezone.utc))
    assert AnalysisReport.model_validate_json(r.model_dump_json()) == r
    Evidence(file="a.md", line_start=1, line_end=2, quote="q")
