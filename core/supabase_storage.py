import os
import uuid
from typing import Any, Dict, Optional

from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from django.conf import settings

try:
    # Supabase python client v2.x typically exports at the top-level
    from supabase import create_client
except ImportError:  # pragma: no cover
    # Fallback for environments where `create_client` isn't top-level
    from supabase.client import create_client


def _get_env(key: str, default: str = "") -> str:
    """Get env var from os.environ or Django settings"""
    # Try os.environ first (for deployment)
    value = os.environ.get(key)
    if value:
        return value
    # Fallback to Django settings (for testing)
    return getattr(settings, key, default)


@deconstructible
class SupabaseStorage(Storage):
    """
    Django Storage implementation that uploads to Supabase Storage.

    Notes:
    - Uses NEXT_PUBLIC_SUPABASE_ANON_KEY for read operations.
    - Uses SUPABASE_SERVICE_ROLE_KEY for write operations (bypasses RLS policies).
    """

    def __init__(
        self,
        bucket_name: str = "product-images",
        folder: str = "",
    ) -> None:
        self.bucket_name = bucket_name
        self.folder = folder.strip("/")

        supabase_url = _get_env("NEXT_PUBLIC_SUPABASE_URL")
        anon_key = _get_env("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        service_role_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url:
            # Use placeholder for migrations (won't actually be used)
            supabase_url = "https://placeholder.supabase.co"
            anon_key = "placeholder-anon-key"
            service_role_key = "placeholder-service-key"

        # anon key client for read operations (public access)
        self.supabase = create_client(supabase_url, anon_key)
        
        # service role client for write operations (bypasses RLS)
        self.supabase_admin = create_client(supabase_url, service_role_key)

    def _make_object_key(self, name: str) -> str:
        filename = name.split("/")[-1]
        unique = uuid.uuid4().hex
        key = f"{unique}-{filename}"
        if self.folder:
            return f"{self.folder}/{key}"
        return key

    def _get_public_url(self, object_key: str) -> str:
        # Supabase public URL format:
        # {supabase_url}/storage/v1/object/public/{bucket}/{object_key}
        supabase_url = os.environ["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/")
        return f"{supabase_url}/storage/v1/object/public/{self.bucket_name}/{object_key}"

    def _save(self, name: str, content: Any) -> str:
        object_key = self._make_object_key(name)

        # DRF/Django may pass UploadedFile or similar; ensure we upload bytes.
        content.seek(0)
        data = content.read()

        # Upload to Supabase using admin client (bypasses RLS policies)
        bucket = self.supabase_admin.storage.from_(self.bucket_name)
        # content-disposition/content-type can be added later; keeping simple for now.
        upload_response = bucket.upload(
            object_key,
            data,
            {"contentType": getattr(content, "content_type", None)} if getattr(content, "content_type", None) else None,
        )

        # supabase-py returns `data`/`error` style; be defensive
        error = getattr(upload_response, "error", None) or getattr(upload_response, "errors", None)
        if error:
            raise RuntimeError(f"Supabase upload failed: {error}")

        # Django expects return value to be "name" stored in the field (relative key)
        return object_key

    def exists(self, name: str) -> bool:
        # Best-effort check; Storage API requires exists()
        try:
            bucket = self.supabase.storage.from_(self.bucket_name)
            # list path with exact prefix; simplest is to check if it can generate signed URL
            # If bucket is public, this is often unnecessary.
            bucket.createSignedUrl(name, 60)
            return True
        except Exception:
            return False

    def url(self, name: str) -> str:
        return self._get_public_url(name)

    def get_available_name(self, name: str, max_length: Optional[int] = None) -> str:
        # Ensure no collision logic is needed; we already prefix with UUID in _make_object_key.
        return name

    def delete(self, name: str) -> None:
        bucket = self.supabase_admin.storage.from_(self.bucket_name)
        bucket.remove([name])
