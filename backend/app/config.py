from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROVIDER_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o-mini",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    LLM_PROVIDER: str = "groq"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str = ""
    OPENAI_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+psycopg://docschema:docschema@localhost:5434/docschema"
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3012", "http://127.0.0.1:3012"]
    DEV_TENANT_API_KEY: str = "docschema-dev-key"

    def llm_provider(self) -> str:
        p = (self.LLM_PROVIDER or "groq").strip().lower()
        if p not in _PROVIDER_MODELS:
            raise ValueError(f"LLM_PROVIDER must be one of {list(_PROVIDER_MODELS)}")
        return p

    def llm_api_key(self) -> str:
        if self.LLM_API_KEY.strip():
            return self.LLM_API_KEY.strip()
        if self.llm_provider() == "openai":
            return self.OPENAI_API_KEY.strip()
        return self.GROQ_API_KEY.strip()

    def llm_model(self) -> str:
        if self.LLM_MODEL.strip():
            return self.LLM_MODEL.strip()
        if self.llm_provider() == "groq" and self.GROQ_MODEL.strip():
            return self.GROQ_MODEL.strip()
        return _PROVIDER_MODELS[self.llm_provider()]

    def llm_base_url(self) -> str | None:
        if self.llm_provider() == "groq":
            return self.GROQ_BASE_URL.strip() or "https://api.groq.com/openai/v1"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
