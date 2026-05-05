from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import json

router = APIRouter(prefix='/auth', tags=['auth'])

# Simple in-memory token storage (in production, use JWT properly)
VALID_TOKENS = {
    'demo-access-token': {'username': 'demo', 'expires': datetime.now() + timedelta(days=7)}
}


@router.post('/token/')
async def login(username: str, password: str):
    """Simple login endpoint - always returns a demo token"""
    # In production, verify credentials against a user database
    if not username or not password:
        raise HTTPException(status_code=400, detail='Username and password required')
    
    # Demo: accept any non-empty credentials
    access_token = f"token_{username}_{int(datetime.now().timestamp())}"
    VALID_TOKENS[access_token] = {
        'username': username,
        'expires': datetime.now() + timedelta(days=7)
    }
    
    return {
        'access': access_token,
        'refresh': f'refresh_{username}_{int(datetime.now().timestamp())}'
    }


@router.post('/refresh/')
async def refresh_token(refresh: str):
    """Refresh access token"""
    # Demo: just return a new token
    new_token = f"token_refreshed_{int(datetime.now().timestamp())}"
    return {'access': new_token}
