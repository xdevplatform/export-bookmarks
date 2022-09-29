import base64
import hashlib
import os
import re
import requests
import pandas as pd
from requests_oauthlib import OAuth2Session
from flask import (
    Flask,
    request,
    redirect,
    session,
    render_template,
    make_response,
)


app = Flask(__name__)
app.secret_key = os.urandom(50)


client_id = os.environ.get("CLIENT_ID")
client_secret = os.environ.get("CLIENT_SECRET")

redirect_uri = os.environ.get("REDIRECT_URI")
auth_url = "https://twitter.com/i/oauth2/authorize"
token_url = "https://api.twitter.com/2/oauth2/token"

# Set the scopes
scopes = ["tweet.read", "users.read", "bookmark.read"]

# Create a code verifier
code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

# Create a code challenge
code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")


def get_bookmarks(user_id, token):
    print("Making a request to the bookmarks endpoint")
    params = {"tweet.fields": "created_at"}
    return requests.request(
        "GET",
        "https://api.twitter.com/2/users/{}/bookmarks".format(user_id),
        headers={"Authorization": "Bearer {}".format(token["access_token"])},
        params=params,
    )


@app.route("/")
def hello():
    return render_template("index.html")


@app.route("/start")
def demo():
    global twitter
    twitter = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
    authorization_url, state = twitter.authorization_url(
        auth_url, code_challenge=code_challenge, code_challenge_method="S256"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/oauth/callback", methods=["GET"])
def callback():
    code = request.args.get("code")
    token = twitter.fetch_token(
        token_url=token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )
    print(token)
    user_me = requests.request(
        "GET",
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": "Bearer {}".format(token["access_token"])},
    ).json()
    print(user_me)
    user_id = user_me["data"]["id"]
    bookmarks = get_bookmarks(user_id, token).json()
    global df
    df = pd.DataFrame(bookmarks["data"])
    return render_template("next.html")


@app.route("/oauth/next")
def export():
    resp = make_response(df.to_csv())
    resp.headers["Content-Disposition"] = "attachment; filename=export.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp


if __name__ == "__main__":
    app.run(debug=True)