from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sarvam_api_key: str = "changeme"
    sarvam_base_url: str = "https://api.sarvam.ai"
    chroma_persist_dir: str = "./data/chroma"
    faq_pdf_path: str = "data/faq.pdf"
    products_json_path: str = "data/products.json"
    chroma_faq_collection: str = "faq"
    chroma_products_collection: str = "products"
    cache_ttl_seconds: int = 3600
    max_rag_results: int = 5
    log_level: str = "INFO"

    # Twilio telephony
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    # Hostname for webhook + WebSocket URLs (no scheme, no trailing slash)
    # Dev: abc123.ngrok.io   Prod: your-app.onrender.com
    public_host: str = "localhost:8000"

    class Config:
        # .env.local (gitignored) takes precedence over .env (committed).
        # On Render, secrets are injected as real env vars which override both.
        env_file = (".env", ".env.local")
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
