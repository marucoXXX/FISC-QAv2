import uuid
from pathlib import Path

from app.config import settings

# ローカル開発時のアップロードディレクトリ
UPLOAD_DIR = Path(__file__).parent.parent.parent / "uploads"

# GCSクライアント（遅延初期化）
_gcs_client = None
_gcs_bucket = None


def _get_gcs_bucket():
    """GCSバケットを取得（遅延初期化）"""
    global _gcs_client, _gcs_bucket
    if _gcs_bucket is None and settings.gcs_bucket:
        from google.cloud import storage
        _gcs_client = storage.Client()
        _gcs_bucket = _gcs_client.bucket(settings.gcs_bucket)
    return _gcs_bucket


def save_file(candidate_id: str, file_name: str, content: bytes) -> str:
    """
    ファイルを保存し、パスを返す。
    GCS_BUCKETが設定されている場合: GCS
    それ以外: ローカルファイルシステム（開発用）
    """
    ext = Path(file_name).suffix
    unique_name = f"{uuid.uuid4()}{ext}"

    bucket = _get_gcs_bucket()
    if bucket:
        # GCSに保存
        blob_path = f"{candidate_id}/{unique_name}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(content)
        return f"gs://{settings.gcs_bucket}/{blob_path}"
    else:
        # ローカルに保存（開発用）
        candidate_dir = UPLOAD_DIR / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        file_path = candidate_dir / unique_name
        file_path.write_bytes(content)
        return str(file_path)


def delete_file(file_path: str) -> bool:
    """ファイルを削除する"""
    try:
        if file_path.startswith("gs://"):
            # GCSから削除
            bucket = _get_gcs_bucket()
            if bucket:
                blob_path = file_path.replace(f"gs://{settings.gcs_bucket}/", "")
                blob = bucket.blob(blob_path)
                blob.delete()
                return True
            return False
        else:
            # ローカルから削除
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
    except Exception:
        return False


def get_file(file_path: str) -> bytes | None:
    """ファイルを読み込む"""
    try:
        if file_path.startswith("gs://"):
            # GCSから読み込み
            bucket = _get_gcs_bucket()
            if bucket:
                blob_path = file_path.replace(f"gs://{settings.gcs_bucket}/", "")
                blob = bucket.blob(blob_path)
                return blob.download_as_bytes()
            return None
        else:
            # ローカルから読み込み
            path = Path(file_path)
            if path.exists():
                return path.read_bytes()
            return None
    except Exception:
        return None
