# backend\app\core\load_env.py

import os
from dotenv import load_dotenv

load_dotenv()

# LinkedIn Developer App Credentials
LINKEDIN_AUTH_URL = os.getenv("LINKEDIN_AUTH_URL")
LINKEDIN_TOKEN_URL = os.getenv("LINKEDIN_TOKEN_URL")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
LINKEDIN_SCOPES = os.getenv("LINKEDIN_SCOPES")