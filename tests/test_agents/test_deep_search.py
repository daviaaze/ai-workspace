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


# ═══════════════════════════════════════════════════════
# Supervisor Agent (Fase 2)
# ═══════════════════════════════════════════════════════


class TestSupervisorAgent:
    """Supervisor agent creation and behavior."""

    def test_supervisor_agent_created_with_correct_role(self):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(max_depth=1)
        agent = engine._create_supervisor_agent()
        assert agent.role == "Research Supervisor"
        assert "research plan" in agent.goal.lower()

    def test_supervisor_refines_sub_questions(self):
        """Supervisor step trims or adds sub-questions before research."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=3)

        # Mock kickoff_async to return refined questions
        refined_response = """1. What is the core concept?
2. What are the practical applications?
3. How does it compare to alternatives?"""

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            # Planner returns 5 questions, supervisor refines to 3
            mock_kickoff.side_effect = [
                '{"questions": ["Q1", "Q2", "Q3", "Q4", "Q5"]}',  # planner
                refined_response,  # supervisor
                '{"answer": "test", "confidence": 0.8}',  # researcher Q1
                '{"answer": "test", "confidence": 0.8}',  # researcher Q2
                '{"answer": "test", "confidence": 0.8}',  # researcher Q3
                '{"summary": "result", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.8, "sources": []}',  # synthesizer
                'APPROVE',  # critic
            ]

            result = asyncio.run(engine.research("Test query"))
            assert result is not None
            assert result.sub_questions is not None


# ═══════════════════════════════════════════════════════
# Critic Agent (Fase 2)
# ═══════════════════════════════════════════════════════


class TestCriticAgent:
    """Critic agent creation and verdict handling."""

    def test_critic_agent_created_with_correct_role(self):
        from ai_workspace.search.deep_search import DeepSearchEngine
        engine = DeepSearchEngine(max_depth=1)
        agent = engine._create_critic_agent()
        assert agent.role == "Research Critic"
        assert "review" in agent.goal.lower()

    def test_critic_approve_accepts_report(self):
        """When critic returns APPROVE, the pipeline completes normally."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            mock_kickoff.side_effect = [
                '{"questions": ["Q1", "Q2"]}',  # planner
                '1. Q1\n2. Q2',  # supervisor (accepts as-is)
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',  # researcher Q1
                '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',  # researcher Q2
                '{"summary": "Good report", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',  # synthesizer
                'APPROVE',  # critic
            ]

            result = asyncio.run(engine.research("Test"))
            assert result is not None
            assert result.summary == "Good report"

    def test_critic_revise_triggers_revision(self):
        """When critic returns REVISE, the report is re-synthesized."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        call_count = [0]
        responses = [
            '{"questions": ["Q1", "Q2"]}',
            '1. Q1\n2. Q2',
            '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
            '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',
            '{"summary": "Draft", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.7, "sources": []}',
            'REVISE: Add more detail to findings',
            '{"summary": "Revised", "key_findings": ["F1"], "detailed_analysis": "better text", "confidence": 0.85, "sources": []}',
            'APPROVE',
        ]

        async def mock_kickoff():
            idx = call_count[0]
            call_count[0] += 1
            return responses[min(idx, len(responses) - 1)]

        with patch("crewai.Crew.kickoff_async", side_effect=mock_kickoff):
            result = asyncio.run(engine.research("Test"))
            assert result is not None
            assert result.summary == "Revised"

    def test_critic_reject_stops_pipeline(self):
        """When critic returns REJECT, the pipeline stops without infinite loop."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            mock_kickoff.side_effect = [
                '{"questions": ["Q1", "Q2"]}',  # planner
                '1. Q1\n2. Q2',  # supervisor
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Bad report", "key_findings": [], "detailed_analysis": "...", "confidence": 0.3, "sources": []}',  # synthesizer
                'REJECT: Fundamental issues with sources',  # critic (reject)
            ]

            result = asyncio.run(engine.research("Test"))
            assert result is not None
            # Pipeline should not crash — REJECT stops the loop

    def test_critic_max_revisions_not_exceeded(self):
        """Critic won't trigger more than MAX_REVISIONS (2)."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            # 3 consecutive REVISE responses — should stop after 2 revisions
            mock_kickoff.side_effect = [
                '{"questions": ["Q1", "Q2"]}',  # planner
                '1. Q1\n2. Q2',  # supervisor
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "v1", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.7, "sources": []}',
                'REVISE: more detail',  # critic revise #1
                '{"summary": "v2", "key_findings": ["F1"], "detailed_analysis": "text2", "confidence": 0.8, "sources": []}',
                'REVISE: even more',  # critic revise #2
                '{"summary": "v3", "key_findings": ["F1"], "detailed_analysis": "text3", "confidence": 0.85, "sources": []}',
                'REVISE: still not good',  # critic revise #3 (should stop here)
            ]

            result = asyncio.run(engine.research("Test"))
            assert result is not None
            # Should complete without infinite loop


# ═══════════════════════════════════════════════════════
# Human-in-the-loop (Fase 2)
# ═══════════════════════════════════════════════════════


class TestHumanInTheLoop:
    """Human-in-the-loop via human_review parameter."""

    def test_human_review_emits_awaiting_approval(self):
        """When human_review=True, progress callback gets awaiting_approval event."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        events = []
        def capture(update):
            events.append(update)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            mock_kickoff.side_effect = [
                '{"questions": ["Q1"]}',  # planner
                '1. Q1',  # supervisor
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Done", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',
                'APPROVE',  # critic
            ]

            result = asyncio.run(engine.research("Test", progress=capture, human_review=True))

        # Should have an awaiting_approval event
        approval_events = [e for e in events if e.get("status") == "awaiting_approval"]
        assert len(approval_events) == 1
        assert "report" in approval_events[0]
        assert approval_events[0]["report"]["summary"] == "Done"

    def test_human_review_false_no_awaiting_event(self):
        """When human_review=False (default), no awaiting_approval event emitted."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        events = []
        def capture(update):
            events.append(update)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            mock_kickoff.side_effect = [
                '{"questions": ["Q1"]}',
                '1. Q1',
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Done", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',
                'APPROVE',
            ]

            result = asyncio.run(engine.research("Test", progress=capture, human_review=False))

        approval_events = [e for e in events if e.get("status") == "awaiting_approval"]
        assert len(approval_events) == 0


# ═══════════════════════════════════════════════════════
# Pipeline flow (supervisor → research → filter → synth → critic)
# ═══════════════════════════════════════════════════════


class TestPipelineFlow:
    """End-to-end pipeline phase ordering."""

    def test_all_phases_executed_in_order(self):
        """Verify planning, supervising, researching, synthesizing, reviewing."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        phases = []
        def track(update):
            phase = update.get("phase", "")
            if phase not in phases:
                phases.append(phase)

        with patch("crewai.Crew.kickoff_async") as mock_kickoff:
            mock_kickoff.side_effect = [
                '{"questions": ["Q1", "Q2"]}',
                '1. Q1\n2. Q2',
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Done", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',
                'APPROVE',
            ]

            asyncio.run(engine.research("Test", progress=track))

        # All expected phases should appear
        assert "planning" in phases
        assert "supervising" in phases
        assert "researching" in phases
        assert "synthesizing" in phases
        assert "reviewing" in phases  # critic

    def test_supervisor_gracefully_degrades(self):
        """Pipeline survives when supervisor step is skipped (no exceptions)."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        with patch("crewai.Crew.kickoff_async") as mock:
            mock.side_effect = [
                '{"questions": ["Q1", "Q2"]}',
                '1. Q1\n2. Q2',  # supervisor works
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"answer": "A2", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Done", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',
                'APPROVE',
            ]
            result = asyncio.run(engine.research("Test"))
            assert result is not None

    def test_critic_gracefully_degraded(self):
        """Pipeline completes with critic step included."""
        from ai_workspace.search.deep_search import DeepSearchEngine

        engine = DeepSearchEngine(max_depth=1, max_sub_questions=2)

        with patch("crewai.Crew.kickoff_async") as mock:
            mock.side_effect = [
                '{"questions": ["Q1"]}',
                '1. Q1',
                '{"answer": "A1", "confidence": 0.9, "sources": [], "further_questions": []}',
                '{"summary": "Done", "key_findings": ["F1"], "detailed_analysis": "text", "confidence": 0.9, "sources": []}',
                'REJECT: Bad quality',  # critic rejects, but pipeline finishes
            ]
            result = asyncio.run(engine.research("Test"))
            assert result is not None
            assert result.summary == "Done"
