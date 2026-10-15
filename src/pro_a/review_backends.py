"""Inference adapters only; no review state, credentials in output, or authority."""
from dataclasses import replace
from urllib.parse import urlsplit

from .config import LLMConfig
from .llm import ChatLLM
from .workbench.config import BoundaryError


class CompatibleBackend:
    kind = 'REMOTE_API'

    def __init__(self, config: LLMConfig):
        # One physical attempt per execution. Explicit retries keep the same reviewer.
        self.client = ChatLLM(replace(config, max_retries=0))
        self.model = config.model

    def identity(self):
        from .evidence_binding import identity
        return {'kind': self.kind, 'model': self.model,
                'endpoint_sha256': identity(self.client.cfg.base_url),
                'temperature': self.client.cfg.temperature,
                'max_output_tokens': self.client.cfg.max_output_tokens,
                'timeout_seconds': self.client.cfg.timeout_seconds}

    def infer(self, system, user):
        return self.client.json(system, user)

    @property
    def metadata(self):
        return self.client.last_call_metadata


class _LocalConfig(LLMConfig):
    @property
    def api_key(self):
        # Ollama's OpenAI-compatible endpoint does not require a credential.
        return 'ollama'


class OllamaBackend(CompatibleBackend):
    kind = 'LOCAL_OPENAI_COMPATIBLE'

    def __init__(self, model, *, base_url='http://127.0.0.1:11434/v1', timeout_seconds=120,
                 max_output_tokens=32768):
        url = urlsplit(base_url)
        if (url.scheme not in ('http', 'https') or url.hostname not in ('127.0.0.1', '::1', 'localhost')
                or url.username or url.password or url.query or url.fragment):
            raise BoundaryError('LOCAL_ENDPOINT_REQUIRED')
        super().__init__(_LocalConfig(enabled=True, model=model, base_url=base_url,
            timeout_seconds=timeout_seconds, max_output_tokens=max_output_tokens))
