from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Cookie
from fastapi.responses import RedirectResponse

from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest

import sqlite3
from google.oauth2.credentials import Credentials

import json
import secrets
from typing import Optional

def load_credentials(db, email: str) -> Credentials | None:
    cursor = db.cursor()
    cursor.execute(
        "SELECT credentials_json FROM user_credentials WHERE user_email = ?",
        (email,)
    )
    row = cursor.fetchone()

    if row is None:
        return None

    creds_json = row[0]
    return Credentials.from_authorized_user_info(
        info=json.loads(creds_json), scopes=SCOPES
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_conn = sqlite3.connect("creds.db", check_same_thread=False)
    cursor = app.state.db_conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_credentials (
            user_email TEXT PRIMARY KEY,
            credentials_json TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_email TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    app.state.db_conn.commit()
    
    yield
    
    # shut down at app close
    app.state.db_conn.close()

app = FastAPI(lifespan=lifespan)

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid"
]

flows = {}

def build_flow():
    flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES)
    flow.redirect_uri = 'http://localhost:8000/auth/callback'

    return flow

@app.get("/")
def health(session_id: Optional[str] = Cookie(None)):
    if not session_id:
        return RedirectResponse(url="/auth")
    
    return "Welcome to MitoMail! ~"

@app.get("/auth")
def login(): # include request to avoid circular imports and use app context
    
    flow = build_flow()

    # first step of the OAuth flow - generate the authorization URL
    # using configuration of my client
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    flows[state] = flow

    return RedirectResponse(url=authorization_url)

@app.get("/auth/callback")
def callback(request: Request):
    db = request.app.state.db_conn

    # use the same flow for state persistence
    state = request.query_params.get("state")
    flow = flows.pop(state)

    url = str(request.url)
    flow.fetch_token(authorization_response=url)

    credentials = flow.credentials

    # get email address as id
    ps = build('people', 'v1', credentials=credentials)
    res = ps.people().get(resourceName='people/me', personFields="names,emailAddresses").execute()

    for addr in res.get("emailAddresses", []):
        if addr.get("metadata").get("primary") == True:
            email_address = addr.get("value")

    creds = credentials.to_json()

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO user_credentials (user_email, credentials_json, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_email) DO UPDATE SET
            credentials_json = excluded.credentials_json,
            updated_at = CURRENT_TIMESTAMP
    """, (email_address, creds))

    db.commit()

    session_id = secrets.token_hex(32)
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="session_id", 
        value=session_id,
        httponly=True,
        secure=True,
        samesite="lax"
    )

    cursor.execute(
        "INSERT INTO sessions (session_id, user_email) VALUES (?, ?)",
        (session_id, email_address)
    )
    db.commit()

    return response