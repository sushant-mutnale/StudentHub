import json

import pytest

from backend.interview_engine.adapters.llm import (
    GroqAnalyzer,
    GroqEvaluator,
    GroqQuestionGenerator,
)
from backend.interview_engine.contracts.records import Analysis
from backend.interview_engine.ports.capabilities import (
    AnalysisRequest,
    BlueprintSlot,
    CompetencyEvaluationInput,
    EvaluationRequest,
    QuestionRequest,
)
from backend.services.llm.groq import LLMCompletion, LLMUnavailable


class FakeLLM:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error
        self.calls = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return LLMCompletion(
            text=self.text,
            prompt_tokens=1,
            completion_tokens=1,
            keyhash="abc",
            model="m",
        )


def _analysis_request(text="I led the migration."):
    return AnalysisRequest(
        session_id="s1",
        turn_id="t1",
        question_id="q1",
        slot_id="slot-1",
        competency="ownership",
        text=text,
    )


def _question_request(purpose="primary"):
    slot = BlueprintSlot(
        slot_id="slot-1",
        competency="ownership",
        dimension="behavioural",
        difficulty="medium",
        intent="Probe ownership of a hard project.",
        fallback_question="Tell me about a project you owned.",
        follow_up_question="What did you personally decide?",
        clarification_text="Pick one specific project.",
        hint_text="Think about a decision only you could make.",
    )
    return QuestionRequest(
        session_id="s1",
        slot=slot,
        purpose=purpose,
        role="Engineer",
        company="Acme",
        prior_questions=[],
    )


def _evaluation_request():
    return EvaluationRequest(
        session_id="s1",
        report_id="r1",
        role="Engineer",
        company="Acme",
        competencies=[
            CompetencyEvaluationInput(
                competency="ownership",
                level="developing",
                confidence="medium",
                instances=2,
            )
        ],
    )


async def test_analyzer_maps_a_valid_response():
    text = json.dumps(
        {
            "instance": "new",
            "signal": "sufficient",
            "substantively_deficient": False,
            "contradiction": False,
            "limitation": None,
        }
    )
    analyzer = GroqAnalyzer(FakeLLM(text))
    analysis = await analyzer.analyze(_analysis_request())
    assert analysis == Analysis(signal="sufficient", instance="new")


async def test_analyzer_honours_the_boolean_fields():
    text = json.dumps(
        {
            "instance": "new",
            "signal": "sufficient",
            "substantively_deficient": True,
            "contradiction": True,
            "limitation": "vague",
        }
    )
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.contradiction is True
    assert analysis.substantively_deficient is True
    assert analysis.limitation == "vague"


async def test_analyzer_normalises_off_topic_to_same_instance():
    text = json.dumps({"instance": "new", "signal": "off_topic"})
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.signal == "off_topic"


async def test_analyzer_degrades_on_transport_failure():
    analyzer = GroqAnalyzer(FakeLLM(error=LLMUnavailable("daily_exhausted")))
    analysis = await analyzer.analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.signal == "incomplete"
    assert analysis.substantively_deficient is True
    assert analysis.limitation == "analysis_unavailable"


async def test_analyzer_degrades_on_malformed_json():
    analysis = await GroqAnalyzer(FakeLLM("not json")).analyze(_analysis_request())
    assert analysis.signal == "incomplete"
    assert analysis.limitation == "analysis_unavailable"


async def test_analyzer_degrades_on_an_out_of_contract_enum():
    text = json.dumps({"instance": "maybe", "signal": "sufficient"})
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.instance == "same"
    assert analysis.limitation == "analysis_unavailable"


async def test_analyzer_degrades_on_a_string_boolean():
    text = json.dumps(
        {"instance": "new", "signal": "sufficient", "contradiction": "false"}
    )
    analysis = await GroqAnalyzer(FakeLLM(text)).analyze(_analysis_request())
    assert analysis.signal == "incomplete"
    assert analysis.limitation == "analysis_unavailable"


async def test_generator_returns_generated_text_stripped_of_quotes():
    generator = GroqQuestionGenerator(FakeLLM('"Tell me about a hard decision."'))
    question = await generator.generate(_question_request())
    assert question.text == "Tell me about a hard decision."
    assert question.source == "generated"


async def test_generator_preserves_inner_quotes():
    generator = GroqQuestionGenerator(FakeLLM('What did they mean by "shipped?"'))
    question = await generator.generate(_question_request())
    assert question.text == 'What did they mean by "shipped?"'
    assert question.source == "generated"


async def test_generator_labels_empty_text_as_fallback():
    question = await GroqQuestionGenerator(FakeLLM("   ")).generate(
        _question_request()
    )
    assert question.text == ""
    assert question.source == "fallback"


