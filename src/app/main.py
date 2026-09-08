from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from google_auth_oauthlib.flow import Flow

import sqlite3

import requests
import json

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
def health():
    return {"status": "running"}

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
    db = request.app.state.db_conn # get db conn to save and use access/refresh tokens

    # use the same flow for state persistence
    state = request.query_params.get("state")
    flow = flows.pop(state)

    # use the url to fetch access token and store it in the flow object
    url = str(request.url)
    flow.fetch_token(authorization_response=url)
    
    # need to save credentials. right now a new refresh token is being made thanks to "consent" param.
    # refresh token only is grabbed at first time logging in and giving consent
    credentials = flow.credentials

    return {"status": "authenticated"}