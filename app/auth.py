from flask import Blueprint, current_app, session, redirect, url_for
import secrets

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login")
def login():
    azure = current_app.extensions["authlib.integrations.flask_client"].azure
    redirect_uri = current_app.config["AZURE_REDIRECT_URI"]

    # Generate and store nonce in session
    nonce = secrets.token_urlsafe(16)
    session["auth_nonce"] = nonce

    return azure.authorize_redirect(redirect_uri, nonce=nonce)

@auth_bp.route("/callback")
def callback():
    azure = current_app.extensions["authlib.integrations.flask_client"].azure
    token = azure.authorize_access_token()       # exchanges “code” for tokens

    # Get the nonce from session
    nonce = session.get("auth_nonce")
    if not nonce:
        return "Missing nonce in session", 400
    
    user  = azure.parse_id_token(token, nonce=nonce)          # OIDC ID-token → profile

    session["user"] = {
        "name":  user.get("name"),
        "email": user.get("preferred_username") or user.get("email")
    }
    return redirect(url_for("main.index"))       # back to your form

@auth_bp.route("/logout")
def logout():
    session.clear()
    post_logout = url_for("main.index", _external=True)
    return redirect(
        "https://login.microsoftonline.com/common/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={post_logout}"
    )