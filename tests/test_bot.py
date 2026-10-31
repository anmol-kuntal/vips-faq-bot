from unittest.mock import MagicMock, call

import pytest
from google.genai import errors

import bot


def server_error(code=503):
    return errors.ServerError(code, {"error": {"message": "boom", "status": "UNAVAILABLE"}})


def client_error(code):
    return errors.ClientError(code, {"error": {"message": "boom", "status": "ERROR"}})


def ok(text="Fees are due on the 1st."):
    r = MagicMock()
    r.text = text
    return r


@pytest.fixture
def gemini(monkeypatch):
    """Fake Gemini client, two models, and no real sleeping."""
    fake = MagicMock()
    monkeypatch.setattr(bot, "client", fake)
    monkeypatch.setattr(bot, "MODELS", ["model-a", "model-b"])
    sleep = MagicMock()
    monkeypatch.setattr(bot.time, "sleep", sleep)
    fake.sleep = sleep
    return fake


def models_called(gemini):
    return [c.kwargs["model"] for c in gemini.models.generate_content.call_args_list]


def test_returns_stripped_text(gemini):
    gemini.models.generate_content.return_value = ok("  Hello  ")
    assert bot.answer("hi") == "Hello"
    assert models_called(gemini) == ["model-a"]


def test_empty_response_text_returns_empty_string(gemini):
    gemini.models.generate_content.return_value = ok(None)
    assert bot.answer("hi") == ""


def test_question_is_sent_as_contents(gemini):
    gemini.models.generate_content.return_value = ok()
    bot.answer("When are fees due?")
    assert gemini.models.generate_content.call_args.kwargs["contents"] == "When are fees due?"


def test_falls_back_to_second_model(gemini):
    gemini.models.generate_content.side_effect = [server_error(503), ok("From model B")]
    assert bot.answer("hi") == "From model B"
    assert models_called(gemini) == ["model-a", "model-b"]


def test_rate_limit_429_is_retried(gemini):
    gemini.models.generate_content.side_effect = [client_error(429), ok("Recovered")]
    assert bot.answer("hi") == "Recovered"


def test_model_not_found_404_moves_to_next_model(gemini):
    gemini.models.generate_content.side_effect = [client_error(404), ok("From model B")]
    assert bot.answer("hi") == "From model B"
    assert models_called(gemini) == ["model-a", "model-b"]


def test_retries_across_attempts_before_succeeding(gemini):
    gemini.models.generate_content.side_effect = [server_error()] * 4 + [ok("Finally")]
    assert bot.answer("hi") == "Finally"
    assert gemini.models.generate_content.call_count == 5


def test_all_models_failing_raises_last_error(gemini):
    gemini.models.generate_content.side_effect = server_error(503)
    with pytest.raises(errors.APIError) as exc:
        bot.answer("hi")
    assert exc.value.code == 503
    # 3 attempts x 2 models
    assert gemini.models.generate_content.call_count == 6


def test_non_retryable_error_raises_immediately(gemini):
    gemini.models.generate_content.side_effect = client_error(400)
    with pytest.raises(errors.APIError) as exc:
        bot.answer("hi")
    assert exc.value.code == 400
    assert gemini.models.generate_content.call_count == 1
    gemini.sleep.assert_not_called()


def test_backoff_waits_1_2_4_seconds(gemini, monkeypatch):
    monkeypatch.setattr(bot, "MODELS", ["model-a"])
    gemini.models.generate_content.side_effect = server_error()
    with pytest.raises(errors.APIError):
        bot.answer("hi")
    assert gemini.sleep.call_args_list == [call(1), call(2), call(4)]


def test_prompt_contains_knowledge_base_and_temperature_zero(gemini):
    gemini.models.generate_content.return_value = ok()
    bot.answer("hi")
    config = gemini.models.generate_content.call_args.kwargs["config"]
    assert config.temperature == 0
    assert bot.KNOWLEDGE_BASE in config.system_instruction
    assert bot.FALLBACK in config.system_instruction


def test_unknown_prompt_version_raises(gemini):
    with pytest.raises(KeyError):
        bot.answer("hi", prompt_version="v99")