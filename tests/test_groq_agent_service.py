import importlib
from types import SimpleNamespace

from backend.app.api.schemas.agent import AgentChatRequest, MessageHistory

agent_service_module = importlib.import_module("backend.app.services.agent_service")
trip_service_module = importlib.import_module("backend.app.services.trip_service")


def test_chat_sends_active_trip_context_to_groq(monkeypatch):
    trip_context = {
        "id": "trip-123",
        "title": "Weekend in Jaipur",
        "start_date": "2026-10-10",
        "end_date": "2026-10-12",
        "total_budget": 18000,
        "currency": "INR",
        "stops": [{"destination_name": "Jaipur", "arrival_date": "2026-10-10"}],
        "itinerary": [{"custom_title": "Amber Fort", "scheduled_date": "2026-10-11"}],
    }
    captured = {}
    monkeypatch.setenv("AI_PROVIDER", "groq")

    class FakeDB:
        def get_trip(self, trip_id):
            return object() if trip_id == "trip-123" else None

    class FakeTripService:
        def get_trip_detail(self, trip_id):
            assert trip_id == "trip-123"
            return SimpleNamespace(model_dump=lambda mode: trip_context)

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Amber Fort is on 11 October."))]
            )

    monkeypatch.setattr(agent_service_module, "get_db", lambda: FakeDB())
    monkeypatch.setattr(trip_service_module, "trip_service", FakeTripService())
    monkeypatch.setattr(
        agent_service_module,
        "_get_groq_client",
        lambda: SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())),
    )

    response = agent_service_module.agent_service.chat(
        AgentChatRequest(
            trip_id="trip-123",
            message="What is planned tomorrow?",
            history=[MessageHistory(role="agent", content="I can check your itinerary.")],
        )
    )

    assert response.reply == "Amber Fort is on 11 October."
    assert response.updated_trip == trip_context
    assert response.executed_tools == []
    assert captured["model"] == "openai/gpt-oss-120b"
    assert captured["messages"][1] == {
        "role": "assistant", "content": "I can check your itinerary."
    }
    system_prompt = captured["messages"][0]["content"]
    assert "Jaipur" in system_prompt
    assert "Amber Fort" in system_prompt
    assert "18000" in system_prompt
