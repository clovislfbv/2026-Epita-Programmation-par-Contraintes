"""Clients LLM pluggables : Mistral, Anthropic, et Mock pour tests offline."""

from __future__ import annotations

import json
import os
import random
import re
import time
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from cp_llm.schemas import (
    ConstraintSet,
    ConstraintSpec,
    ProblemAnalysis,
    VariableSet,
    VariableSpec,
)

T = TypeVar("T", bound=BaseModel)


def _strip_json_fences(text: str) -> str:
    """Enleve les fences markdown ``` autour d'un bloc JSON, et le texte qui
    encadre l'objet JSON principal s'il est facilement detectable.
    """
    text = text.strip()
    # Cas 1 : fence ```json ... ``` ou ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # Cas 2 : prose avant/apres l'objet. On extrait du premier { au dernier }.
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    return text


class LLMClient:
    """Interface du client LLM. Sous-classer pour brancher un fournisseur."""

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
    ) -> T:
        raise NotImplementedError

    def call_text(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.0
    ) -> str:
        raise NotImplementedError


class MistralClient(LLMClient):
    """Client Mistral via le SDK officiel mistralai.

    Tier gratuit Mistral : https://console.mistral.ai/ (rate-limited mais genereux).
    Le meme modele est utilise pour toutes les etapes par defaut. Override via `model`.
    """

    DEFAULT_MODEL = "codestral-2508"

    def __init__(self, model: str | None = None):
        try:
            from mistralai.client import Mistral
        except ImportError as e:
            raise ImportError(
                "Le package 'mistralai' n'est pas installe. Lance 'pip install mistralai'."
            ) from e

        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY n'est pas defini. Cree une cle sur "
                "https://console.mistral.ai et remplis .env (cf .env.example)."
            )
        self._client = Mistral(api_key=api_key)
        self._model = model or self.DEFAULT_MODEL
        # Free tier Mistral : 1 RPS approximativement. On respace les appels.
        self._min_interval_s = 1.2
        self._last_call_at: float = 0.0

    def _throttle(self) -> None:
        """Espace les appels d'au moins min_interval_s pour respecter le free tier."""
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_call_at = time.monotonic()

    def _call_with_retry(self, fn: Callable[[], T], max_retries: int = 5) -> T:
        """Retry automatique sur 429 (rate limit) avec backoff exponentiel + jitter."""
        from mistralai.client.errors import SDKError

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            self._throttle()
            try:
                return fn()
            except SDKError as exc:
                last_exc = exc
                status = (
                    getattr(exc.raw_response, "status_code", None)
                    if exc.raw_response
                    else None
                )
                if status != 429 or attempt == max_retries - 1:
                    raise
                # Backoff : 2s, 4s, 8s, 16s, 32s avec jitter pour eviter le thundering herd.
                wait = min(2 ** (attempt + 1), 32) + random.uniform(0, 1)
                print(
                    f"  [Mistral 429] retry dans {wait:.1f}s (tentative {attempt + 1}/{max_retries})",
                    flush=True,
                )
                time.sleep(wait)
        assert last_exc is not None
        raise last_exc

    def call_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: type[T],
    ) -> T:
        # Plutot que chat.parse() (qui plante sans diagnostic si Mistral
        # renvoie du JSON imparfait), on guide le modele vers un JSON brut puis
        # on parse + valide nous-memes. Permet de loguer la sortie brute en cas
        # d'echec.
        schema = output_schema.model_json_schema()
        enriched_system = (
            f"{system_prompt}\n\n"
            "REGLES DE FORMAT (strictes) :\n"
            "- Reponds UNIQUEMENT par un JSON valide, sans texte avant ou apres.\n"
            "- Pas de fences markdown (pas de ```json ni de ```).\n"
            "- Toutes les cles entre guillemets doubles.\n"
            "- Pas de commentaires, pas de virgules trainantes.\n\n"
            f"Schema JSON cible (Pydantic v2) :\n{json.dumps(schema, indent=2)}"
        )

        response = self._call_with_retry(
            lambda: self._client.chat.complete(
                model=self._model,
                messages=[
                    {"role": "system", "content": enriched_system},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )
        )
        raw = response.choices[0].message.content
        if not isinstance(raw, str):
            raise RuntimeError(f"Reponse Mistral inattendue (non-string) : {raw!r}")

        cleaned = _strip_json_fences(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"JSON invalide dans la reponse Mistral (modele: {self._model}).\n"
                f"Erreur : {e}\n\n"
                f"Reponse brute (premiers 2000 chars) :\n{raw[:2000]}"
            ) from e

        try:
            return output_schema.model_validate(data)
        except ValidationError as e:
            raise RuntimeError(
                f"JSON valide mais ne respecte pas le schema {output_schema.__name__}.\n"
                f"Validation : {e}\n\n"
                f"JSON recu :\n{json.dumps(data, indent=2)[:2000]}"
            ) from e

    def call_text(
        self, system_prompt: str, user_prompt: str, temperature: float = 0.0
    ) -> str:
        response = self._call_with_retry(
            lambda: self._client.chat.complete(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
        )
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise RuntimeError(f"Reponse inattendue : {content!r}")
        return content
