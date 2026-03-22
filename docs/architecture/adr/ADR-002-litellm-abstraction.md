# ADR-002 — Abstraction LLM via LiteLLM

**Statut** : Accepté
**Date** : 2026-03-22

## Contexte

DB-IA doit supporter plusieurs providers LLM (Claude, OpenAI, Ollama, etc.) et permettre de les swapper sans changer de code. Les APIs des providers changent fréquemment. La dépendance directe à un seul SDK provider crée un risque de lock-in.

## Décision

Utiliser **LiteLLM** comme couche d'abstraction sur tous les providers LLM, avec un `AbstractLLMProvider` Protocol en Python pour permettre des implémentations alternatives.

## Architecture

```python
# Interface stable (app/core/interfaces/llm_provider.py)
class AbstractLLMProvider(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]: ...
    async def embed(self, text: str) -> list[float]: ...

# Implémentation via LiteLLM (app/llm/base.py)
class BaseLLMProvider:
    async def complete(self, request: LLMRequest) -> LLMResponse:
        response = await litellm.acompletion(
            model=self.model_name,
            messages=request.messages,
            **self.provider_options
        )
        return LLMResponse(content=response.choices[0].message.content)
```

Changer de provider = changer la variable d'environnement `LITELLM_DEFAULT_MODEL` :
- `claude-sonnet-4-6` → Anthropic Claude
- `gpt-4o` → OpenAI
- `ollama/llama3.1` → Ollama local

## Alternatives considérées

### A. SDK direct Anthropic

```python
import anthropic
client = anthropic.Anthropic()
response = client.messages.create(model="claude-sonnet-4-6", ...)
```

**Rejeté** : Crée un couplage fort à Anthropic. Changer de provider = refactoring de code. Les APIs changent (ex: messages vs completions).

### B. LangChain ChatModels

```python
from langchain_anthropic import ChatAnthropic
```

**Rejeté** : LangChain est une dépendance lourde avec beaucoup de code non utilisé. Son abstraction est plus complexe que nécessaire pour notre usage (appels LLM directs, pas de chaînes complexes).

### C. LiteLLM (choisi)

**Avantages** :
- Supporte 100+ providers avec la même API
- Gestion du retry et du fallback intégrée
- Logging et tracking des coûts intégré
- Streaming unifié sur tous les providers
- Peut agir comme proxy local (pour les environnements sans accès internet direct)

**Inconvénients** :
- Dépendance supplémentaire
- Peut introduire un overhead de version (mais LiteLLM suit rapidement les changements des providers)

## Conséquences

- Tous les appels LLM dans le code doivent passer par `AbstractLLMProvider`
- Les providers spécifiques ne sont instanciés que dans `app/llm/` et injectés via FastAPI DI
- La configuration du modèle est centralisée dans les variables d'environnement
- Un `LLMRegistry` permet de sélectionner le provider via l'UI Settings
