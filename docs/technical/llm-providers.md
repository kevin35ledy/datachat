# Providers LLM

## Architecture

Tous les providers implémentent le Protocol `AbstractLLMProvider` défini dans `backend/app/core/interfaces/llm_provider.py`. Ils passent tous par **LiteLLM**, qui fournit une interface unifiée pour 100+ providers.

Changer de provider = changer la variable `LITELLM_DEFAULT_MODEL` dans `.env`.

## Providers supportés

### Anthropic Claude (démarrage, recommandé)

**Variable** : `LITELLM_DEFAULT_MODEL=claude-sonnet-4-6`
**Clé API** : `ANTHROPIC_API_KEY`

Modèles recommandés par cas d'usage :

| Usage | Modèle | Raison |
|-------|--------|--------|
| Génération SQL principale | `claude-sonnet-4-6` | Meilleur équilibre qualité/vitesse |
| Requêtes complexes / audit | `claude-opus-4-6` | Meilleure compréhension contextuelle |
| Résumés NL, classification | `claude-haiku-4-5-20251001` | Rapide, économique pour les tâches simples |

Avantages :
- Excellente compréhension du contexte long (schémas complexes)
- Fiable pour suivre des instructions précises (règles de sécurité SQL)
- Tool use / function calling natif (utilisé pour la génération structurée)

### OpenAI (Phase 2)

**Variable** : `LITELLM_DEFAULT_MODEL=gpt-4o`
**Clé API** : `OPENAI_API_KEY`

Modèles recommandés :

| Usage | Modèle |
|-------|--------|
| Génération SQL principale | `gpt-4o` |
| Tâches légères | `gpt-4o-mini` |

### Ollama — modèles locaux (Phase 2)

**Variable** : `LITELLM_DEFAULT_MODEL=ollama/llama3.1`
**Configuration** : `OLLAMA_API_BASE=http://localhost:11434`
**Aucune clé API requise**

Modèles recommandés pour NL2SQL :
- `ollama/sqlcoder` — spécialisé NL→SQL, très bonnes performances
- `ollama/llama3.1` — généraliste, bon équilibre
- `ollama/codellama` — orienté code

Cas d'usage :
- Environnements avec données ultra-sensibles (données de santé, finance)
- Air-gapped networks (pas d'accès internet)
- Développement offline
- Maîtrise complète des coûts

Limitations :
- Qualité SQL inférieure sur les requêtes très complexes
- Pas de streaming natif sur tous les modèles
- Nécessite une machine avec GPU pour des performances raisonnables

---

## Stratégie multi-modèles

DB-IA peut utiliser **différents modèles pour différentes tâches** dans le même pipeline :

```python
# Configuration recommandée pour optimiser coût/qualité
LLM_MODELS = {
    "sql_generation": "claude-sonnet-4-6",     # Tâche principale, qualité max
    "nl_summary":     "claude-haiku-4-5-20251001",  # Résumé des résultats, rapide
    "audit_analysis": "claude-opus-4-6",       # Analyse complexe de findings
    "embeddings":     "text-embedding-3-small"  # Embeddings schéma (via OpenAI)
}
```

Cette stratégie réduit les coûts de 60-70% par rapport à l'utilisation d'Opus pour tout.

---

## Gestion des coûts

LiteLLM intègre un tracking des tokens et du coût estimé. Chaque appel LLM est loggé avec :
- Modèle utilisé
- Tokens input + output
- Coût estimé en USD
- Latence

Ces métriques sont accessibles dans les logs structurés et pourront alimenter un dashboard dans une version future.

### Estimation des coûts (ordre de grandeur)

| Scénario | Tokens/requête | Coût estimé (Sonnet) |
|----------|---------------|----------------------|
| Requête simple (petite DB) | ~2,000 | ~$0.003 |
| Requête complexe (grande DB, RAG) | ~8,000 | ~$0.012 |
| Audit complet (100 tables) | ~50,000 | ~$0.075 |

---

## Interface AbstractLLMProvider

```python
class AbstractLLMProvider(Protocol):

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Complétion non-streaming. Retourne la réponse complète."""

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Complétion streaming. Yield des tokens au fur et à mesure."""

    async def embed(self, text: str) -> list[float]:
        """Génère un vecteur d'embedding pour la recherche RAG."""

    def count_tokens(self, text: str) -> int:
        """Estime le nombre de tokens pour la gestion du budget."""

    @property
    def model_name(self) -> str: ...

    @property
    def max_context_tokens(self) -> int: ...

    @property
    def supports_streaming(self) -> bool: ...
```

---

## Fallback et résilience

LiteLLM supporte le fallback automatique :

```python
# Configuration dans .env
LITELLM_FALLBACKS=[
    {"model": "claude-sonnet-4-6", "api_key": "..."},
    {"model": "gpt-4o", "api_key": "..."},          # Fallback si Claude down
    {"model": "ollama/llama3.1"}                      # Fallback local si tout le cloud est down
]
```

En cas d'erreur (rate limit, timeout, provider down) :
1. Retry 3x avec backoff exponentiel
2. Si toujours en échec → essaie le provider suivant dans la liste de fallback
3. Si tous les fallbacks échouent → erreur explicite retournée à l'utilisateur

---

## Guide d'ajout d'un provider

Voir [guides/add-llm-provider.md](../guides/add-llm-provider.md) pour le guide pas-à-pas.
