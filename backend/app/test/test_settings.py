import os

from app.config.settings import Settings


os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_MODEL"] = "test-model"
os.environ["OPENAI_BASE_URL"] = "https://example.com/v1"
os.environ["OPENAI_ORGANIZATION"] = "test-org"
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DEEPSEEK_API_BASE", None)
os.environ.pop("DEEPSEEK_MODEL", None)
os.environ["STORE_BACKEND"] = "sqlite"
os.environ["RUNTIME_DB_PATH"] = "/tmp/runtime.db"

settings = Settings.from_env()

assert settings.openai_api_key == "test-key"
assert settings.openai_model == "test-model"
assert settings.openai_base_url == "https://example.com/v1"
assert settings.openai_organization == "test-org"
assert settings.model_provider == "openai"
assert settings.store_backend == "sqlite"
assert settings.runtime_db_path == "/tmp/runtime.db"

os.environ.pop("OPENAI_MODEL", None)
os.environ.pop("STORE_BACKEND", None)
os.environ.pop("RUNTIME_DB_PATH", None)

default_settings = Settings.from_env()

assert default_settings.openai_model == "gpt-5.4"
assert default_settings.store_backend == "memory"
assert default_settings.runtime_db_path is None

os.environ["DEEPSEEK_API_KEY"] = "sk-deepseek-test"
os.environ["DEEPSEEK_MODEL"] = "deepseek-chat"
os.environ["DEEPSEEK_API_BASE"] = "https://api.deepseek.com"
deepseek_settings = Settings.from_env()
assert deepseek_settings.model_provider == "deepseek"
assert deepseek_settings.openai_api_key == "sk-deepseek-test"
assert deepseek_settings.openai_model == "deepseek-chat"
assert deepseek_settings.openai_base_url == "https://api.deepseek.com/v1"

os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DEEPSEEK_MODEL", None)
os.environ.pop("DEEPSEEK_API_BASE", None)

print("settings tests passed")
