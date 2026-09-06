from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from google_auth_oauthlib.flow import Flow

app = FastAPI()

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
def login():
    # trigger google OAuth flow
    # use my client credentials to authorize access into user google account
    # grab access token to call gmail API on behalf of user
    flow = build_flow()

    # first step of the OAuth flow - generate the authorization URL
    # using configuration of my client
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    flows[state] = flow

    return RedirectResponse(url=authorization_url)

@app.get("/auth/callback")
def callback(request: Request):
    # use the same flow for state persistence
    state = request.query_params.get("state")
    flow = flows.pop(state)

    # use the url to fetch access token and store it in the flow object
    url = str(request.url)
    flow.fetch_token(authorization_response=url)
    credentials = flow.credentials

    return {"status": "authenticated"}