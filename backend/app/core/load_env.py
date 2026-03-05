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

# Zoom Developer App Credentials
ZM_RTMS_CLIENT=os.getenv("ZM_RTMS_CLIENT")
ZM_RTMS_SECRET=os.getenv("ZM_RTMS_SECRET")

# Load Zoom paths from environment
ZOOM_EXE_PATHS = [
    os.path.expandvars(os.getenv("ZOOM_PATH_1", "")),
    os.path.expandvars(os.getenv("ZOOM_PATH_2", "")),
    os.path.expandvars(os.getenv("ZOOM_PATH_3", ""))
]

# Zoom URL
ZOOM_DESKTOP_BASE_URL = os.getenv("ZOOM_DESKTOP_BASE_URL")
ZOOM_WEB_BASE_URL = os.getenv("ZOOM_WEB_BASE_URL")