import httpx
from config import config
from datetime import datetime


async def get_jwt_token(auth_url: str = None, client_id: str = None, client_secret: str = None):
    payload = {
        "ClientId": config.CLIENT_ID,
        "ClientSecret": config.CLIENT_SECRET
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(config.AUTH_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        
        token_expiry = datetime.fromisoformat(data['accessTokenExpiresAt'])
        token = data['accessToken']

        return token_expiry, token
