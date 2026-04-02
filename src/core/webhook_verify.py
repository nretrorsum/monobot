import base64
import hashlib
import logging

import ecdsa
import httpx

logger = logging.getLogger(__name__)

_cached_pub_key: ecdsa.VerifyingKey | None = None

MONO_PUBKEY_URL = "https://api.monobank.ua/api/merchant/pubkey"


async def _get_monobank_pubkey() -> ecdsa.VerifyingKey:
    global _cached_pub_key
    if _cached_pub_key is not None:
        return _cached_pub_key

    async with httpx.AsyncClient() as client:
        resp = await client.get(MONO_PUBKEY_URL)
        resp.raise_for_status()
        data = resp.json()

    pub_key_base64 = data["key"]
    pub_key_bytes = base64.b64decode(pub_key_base64)
    _cached_pub_key = ecdsa.VerifyingKey.from_pem(pub_key_bytes.decode())
    logger.info("Monobank public key cached successfully")
    return _cached_pub_key


async def verify_webhook_signature(body: bytes, x_sign: str) -> bool:
    try:
        pub_key = await _get_monobank_pubkey()
        signature_bytes = base64.b64decode(x_sign)
        pub_key.verify(
            signature_bytes,
            body,
            sigdecode=ecdsa.util.sigdecode_der,
            hashfunc=hashlib.sha256,
        )
        return True
    except (ecdsa.BadSignatureError, Exception) as e:
        logger.warning("Webhook signature verification failed: %s", e)
        return False
