from datetime import datetime, timedelta
import secrets
import hashlib
import base64
from urllib.parse import urlencode
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import requests

from app.core.config import settings
from app.core.database import get_db
from app.crud.user import get_user_by_x_id, create_user_from_x, get_user_by_id
from app.schemas.auth import XAuthInitiate, XAuthCallback, UserToken
from models.models import User, XAuthorization

router = APIRouter()

# In-memory storage for PKCE codes (use Redis in production)
_auth_states = {}


def generate_pkce_challenge():
    """Generate PKCE code verifier and challenge for OAuth 2.0"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


@router.post("/x/login", response_model=XAuthInitiate)
def initiate_x_login():
    """Initiate X.com OAuth 2.0 login flow"""
    if not settings.x_client_id or not settings.x_redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="X.com OAuth not configured. Please set X_CLIENT_ID and X_REDIRECT_URI environment variables."
        )
    
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce_challenge()
    state = secrets.token_urlsafe(32)
    
    # Store PKCE parameters temporarily (use Redis in production)
    _auth_states[state] = {
        'code_verifier': code_verifier,
        'timestamp': datetime.utcnow()
    }
    
    # Build X.com OAuth authorization URL
    auth_params = {
        'response_type': 'code',
        'client_id': settings.x_client_id,
        'redirect_uri': settings.x_redirect_uri,
        'scope': 'tweet.read users.read',
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256'
    }
    
    auth_url = f"https://twitter.com/i/oauth2/authorize?{urlencode(auth_params)}"
    
    return XAuthInitiate(auth_url=auth_url, state=state)


@router.post("/x/callback")
def handle_x_callback(callback_data: XAuthCallback, db: Session = Depends(get_db)):
    """Handle X.com OAuth callback and create/login user"""
    
    # Validate state parameter
    if callback_data.state not in _auth_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    
    stored_data = _auth_states.pop(callback_data.state)
    code_verifier = stored_data['code_verifier']
    
    # Check for errors in callback
    if callback_data.error:
        raise HTTPException(status_code=400, detail=f"X.com OAuth error: {callback_data.error}")
    
    if not callback_data.code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # Exchange authorization code for access token
    token_data = {
        'client_id': settings.x_client_id,
        'client_secret': settings.x_client_secret,
        'code': callback_data.code,
        'grant_type': 'authorization_code',
        'redirect_uri': settings.x_redirect_uri,
        'code_verifier': code_verifier
    }
    
    try:
        token_response = requests.post(
            'https://api.twitter.com/2/oauth2/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        token_response.raise_for_status()
        token_info = token_response.json()
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange code for token: {str(e)}")
    
    # Get user info from X API
    access_token = token_info['access_token']
    
    try:
        user_response = requests.get(
            'https://api.twitter.com/2/users/me',
            headers={'Authorization': f'Bearer {access_token}'},
            params={'user.fields': 'id,username,name,profile_image_url,verified'}
        )
        user_response.raise_for_status()
        user_data = user_response.json()['data']
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to get user info from X: {str(e)}")
    
    # Create or get existing user
    user = get_user_by_x_id(db, user_data['id'])
    
    if not user:
        # Create new user
        user = create_user_from_x(db, user_data)
    
    # Store/update X authorization tokens
    x_auth = user.x_authorization
    if not x_auth:
        x_auth = XAuthorization(
            user_id=user.id,
            access_token=access_token,  # In production, encrypt this
            refresh_token=token_info.get('refresh_token'),
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_info.get('expires_in', 7200)),
            scopes=token_info.get('scope', 'tweet.read users.read')
        )
        db.add(x_auth)
    else:
        x_auth.access_token = access_token
        x_auth.refresh_token = token_info.get('refresh_token')
        x_auth.token_expires_at = datetime.utcnow() + timedelta(seconds=token_info.get('expires_in', 7200))
        x_auth.scopes = token_info.get('scope', 'tweet.read users.read')
        x_auth.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Create session token (simplified - use JWT or secure sessions in production)
    session_token = secrets.token_urlsafe(32)
    
    return UserToken(
        access_token=session_token,
        token_type="bearer",
        user_id=user.id,
        x_username=user.x_username,
        x_display_name=user.x_display_name
    )


# Placeholder for session-based authentication
# In production, implement proper JWT or session management
async def get_current_user(db: Session = Depends(get_db)):
    """Get current authenticated user from session"""
    # This is a placeholder - implement proper session/JWT validation
    # For now, this will need to be implemented based on your session strategy
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Please implement session management."
    )


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "x_user_id": current_user.x_user_id,
        "x_username": current_user.x_username,
        "x_display_name": current_user.x_display_name,
        "email": current_user.email,
        "username": current_user.username,
        "profile_picture_url": current_user.profile_picture_url,
        "strava_connected": current_user.strava_athlete_id is not None,
        "backfill_status": current_user.backfill_status
    }