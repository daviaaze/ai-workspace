"""
Tests for deep search engine — planning, research, synthesis.

Covers:
- Data classes (SubQuestion, ResearchResult)
- Safe float coercion and JSON parsing
- DeepSearchEngine initialization for Ollama and DeepSeek
- Research pipeline (mocked LLM)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════


class TestDataClasses:
    """SubQuestion and ResearchResult data classes."""

    def test_sub_question_defaults(self):
        from ai_workspace.search.deep_search import SubQuestion
        sq = SubQuestion(question="What is Nix?")
        assert sq.question == "What is Nix?"
        assert sq.answer == ""
        assert sq.sources == []
        assert sq.confidence == 0.0

    def test_sub_question_full(self):
        from ai_workspace.search.deep_search import SubQuestion
        sq = SubQuestion(
            question="What is Nix?",
            answer="A package manager",
            sources=["https://nixos.org"],
            confidence=0.95,
        )
        assert sq.answer == "A package manager"
        assert len(sq.sources) == 1
        assert sq.confidence == 0.95

    def test_research_result_defaults(self):
        from ai_workspace.search.deep_search import ResearchResult
        rr = ResearchResult(original_query="test")
        assert rr.original_query == "test"
        assert rr.sub_questions == []
        assert rr.summary == ""
        assert rr.confidence == 0.0

    def test_research_result_with_sub_questions(self):
        from ai_workspace.search.deep_search import ResearchResult, SubQuestion
        sq = SubQuestion(question="Q1", answer="A1", confidence=0.8)
        rr = ResearchResult(
            original_query="test",
            sub_questions=[sq],
            summary="Summary text",
            confidence=0.85,
        )
        assert len(rr.sub_questions) == 1
        assert rr.summary == "Summary text"
        assert rr.confidence == 0.85


# ═══════════════════════════════════════════════════════
# Safe float coercion
# ═══════════════════════════════════════════════════════


class TestSafeFloat:
    """_safe_float coerces various types to float safely."""

    def test_float_passthrough(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float(0.85) == 0.85
        assert _safe_float(0.0) == 0.0
        assert _safe_float(1.0) == 1.0

    def test_int_to_float(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float(42) == 42.0
        assert _safe_float(0) == 0.0

    def test_string_number(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float("0.85") == 0.85
        assert _safe_float("42") == 42.0
        assert _safe_float("  0.5  ") == 0.5

    def test_string_text_fallback(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float("The analysis combines findings...") == 0.0
        assert _safe_float("not a number") == 0.0

    def test_none_fallback(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float(None) == 0.0

    def test_bool_fallback(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float(True) == 0.0
        assert _safe_float(False) == 0.0

    def test_custom_default(self):
        from ai_workspace.search.deep_search import _safe_float
        assert _safe_float("nonsense", default=0.5) == 0.5
        assert _safe_float(None, default=0.75) == 0.75


# ═══════════════════════════════════════════════════════
# JSON parsing safety
# ═══════════════════════════════════════════════════════


class TestParseJsonSafe:
    """_parse_json_safe handles various JSON formats from LLM output."""

    def test_plain_json_object(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        result = _parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_markdown_fence(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        result = _parse_json_safe('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_array(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        result = _parse_json_safe('["q1", "q2", "q3"]')
        assert result == ["q1", "q2", "q3"]

    def test_embedded_json_in_text(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        result = _parse_json_safe('Here are the questions: ["q1", "q2"] and more text')
        assert result == ["q1", "q2"]

    def test_invalid_json_raises(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        with pytest.raises(ValueError):
            _parse_json_safe("This is not JSON at all. No brackets here.")

    def test_nested_json(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        result = _parse_json_safe('{"questions": [{"q": "Q1", "confidence": 0.9}]}')
        assert result["questions"][0]["q"] == "Q1"

    def test_empty_string(self):
        from ai_workspace.search.deep_search import _parse_json_safe
        with pytest.raises(ValueError):
            _parse_json_safe("")


# ═══════════════════════════════════════════════════════
# DeepSearchEngine initialization
# ═══════════════════════════════════════════════════════


class TestEngineInit:
    """DeepSearchEngine constructor and configuration."""

    def test_ollama_default_init(self):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine()
        assert engine.max_depth == 2
        assert engine.max_sub_questions == 5
        assert engine.provider == "ollama"
        assert engine.llm is not None
        assert engine.deep_llm is not None

    def test_ollama_custom_params(self):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(
            model="ollama/qwen3:14b",
            deep_model="ollama/deepseek-r1:14b",
            max_depth=3,
            max_sub_questions=7,
            provider="ollama",
        )
        assert engine.max_depth == 3
        assert engine.max_sub_questions == 7

    def test_deepseek_init_requires_key(self, monkeypatch):
        from ai_workspace.search.deep_search import DeepSearchEngine
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
        engine = DeepSearchEngine(provider="deepseek")
        assert engine.provider == "deepseek"
        assert engine.llm is not None
        assert engine.deep_llm is not None

    def test_deepseek_init_without_key_raises(self, monkeypatch):
        from ai_workspace.search.deep_search import DeepSearchEngine
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with patch("os.path.exists", return_value=False):
            with pytest.raises(ValueError, match="DeepSeek API not configured"):
                DeepSearchEngine(provider="deepseek")


# ═══════════════════════════════════════════════════════
# Research pipeline (mocked LLM)
# ═══════════════════════════════════════════════════════


class TestResearchPipeline:
    """Research pipeline with mocked crewAI LLM."""

    @pytest.fixture
    def mock_crew_kickoff(self):
        """Mock crew.kickoff_async() — crewAI 1.x requires async."""
        with patch("crewai.Crew.kickoff_async") as mock:
            mock.return_value = '{"answer": "Test answer", "confidence": 0.9, "summary": "Test summary"}'
            yield mock

    def test_research_returns_result(self, mock_crew_kickoff):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)
        result = asyncio.run(engine.research("What is Nix?"))
        assert result is not None
        assert result.original_query == "What is Nix?"
        assert isinstance(result.summary, str)
        assert isinstance(result.confidence, float)

    def test_research_with_progress_callback(self, mock_crew_kickoff):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)
        
        progress_calls = []
        def track_progress(update: dict):
            progress_calls.append(update)
        
        result = asyncio.run(engine.research("Test query", progress=track_progress))
        assert len(progress_calls) > 0
        # Should have at least planning and synthesis stages
        phases = [c.get("phase", "") for c in progress_calls]
        assert any("planning" in p for p in phases)
        assert any("synthesizing" in p for p in phases)

    def test_research_handles_crew_error(self):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)
        
        with patch("crewai.Crew.kickoff_async", side_effect=RuntimeError("LLM timeout")):
            with pytest.raises(RuntimeError, match="LLM timeout"):
                asyncio.run(engine.research("Test"))


# ═══════════════════════════════════════════════════════
# Output Pydantic models (crewAI 1.x output_pydantic)
# ═══════════════════════════════════════════════════════


class TestOutputModels:
    """Pydantic models for crewAI structured output validation."""

    def test_plan_output_validation(self):
        from ai_workspace.search.deep_search import PlanOutput
        plan = PlanOutput(questions=["Q1", "Q2", "Q3"])
        assert len(plan.questions) == 3
        assert plan.questions[0] == "Q1"

    def test_plan_output_empty(self):
        from ai_workspace.search.deep_search import PlanOutput
        plan = PlanOutput()
        assert plan.questions == []

    def test_research_answer_validation(self):
        from ai_workspace.search.deep_search import ResearchAnswer
        answer = ResearchAnswer(
            answer="The answer is 42",
            confidence=0.9,
            sources=["https://example.com"],
        )
        assert answer.answer == "The answer is 42"
        assert answer.confidence == 0.9
        assert len(answer.sources) == 1

    def test_research_answer_confidence_bounds(self):
        from ai_workspace.search.deep_search import ResearchAnswer
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ResearchAnswer(answer="test", confidence=1.5)
        with pytest.raises(pydantic.ValidationError):
            ResearchAnswer(answer="test", confidence=-0.1)

    def test_synthesis_report_validation(self):
        from ai_workspace.search.deep_search import SynthesisReport
        report = SynthesisReport(
            summary="Executive summary",
            key_findings=["Finding 1", "Finding 2"],
            detailed_analysis="Detailed text",
            confidence=0.85,
            sources=["https://source.com"],
        )
        assert report.summary == "Executive summary"
        assert len(report.key_findings) == 2
        assert report.confidence == 0.85

    def test_synthesis_report_json_roundtrip(self):
        from ai_workspace.search.deep_search import SynthesisReport
        report = SynthesisReport(
            summary="Test summary",
            key_findings=["F1"],
            detailed_analysis="Full analysis",
            confidence=0.75,
            sources=["https://s.com"],
        )
        json_str = report.model_dump_json()
        parsed = SynthesisReport.model_validate_json(json_str)
        assert parsed.summary == report.summary
        assert parsed.confidence == report.confidence


class TestGuardrail:
    """Guardrail function validates output quality."""

    def test_guardrail_accepts_high_confidence(self):
        from ai_workspace.search.deep_search import guardrail_min_confidence
        from unittest.mock import MagicMock
        output = MagicMock()
        output.pydantic = MagicMock(confidence=0.85)
        accepted, result = guardrail_min_confidence(output, min_confidence=0.3)
        assert accepted is True

    def test_guardrail_rejects_low_confidence(self):
        from ai_workspace.search.deep_search import guardrail_min_confidence
        from unittest.mock import MagicMock
        output = MagicMock()
        output.pydantic = MagicMock(confidence=0.15)
        accepted, msg = guardrail_min_confidence(output, min_confidence=0.3)
        assert accepted is False
        assert "below minimum" in msg

    def test_guardrail_handles_no_pydantic(self):
        from ai_workspace.search.deep_search import guardrail_min_confidence
        from unittest.mock import MagicMock
        output = MagicMock()
        del output.pydantic
        accepted, result = guardrail_min_confidence(output)
        assert accepted is True
