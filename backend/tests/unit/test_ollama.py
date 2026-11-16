from types import SimpleNamespace

from app.infrastructure.llm import ollama


def test_payload_uses_30_minute_keep_alive_and_supplied_context_limit(monkeypatch):
    monkeypatch.setattr(
        ollama, "get_settings",
        lambda: SimpleNamespace(llm_model="llama3.2", num_ctx=8192))

    payload = ollama._payload("prompt", 200, True, num_ctx=4096)

    assert payload["keep_alive"] == "30m"
    assert payload["options"]["num_ctx"] == 4096
    assert payload["options"]["num_predict"] == 200


def test_generate_timeout_has_ten_second_connect_and_180_second_read(monkeypatch):
    seen = {}

    class Response:
        def raise_for_status(self):
            pass

        @staticmethod
        def json():
            return {"response": "ok", "prompt_eval_count": 4, "eval_count": 1}

    def post(url, **kwargs):
        seen.update(kwargs)
        return Response()

    monkeypatch.setattr(ollama, "get_settings",
                        lambda: SimpleNamespace(ollama_host="http://localhost:11434",
                                                llm_model="llama3.2", num_ctx=4096))
    monkeypatch.setattr(ollama.httpx, "post", post)

    assert ollama.complete("prompt", stage="test") == "ok"
    assert seen["timeout"].connect == 10
    assert seen["timeout"].read == 180
