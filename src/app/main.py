from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from google_auth_oauthlib.flow import Flow

app = FastAPI()

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
]

@app.get("/")
def health():
    return {"status": "running"}

@app.get("/auth")
def login():
    # trigger google OAuth flow
    # use my client credentials to authorize access into user google account
    # grab access token to call gmail API on behalf of user
    flow = Flow.from_client_secrets_file('credentials.json', scopes=SCOPES)
    flow.redirect_uri = 'http://localhost:8000/auth/callback'

    # first step of the OAuth flow - generate the authorization URL
    # using configuration of my client
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    return RedirectResponse(url=authorization_url)

@app.get("/auth/callback")
def callback(request: Request):
    pass