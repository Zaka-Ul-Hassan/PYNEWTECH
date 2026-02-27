# backend\app\services\linkedin\linkedin_auth_service.py

from urllib.parse import quote
import requests

from app.core.load_env import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_REDIRECT_URI,
    LINKEDIN_SCOPES,
    LINKEDIN_AUTH_URL,
    LINKEDIN_TOKEN_URL
)
from app.schemas.linkedin.linkedin_auth_schema import LinkedInAuthURLSchema, LinkedInTokenResponseSchema
from app.schemas.response_schema import ResponseSchema

# Generate LinkedIn authentication URL
def generate_linkedin_auth_url() -> ResponseSchema:
    encoded_redirect = quote(LINKEDIN_REDIRECT_URI, safe="")
    encoded_scope = quote(LINKEDIN_SCOPES, safe="")

    auth_url = f"""
        {LINKEDIN_AUTH_URL}?response_type=code
        &client_id={LINKEDIN_CLIENT_ID}
        &redirect_uri={encoded_redirect}
        &scope={encoded_scope}
    """

    auth_url = "".join(auth_url.split())
    auth_data = LinkedInAuthURLSchema(auth_url=auth_url)

    return ResponseSchema(
        status=True,
        message="LinkedIn auth URL generated successfully",
        data=auth_data
    )


# Callback handling and token exchange
def exchange_code_for_token(auth_code: str = None, error: str = None):
    if error:
        return ResponseSchema(
            status=False,
            message=f"Error during LinkedIn authentication: {error}"
        )
    
    token_url = LINKEDIN_TOKEN_URL
    payload = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(token_url, data=payload, headers=headers)
    token_data = response.json()

    token_schema = LinkedInTokenResponseSchema(**token_data)

    if response.status_code != 200:
        return ResponseSchema(
            status=False,
            message="Failed to obtain access token",
            data=None
        )
    
    return ResponseSchema(
        status=True,
        message="Access token obtained successfully",
        data=token_schema
    )
