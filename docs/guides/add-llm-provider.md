# Guide — Ajouter un provider LLM

Ce guide permet d'ajouter le support d'un nouveau provider LLM en moins d'une heure.

## Étape 1 — Créer le fichier provider

```python
# backend/app/llm/your_provider.py

from app.llm.base import BaseLLMProvider


class YourProvider(BaseLLMProvider):
    """
    Provider LLM pour YourService.

    Variables d'environnement requises:
        YOUR_SERVICE_API_KEY: Clé API YourService

    Modèles supportés:
        - your-model-fast : rapide, économique
        - your-model-pro : qualité maximale

    Exemple de configuration .env:
        LITELLM_DEFAULT_MODEL=yourservice/your-model-pro
        YOUR_SERVICE_API_KEY=sk-...
    """

    def __init__(self, model_name: str = "yourservice/your-model-pro"):
        super().__init__(
            model_name=model_name,
            provider_options={
                # Options spécifiques à ce provider si nécessaire
                # "api_base": "https://api.yourservice.com/v1",
            }
        )
```

Dans la plupart des cas, c'est tout ce qui est nécessaire si LiteLLM supporte déjà ce provider.

## Étape 2 — Enregistrer dans le registry

```python
# backend/app/llm/registry.py — ajouter :

from app.llm.your_provider import YourProvider

LLM_REGISTRY = {
    # ... existants ...
    "yourservice": YourProvider,
}

def get_provider(provider_name: str, model: str | None = None) -> AbstractLLMProvider:
    cls = LLM_REGISTRY.get(provider_name)
    if not cls:
        raise UnsupportedProviderError(f"Unknown LLM provider: {provider_name}")
    return cls(model_name=model or cls.default_model)
```

## Étape 3 — Variables d'environnement

```bash
# Ajouter dans .env.example :
# YourService LLM
# YOUR_SERVICE_API_KEY=    # Requis pour utiliser YourService
```

## Étape 4 — Frontend Settings

```typescript
// frontend/src/pages/SettingsPage.tsx
// Ajouter dans la liste des providers :

const LLM_PROVIDERS = [
  { value: "anthropic", label: "Anthropic Claude", models: ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5-20251001"] },
  { value: "openai", label: "OpenAI", models: ["gpt-4o", "gpt-4o-mini"] },
  { value: "ollama", label: "Ollama (local)", models: ["llama3.1", "sqlcoder", "codellama"] },
  // Ajouter :
  { value: "yourservice", label: "YourService", models: ["your-model-fast", "your-model-pro"] },
];
```

## Cas particulier : provider non supporté par LiteLLM

Si votre provider n'est pas supporté par LiteLLM, vous devez override les méthodes de `BaseLLMProvider` :

```python
class YourProvider(BaseLLMProvider):

    async def complete(self, request: LLMRequest) -> LLMResponse:
        # Appel direct à l'API du provider
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.yourservice.com/v1/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model_name,
                    "messages": request.messages,
                    "temperature": request.temperature or 0.1,
                    "max_tokens": request.max_tokens or 1000,
                }
            )
            data = response.json()
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                model=self.model_name,
                usage={"input_tokens": data["usage"]["prompt_tokens"],
                       "output_tokens": data["usage"]["completion_tokens"]}
            )

    async def embed(self, text: str) -> list[float]:
        # Si votre provider a une API d'embedding
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.yourservice.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": "your-embedding-model", "input": text}
            )
            return response.json()["data"][0]["embedding"]
```

## Checklist avant PR

- [ ] Classe provider créée dans `backend/app/llm/`
- [ ] Enregistrée dans `backend/app/llm/registry.py`
- [ ] Variables d'environnement ajoutées dans `.env.example`
- [ ] Provider visible dans `frontend/src/pages/SettingsPage.tsx`
- [ ] Test manuel : une requête NL fonctionne de bout en bout avec ce provider
- [ ] Limitations documentées (ex: "ne supporte pas le streaming", "pas d'API d'embedding")
