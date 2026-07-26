import os
import httpx

def _base_url() -> str:
    url = os.getenv("PII_API_URL", "http://localhost:15500").rstrip("/")
    if not url:
        raise RuntimeError("PII_API_URL is not set — check your .env file.")
    return url

def _headers() -> dict:
    key = os.getenv("PII_API_KEY", "")
    if not key:
        raise RuntimeError("PII_API_KEY is not set — check your .env file.")
    return {"X-Api-Key": key, "Content-Type": "application/json"}


async def anonymize(
    text: str,
    context_id: str,
    language: str = "it",
    mode: str = "tag",
    context_type: str = "embedding",
) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_base_url()}/v1/anonymize",
            headers=_headers(),
            json={
                "text": text,
                "context_id": context_id,
                "context_type": context_type,
                "language": language,
                "mode": mode,
            },
        )
        r.raise_for_status()
        return r.json()


async def deanonymize(
    text: str,
    context_id: str,
    context_type: str = "embedding",
) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_base_url()}/v1/deanonymize",
            headers=_headers(),
            json={"text": text, "context_id": context_id, "context_type": context_type},
        )
        r.raise_for_status()
        return r.json()


async def list_pii_types() -> list:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{_base_url()}/v1/admin/pii-types", headers=_headers())
        r.raise_for_status()
        return r.json()
