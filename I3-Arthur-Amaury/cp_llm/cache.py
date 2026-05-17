"""Cache disque pour les appels LLM.

Wrap un LLMClient avec CachedLLMClient(inner=..., cache_dir=...) pour persister
toutes les reponses sur disque, indexees par hash(provider, modele, system,
user[, schema]). Les appels suivants identiques sont servis depuis le cache
sans toucher l'API.

Indispensable pour rendre les demos live reproductibles malgre les rate-limits
Mistral, et pour iterer sur le code de l'app sans re-payer les 4 etages.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from cp_llm.llm_client import LLMClient

T = TypeVar("T", bound=BaseModel)


def _digest(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:24]


class CachedLLMClient(LLMClient):
    """Wrap un LLMClient et persiste les reponses sur disque."""

    def __init__(self, inner: LLMClient, cache_dir: str | Path):
        self._inner = inner
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._provider = type(inner).__name__
        self._model = getattr(inner, "_model", "default")
        self.hits = 0
        self.misses = 0

    def _path(self, key: str, suffix: str) -> Path:
        return self._cache_dir / f"{key}.{suffix}"

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
    ) -> T:
        key = _digest(
            self._provider,
            str(self._model),
            output_schema.__name__,
            system_prompt,
            user_prompt,
        )
        path = self._path(key, "json")
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            self.hits += 1
            return output_schema.model_validate(data)
        result = self._inner.call_structured(system_prompt, user_prompt, output_schema)
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        self.misses += 1
        return result

    def call_text(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.0
    ) -> str:
        # On n'inclut la temperature dans la clef que si elle est non-nulle :
        # garde la backward-compat avec les anciennes entrees de cache.
        parts = [
            self._provider,
            str(self._model),
            "text",
            system_prompt,
            user_prompt,
        ]
        if temperature != 0.0:
            parts.append(f"temp={temperature}")
        key = _digest(*parts)
        path = self._path(key, "txt")
        if path.exists():
            self.hits += 1
            return path.read_text(encoding="utf-8")
        result = self._inner.call_text(system_prompt, user_prompt, temperature=temperature)
        path.write_text(result, encoding="utf-8")
        self.misses += 1
        return result
