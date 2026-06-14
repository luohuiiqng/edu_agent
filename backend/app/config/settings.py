from dataclasses import dataclass
import os


def _normalize_base_url(url: str | None) -> str | None:
    if not url:
        return None
    cleaned = url.rstrip("/")
    if cleaned.endswith("/v1"):
        return cleaned
    return f"{cleaned}/v1"


@dataclass
class Settings:
    openai_api_key: str | None
    openai_model: str
    openai_base_url: str | None
    openai_organization: str | None
    store_backend: str
    runtime_db_path: str | None
    model_provider: str

    @classmethod
    def from_env(cls) -> "Settings":
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        if deepseek_key:
            return cls(
                openai_api_key=deepseek_key,
                openai_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                openai_base_url=_normalize_base_url(
                    os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
                ),
                openai_organization=None,
                store_backend=os.getenv("STORE_BACKEND", "memory"),
                runtime_db_path=os.getenv("RUNTIME_DB_PATH"),
                model_provider="deepseek",
            )

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4"),
            openai_base_url=_normalize_base_url(os.getenv("OPENAI_BASE_URL")),
            openai_organization=os.getenv("OPENAI_ORGANIZATION"),
            store_backend=os.getenv("STORE_BACKEND", "memory"),
            runtime_db_path=os.getenv("RUNTIME_DB_PATH"),
            model_provider="openai",
        )
