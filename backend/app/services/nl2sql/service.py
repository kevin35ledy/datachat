from __future__ import annotations
import re
import structlog
from typing import TYPE_CHECKING
from app.core.exceptions import (
    SQLExtractionError, SQLValidationError, SQLSecurityError,
    LLMError, SchemaNotFoundError,
)
from app.core.models.query import ChatResponse, SQLQuery
from app.services.nl2sql.sql_validator import SQLValidator
from app.services.nl2sql.prompt_builder import PromptBuilder
from app.services.nl2sql.sql_executor import SQLExecutor
from app.services.nl2sql.result_formatter import ResultFormatter

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.connector import AbstractDatabaseConnector
    from app.core.interfaces.llm_provider import AbstractLLMProvider
    from app.core.models.schema import SchemaInfo
    from app.core.models.chat import ChatMessage
    from app.core.models.query import NLQuery

logger = structlog.get_logger()


class NL2SQLService:
    """
    Orchestrates the full 10-step NL→SQL→Result pipeline.

    Steps:
      1. Schema RAG   — retrieve relevant tables
      2. Prompt build — assemble context + history + rules
      3. LLM generate — produce SQL + explanation
      4. SQL extract  — isolate SQL block from response
      5. AST validate — sqlglot parse + type check
      6. Safety gate  — whitelist / blocklist
      7. Table validate — check references exist in schema
      8. Complexity   — inject LIMIT
      9. Execute      — run via connector with timeout
     10. Format       — enrich columns + chart suggestion + NL summary
    """

    def __init__(
        self,
        settings: "Settings",
        llm: "AbstractLLMProvider",
    ):
        self._settings = settings
        self._llm = llm
        self._validator = SQLValidator()
        self._prompt_builder = PromptBuilder()
        self._executor = SQLExecutor(settings)
        self._formatter = ResultFormatter()

    async def generate_and_run(
        self,
        nl_query: "NLQuery",
        connector: "AbstractDatabaseConnector",
        schema_info: "SchemaInfo",
        history: list["ChatMessage"],
        relevant_tables: list[str] | None = None,
    ) -> ChatResponse:
        """Execute the full pipeline. Returns a ChatResponse (may contain error)."""
        log = logger.bind(
            conn_id=nl_query.connection_id,
            session_id=nl_query.session_id,
        )

        # Step 2: Build prompt
        request = self._prompt_builder.build(
            nl_query=nl_query.text,
            schema_info=schema_info,
            relevant_tables=relevant_tables,
            history=history,
            dialect=connector.dialect,
        )

        # Step 3: LLM generation
        try:
            log.info("nl2sql_generating", query=nl_query.text[:100])
            llm_response = await self._llm.complete(request)
        except Exception as e:
            log.error("nl2sql_llm_error", error=str(e))
            return ChatResponse(
                session_id=nl_query.session_id,
                nl_query=nl_query.text,
                error=f"LLM error: {str(e)}",
            )

        # Step 4: Extract SQL
        try:
            raw_sql = SQLValidator.extract_sql(llm_response.content)
        except SQLExtractionError as e:
            return ChatResponse(
                session_id=nl_query.session_id,
                nl_query=nl_query.text,
                error=str(e),
            )

        # Extract explanation and confidence from LLM response
        explanation = _extract_explanation(llm_response.content)
        confidence = _extract_confidence(llm_response.content)

        # Steps 5-8: Validate
        try:
            validated_sql = self._validator.validate(
                sql=raw_sql,
                dialect=connector.dialect,
                schema_info=schema_info,
            )
        except (SQLSecurityError, SQLValidationError) as e:
            log.warning("nl2sql_validation_failed", error=str(e), sql=raw_sql[:200])
            return ChatResponse(
                session_id=nl_query.session_id,
                nl_query=nl_query.text,
                sql_query=SQLQuery(
                    raw_sql=raw_sql,
                    validated_sql="",
                    dialect=connector.dialect,
                    is_safe=False,
                    explanation=explanation,
                    confidence=confidence,
                ),
                error=str(e),
            )

        sql_query = SQLQuery(
            raw_sql=raw_sql,
            validated_sql=validated_sql,
            dialect=connector.dialect,
            explanation=explanation,
            confidence=confidence,
        )

        # Step 9: Execute
        try:
            result = await self._executor.execute(validated_sql, connector)
        except Exception as e:
            log.error("nl2sql_execution_error", error=str(e))
            return ChatResponse(
                session_id=nl_query.session_id,
                nl_query=nl_query.text,
                sql_query=sql_query,
                error=str(e),
            )

        # Step 10: Format
        result = self._formatter.format(result)
        chart = self._formatter.infer_chart(result)

        # Generate NL summary (lightweight — use a fast model)
        summary = await self._summarize(nl_query.text, validated_sql, result)

        log.info("nl2sql_complete", rows=result.total_count, ms=result.execution_time_ms)
        return ChatResponse(
            session_id=nl_query.session_id,
            nl_query=nl_query.text,
            sql_query=sql_query,
            result=result,
            chart_suggestion=chart,
            summary=summary,
        )

    async def _summarize(self, nl_query: str, sql: str, result) -> str:
        """Generate a short NL summary of the results using a fast model."""
        if result.total_count == 0:
            return "Aucun résultat trouvé pour cette requête."
        try:
            from app.core.models.chat import LLMRequest
            sample = result.rows[:3]
            prompt = (
                f"Question: {nl_query}\n"
                f"SQL exécuté: {sql[:300]}\n"
                f"Résultat: {result.total_count} ligne(s). Échantillon: {sample}\n\n"
                "Résume en 1-2 phrases ce que montrent ces résultats. "
                "Sois concis et en français."
            )
            req = LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=120,
                model_override=self._settings.litellm_summary_model,
            )
            resp = await self._llm.complete(req)
            return resp.content.strip()
        except Exception:
            return f"{result.total_count} résultat(s) trouvé(s)."


def _extract_explanation(response: str) -> str:
    m = re.search(r"<explanation>(.*?)</explanation>", response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def _extract_confidence(response: str) -> float:
    m = re.search(r"<confidence>\s*([0-9.]+)\s*</confidence>", response, re.IGNORECASE)
    if m:
        try:
            return max(0.0, min(1.0, float(m.group(1))))
        except ValueError:
            pass
    return 1.0
