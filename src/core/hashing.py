import asyncio

import bcrypt


async def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt in a thread pool."""
    loop = asyncio.get_event_loop()
    hashed = await loop.run_in_executor(
        None, bcrypt.hashpw, plain.encode(), bcrypt.gensalt()
    )
    return hashed.decode()


async def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash in a thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, bcrypt.checkpw, plain.encode(), hashed.encode()
    )
