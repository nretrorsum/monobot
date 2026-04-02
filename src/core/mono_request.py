import aiohttp

MONO_API_URL = "https://api.monobank.ua/"

class MonoRequestService:
    def __init__(self):
        self.request_session: aiohttp.ClientSession = None

    async def __aenter__(self):
        self.request_session = aiohttp.ClientSession(base_url=MONO_API_URL)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.request_session.close()

    async def _make_request(self, endpoint: str, token: str, params: dict | None = None) -> dict:
        headers = {"X-Token": token}
        async with self.request_session.get(endpoint, params=params, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_client_info(self, token: str) -> dict:
        return await self._make_request("/personal/client-info", token)

    async def get_statement_info(self, token: str, account: str, from_ts: int, to_ts: int | None = None) -> list[dict]:
        endpoint = f"/personal/statement/{account}/{from_ts}"
        if to_ts:
            endpoint += f"/{to_ts}"
        return await self._make_request(endpoint, token)

