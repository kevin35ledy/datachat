import pytest
from app.services.nl2sql.prompt_builder import PromptBuilder
from app.core.models.chat import LLMRequest


@pytest.fixture
def builder():
    return PromptBuilder()


class TestPromptBuilder:
    def test_builds_valid_request(self, builder, sample_schema):
        request = builder.build(
            nl_query="Combien de clients avons-nous ?",
            schema_info=sample_schema,
            relevant_tables=None,
            history=[],
            dialect="sqlite",
        )
        assert isinstance(request, LLMRequest)
        assert len(request.messages) >= 1
        assert request.temperature == 0.1

    def test_includes_dialect_in_system(self, builder, sample_schema):
        request = builder.build(
            nl_query="test",
            schema_info=sample_schema,
            relevant_tables=None,
            history=[],
            dialect="postgres",
        )
        system_content = request.messages[0]["content"]
        assert "postgres" in system_content

    def test_includes_table_names_in_schema(self, builder, sample_schema):
        request = builder.build(
            nl_query="test",
            schema_info=sample_schema,
            relevant_tables=None,
            history=[],
            dialect="sqlite",
        )
        system_content = request.messages[0]["content"]
        assert "clients" in system_content
        assert "commandes" in system_content

    def test_filters_to_relevant_tables(self, builder, sample_schema):
        request = builder.build(
            nl_query="test",
            schema_info=sample_schema,
            relevant_tables=["clients"],
            history=[],
            dialect="sqlite",
        )
        system_content = request.messages[0]["content"]
        assert "clients" in system_content
        # commandes should not be in context when filtered out
        assert "commandes" not in system_content

    def test_user_query_is_last_message(self, builder, sample_schema):
        query = "Quelles sont les villes représentées ?"
        request = builder.build(
            nl_query=query,
            schema_info=sample_schema,
            relevant_tables=None,
            history=[],
            dialect="sqlite",
        )
        assert request.messages[-1]["role"] == "user"
        assert request.messages[-1]["content"] == query

    def test_history_trimming(self, builder, sample_schema):
        from app.core.models.chat import ChatMessage
        import uuid
        history = [
            ChatMessage(id=str(uuid.uuid4()), session_id="s", role="user", content=f"question {i}")
            for i in range(20)
        ]
        request = builder.build(
            nl_query="nouvelle question",
            schema_info=sample_schema,
            relevant_tables=None,
            history=history,
            dialect="sqlite",
        )
        # Should not include all 20 history messages
        assert len(request.messages) < 25
