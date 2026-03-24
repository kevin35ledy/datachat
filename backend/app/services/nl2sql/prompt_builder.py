from __future__ import annotations
import structlog
from typing import TYPE_CHECKING
from app.core.models.chat import ChatMessage, LLMRequest

if TYPE_CHECKING:
    from app.core.models.schema import SchemaInfo

logger = structlog.get_logger()

# Token budget allocations for different sections of the prompt
TOKEN_BUDGET = {
    "system": 600,
    "schema": 4000,
    "history": 1200,
    "user_query": 300,
}

SYSTEM_PROMPT_TEMPLATE = """You are an expert SQL assistant. Your job is to translate natural language questions into valid, safe SQL queries.

RULES (strictly enforced — never violate these):
1. Generate ONLY SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, or any DDL/DML.
2. Never access system tables (information_schema, pg_catalog, sqlite_master, mysql.*, etc.)
3. Always include a LIMIT clause when the result could be large. Default to LIMIT 100 unless the user specifies.
4. If a question cannot be answered with the available schema, say so clearly — do NOT invent tables or columns.
5. Use the dialect: {dialect}

RESPONSE FORMAT (always use this exact format):
<sql>
SELECT ...
</sql>
<explanation>
[1-2 sentence plain English explanation of what this query does and any assumptions made]
</explanation>
<confidence>
[a number between 0 and 1 — your confidence that this SQL correctly answers the question]
</confidence>"""

SCHEMA_SECTION_TEMPLATE = """AVAILABLE SCHEMA (database: {database_name}):
{schema_context}"""


class PromptBuilder:
    """
    Assembles the LLM prompt for NL2SQL generation.

    Combines: system instructions + schema context + conversation history + user query.
    Manages token budget to stay within model context limits.
    """

    def build(
        self,
        nl_query: str,
        schema_info: "SchemaInfo",
        relevant_tables: list[str] | None,
        history: list[ChatMessage],
        dialect: str,
    ) -> LLMRequest:
        system = SYSTEM_PROMPT_TEMPLATE.format(dialect=dialect)
        schema_context = schema_info.to_prompt_context(tables=relevant_tables)
        schema_section = SCHEMA_SECTION_TEMPLATE.format(
            database_name=schema_info.database_name,
            schema_context=schema_context,
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": f"{system}\n\n{schema_section}"},
        ]

        # Add recent conversation history (last N exchanges)
        for msg in self._trim_history(history):
            messages.append({"role": msg.role, "content": msg.content})

        # Current user query
        messages.append({"role": "user", "content": nl_query})

        request = LLMRequest(messages=messages, temperature=0.1, max_tokens=1000)

        logger.debug("prompt_built",
            dialect=dialect,
            db=schema_info.database_name,
            history_msgs=len(messages) - 2,
            schema_chars=len(schema_context),
        )
        logger.debug("prompt_system", content=messages[0]["content"])
        logger.debug("prompt_user", content=nl_query)

        return request

    def _trim_history(self, history: list[ChatMessage], max_turns: int = 6) -> list[ChatMessage]:
        """Keep the last max_turns messages (user+assistant pairs)."""
        if not history:
            return []
        recent = history[-max_turns * 2 :] if len(history) > max_turns * 2 else history
        # Only include user/assistant messages, not system
        return [m for m in recent if m.role in ("user", "assistant")]
