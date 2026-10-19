from mde.ai.usage import estimate_cost_usd, normalize_usage


def test_normalize_usage_handles_provider_shapes():
    assert (
        normalize_usage({"promptTokenCount": 10, "candidatesTokenCount": 5})[
            "total_tokens"
        ]
        == 15
    )


def test_estimate_cost_uses_environment(monkeypatch):
    monkeypatch.setenv("MDE_AI_PRICE_OPENAI_TEST_MODEL_INPUT_PER_1M", "1")
    monkeypatch.setenv("MDE_AI_PRICE_OPENAI_TEST_MODEL_OUTPUT_PER_1M", "2")
    assert (
        estimate_cost_usd(
            "openai",
            "test-model",
            {"input_tokens": 1_000_000, "output_tokens": 500_000},
        )
        == 2.0
    )