async def test_generator_returns_empty_text_when_the_call_fails():
    generator = GroqQuestionGenerator(FakeLLM(error=RuntimeError("boom")))
    question = await generator.generate(_question_request())
    assert question.text == ""
    assert question.source == "fallback"


async def test_generator_requests_plain_text_not_json():
    fake = FakeLLM("Question?")
    await GroqQuestionGenerator(fake).generate(_question_request())
    assert "response_format" not in fake.calls[0]


async def test_evaluator_returns_reasons_and_narrative():
    text = json.dumps(
        {"reasons": {"ownership": ["Owned the migration end to end."]}, "narrative": "Solid."}
    )
    output = await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert output.narrative == "Solid."
    assert output.reasons == {"ownership": ["Owned the migration end to end."]}


async def test_evaluator_raises_typed_failure_on_transport_error():
    evaluator = GroqEvaluator(FakeLLM(error=LLMUnavailable("wait_budget_exceeded")))
    with pytest.raises(LLMUnavailable):
        await evaluator.evaluate(_evaluation_request())


async def test_evaluator_rejects_an_unknown_competency():
    text = json.dumps({"reasons": {"leadership": ["x"]}, "narrative": "y"})
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_evaluator_rejects_partial_competency_coverage():
    text = json.dumps({"reasons": {}, "narrative": "n"})
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_evaluator_rejects_malformed_json():
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM("nope")).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_evaluator_rejects_out_of_contract_keys():
    text = json.dumps(
        {"reasons": {"ownership": []}, "narrative": "n", "score": 99, "final_score": 1}
    )
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_evaluator_rejects_an_empty_narrative():
    text = json.dumps({"reasons": {"ownership": []}, "narrative": "   "})
    with pytest.raises(LLMUnavailable) as caught:
        await GroqEvaluator(FakeLLM(text)).evaluate(_evaluation_request())
    assert caught.value.reason == "malformed_evaluation"


async def test_adapters_use_the_spec_token_caps_and_temperatures():
    analyzer_llm = FakeLLM(json.dumps({"instance": "new", "signal": "sufficient"}))
    generator_llm = FakeLLM("Question?")
    evaluator_llm = FakeLLM(
        json.dumps({"reasons": {"ownership": []}, "narrative": "n"})
    )
    await GroqAnalyzer(analyzer_llm).analyze(_analysis_request())
    await GroqQuestionGenerator(generator_llm).generate(_question_request())
    await GroqEvaluator(evaluator_llm).evaluate(_evaluation_request())
    assert analyzer_llm.calls[0]["max_completion_tokens"] == 600
    assert analyzer_llm.calls[0]["temperature"] == 0.0
    assert analyzer_llm.calls[0]["response_format"] == "json_object"
    assert generator_llm.calls[0]["max_completion_tokens"] == 400
    assert generator_llm.calls[0]["temperature"] == 0.5
    assert evaluator_llm.calls[0]["max_completion_tokens"] == 1200
    assert evaluator_llm.calls[0]["temperature"] == 0.0
    assert evaluator_llm.calls[0]["response_format"] == "json_object"


class _Settings:
    groq_llm_enabled = False
    groq_api_key_1 = "gsk_a"
    groq_api_key_2 = None
    groq_api_key_3 = None
    groq_model = "openai/gpt-oss-120b"
    groq_base_url = "https://example.invalid"
    groq_rpm_per_key = 25
    groq_rpd_per_key = 900
    groq_tpm_per_key = 7000
    groq_tpd_per_key = 180000
    groq_max_wait_seconds = 60
    groq_request_timeout_seconds = 30
    groq_reasoning_effort = "low"


def _settings(**overrides):
    settings = _Settings()
    for name, value in overrides.items():
        setattr(settings, name, value)
    return settings


def test_build_llm_adapters_returns_none_when_disabled():
    from backend.interview_engine.adapters.llm import build_llm_adapters

    assert build_llm_adapters(_settings(groq_llm_enabled=False)) is None


def test_build_llm_adapters_returns_none_without_keys():
    from backend.interview_engine.adapters.llm import build_llm_adapters

    settings = _settings(groq_llm_enabled=True, groq_api_key_1=None)
    assert build_llm_adapters(settings) is None


def test_build_llm_adapters_wires_the_three_real_adapters():
    from backend.interview_engine.adapters.llm import (
        GroqAnalyzer,
        GroqEvaluator,
        GroqQuestionGenerator,
        build_llm_adapters,
    )

    built = build_llm_adapters(
        _settings(groq_llm_enabled=True), client=FakeLLM("unused")
    )
    assert isinstance(built.analyzer, GroqAnalyzer)
    assert isinstance(built.generator, GroqQuestionGenerator)
    assert isinstance(built.evaluator, GroqEvaluator)
