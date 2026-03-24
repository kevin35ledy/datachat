from __future__ import annotations
import json
import re
import structlog
from typing import TYPE_CHECKING
from app.core.models.clarification import ClarificationQuestion

if TYPE_CHECKING:
    from app.config import Settings
    from app.core.interfaces.llm_provider import AbstractLLMProvider
    from app.core.models.schema import SchemaInfo

logger = structlog.get_logger()

_SYSTEM_PROMPT = """\
Tu es un assistant qui analyse une requête en langage naturel et un schéma de base de données \
pour détecter d'éventuelles ambiguïtés sémantiques.

Réponds UNIQUEMENT avec un tableau JSON (peut être vide []) contenant 0 à 2 objets de la forme :
{
  "id": "slug-court",
  "question": "Question courte posée à l'utilisateur",
  "context": "Contexte : noms de colonnes ou valeurs observées",
  "suggestions": ["option1", "option2", "option3"]
}

Génère des questions UNIQUEMENT si :
- Un nom de colonne est cryptique (ex: 'cod_stt', 'flg_act') et les valeurs sont ambiguës
- Plusieurs colonnes peuvent correspondre à la même notion métier (ex: montant_ht vs montant_ttc)
- La granularité temporelle n'est pas claire (date de commande vs date de livraison)

Ne génère PAS de question si :
- Le schéma est déjà bien annoté (présence de commentaires ou valeurs possibles)
- La requête est simple et sans ambiguïté
- Les noms de colonnes sont explicites
"""


class ClarificationService:

    def __init__(self, settings: "Settings", llm: "AbstractLLMProvider"):
        self._settings = settings
        self._llm = llm

    async def get_questions(
        self,
        nl_text: str,
        schema_info: "SchemaInfo",
    ) -> list[ClarificationQuestion]:
        """Return 0–2 clarification questions for an NL query given the schema."""
        from app.core.models.chat import LLMRequest

        schema_context = schema_info.to_prompt_context()[:2000]

        user_prompt = (
            f"Requête utilisateur : {nl_text}\n\n"
            f"Schéma disponible :\n{schema_context}\n\n"
            "Retourne uniquement le JSON."
        )

        try:
            req = LLMRequest(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
                max_tokens=400,
                model_override=self._settings.litellm_summary_model,
            )
            response = await self._llm.complete(req)
            raw = response.content.strip()

            # Extract JSON array from response (may be wrapped in markdown)
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if not m:
                return []
            data = json.loads(m.group(0))
            return [ClarificationQuestion(**q) for q in data[:2]]
        except Exception as e:
            logger.warning("clarification_failed", error=str(e))
            return []
