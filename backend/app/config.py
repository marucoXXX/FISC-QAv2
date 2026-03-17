import os
import sys
import traceback

from pydantic_settings import BaseSettings


def _debug(msg: str) -> None:
    """デバッグログをstderrに出力"""
    print(f"[DEBUG config] {msg}", file=sys.stderr, flush=True)


def _is_local() -> bool:
    """ローカル環境かどうかを判定"""
    result = os.getenv("DATASTORE_EMULATOR_HOST") is not None
    _debug(f"_is_local() = {result}")
    return result


def _get_secret(secret_id: str) -> str | None:
    """本番環境でSecret Managerからシークレットを取得"""
    _debug(f"_get_secret('{secret_id}') called")

    if _is_local():
        _debug(f"Skipping Secret Manager (local mode)")
        return None

    try:
        _debug(f"Importing secretmanager...")
        from google.cloud import secretmanager
        _debug(f"Import successful")

        _debug(f"Creating SecretManagerServiceClient...")
        client = secretmanager.SecretManagerServiceClient()
        _debug(f"Client created")

        name = f"projects/fisc-qav2/secrets/{secret_id}/versions/latest"
        _debug(f"Accessing secret: {name}")
        response = client.access_secret_version(request={"name": name})
        _debug(f"Secret retrieved successfully (length={len(response.payload.data)})")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        _debug(f"ERROR getting secret '{secret_id}': {type(e).__name__}: {e}")
        _debug(f"Traceback: {traceback.format_exc()}")
        return None


class Settings(BaseSettings):
    cors_origins: str = "http://localhost:5173"
    openai_api_key: str = ""
    openai_model: str = "gpt-5.2-2025-12-11"  # ハードコード（環境変数で上書きしない）
    auth_mock_mode: bool = True
    allowed_emails: str = ""
    gcs_bucket: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _debug(f"Settings.__init__ called")
        _debug(f"Initial openai_api_key from env: {'set' if self.openai_api_key else 'empty'}")

        # 本番環境ではSecret Managerから上書き
        if secret := _get_secret("openai-api-key"):
            self.openai_api_key = secret
            _debug(f"openai_api_key set from Secret Manager")
        else:
            _debug(f"openai_api_key NOT set from Secret Manager")

        if secret := _get_secret("allowed-emails"):
            self.allowed_emails = secret
            _debug(f"allowed_emails set from Secret Manager")

        _debug(f"Final openai_api_key: {'set (len=' + str(len(self.openai_api_key)) + ')' if self.openai_api_key else 'EMPTY'}")

    def get_allowed_emails_list(self) -> list[str]:
        if not self.allowed_emails:
            return []
        return [e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()]

    class Config:
        extra = "ignore"


settings = Settings()
