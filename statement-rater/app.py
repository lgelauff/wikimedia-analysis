"""app.py — Flask application factory for statement-rater.

Crowdsources equivalence ratings for statement alignment. Wikimedia OAuth2
identity (meta.wikimedia.org), SQLite for local dev / MariaDB on Toolforge.
OAuth/secret patterns adapted from chatstream-moderate.
"""
import base64
import hashlib
import json as _json
import os
import secrets
import urllib.parse

import requests
from flask import Flask, redirect, render_template, request, session, url_for

from src.models import db

TOOL_NAME = "statement-rater"

# ── Community configuration ───────────────────────────────────────────────────
# Wikimedia usernames allowed to see /stats and export judgments.
SUPERADMIN_USERS: list[str] = ["Effeietsanders"]
# ── End of community configuration ────────────────────────────────────────────


def _read_secret(name: str, default: str = '') -> str:
    """Toolforge secret file, falling back to an env var (NAME with - → _)."""
    try:
        with open(f'/etc/passwords/{name}') as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.environ.get(name.upper().replace('-', '_'), default)


def _db_uri() -> str:
    host = _read_secret('db-host', 'tools.db.svc.wikimedia.cloud')
    user = _read_secret('db-user')
    pw   = _read_secret('db-password')
    name = _read_secret('db-name')
    if user and pw and name:
        return f'mysql+pymysql://{user}:{pw}@{host}/{name}?charset=utf8mb4'
    return 'sqlite:///dev.db'


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY                     = _read_secret('secret-key') or secrets.token_hex(32),
        SQLALCHEMY_DATABASE_URI        = _db_uri(),
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        SESSION_COOKIE_HTTPONLY        = True,
        SESSION_COOKIE_SAMESITE        = 'Lax',
        SUPERADMIN_USERS               = SUPERADMIN_USERS,
        OAUTH_CLIENT_ID                = _read_secret('oauth-client-id'),
        OAUTH_CLIENT_SECRET            = _read_secret('oauth-client-secret'),
        OAUTH_REDIRECT_URI             = _read_secret(
            'oauth-redirect-uri', 'http://localhost:5000/oauth-callback'),
    )
    if test_config:
        app.config.update(test_config)
    if not app.debug:
        app.config['SESSION_COOKIE_SECURE'] = True

    db.init_app(app)
    app.jinja_env.filters['fromjson'] = _json.loads
    with app.app_context():
        db.create_all()

    from src.admin_bp import admin_bp
    from src.rate_bp import rate_bp
    app.register_blueprint(rate_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def _ensure_csrf():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)

    @app.context_processor
    def _globals():
        from src.auth import current_wiki_username, is_superadmin
        return dict(
            csrf_token       = session.get('csrf_token', ''),
            current_username = current_wiki_username(),
            is_superadmin    = is_superadmin(),
            tool_name        = TOOL_NAME,
        )

    # ── Landing ────────────────────────────────────────────────────────────────
    @app.get('/')
    def index():
        from src.auth import current_centralauth_id
        if current_centralauth_id() is not None:
            return redirect(url_for('rate.rate'))
        return render_template('index.html', oauth_ready=bool(app.config.get('OAUTH_CLIENT_ID')))

    # ── Wikimedia OAuth2 (PKCE) ──────────────────────────────────────────────────
    @app.get('/login')
    def login():
        if not app.config.get('OAUTH_CLIENT_ID'):
            return 'OAuth not configured — set OAUTH_CLIENT_ID/SECRET/REDIRECT_URI', 503
        verifier  = secrets.token_urlsafe(64)
        state     = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        session['oauth_state']         = state
        session['oauth_code_verifier'] = verifier
        params = urllib.parse.urlencode({
            'response_type': 'code',
            'client_id':     app.config['OAUTH_CLIENT_ID'],
            'redirect_uri':  app.config['OAUTH_REDIRECT_URI'],
            'scope':         'basic',
            'state':         state,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
        })
        return redirect(f'https://meta.wikimedia.org/w/rest.php/oauth2/authorize?{params}')

    @app.get('/oauth-callback')
    def oauth_callback():
        if request.args.get('state') != session.pop('oauth_state', None):
            return 'OAuth error: state mismatch', 400
        verifier = session.pop('oauth_code_verifier', '')
        try:
            tok = requests.post(
                'https://meta.wikimedia.org/w/rest.php/oauth2/access_token',
                data={'grant_type': 'authorization_code', 'code': request.args.get('code'),
                      'redirect_uri': app.config['OAUTH_REDIRECT_URI'],
                      'client_id': app.config['OAUTH_CLIENT_ID'],
                      'client_secret': app.config['OAUTH_CLIENT_SECRET'],
                      'code_verifier': verifier}, timeout=10)
            tok.raise_for_status()
            prof = requests.get(
                'https://meta.wikimedia.org/w/rest.php/oauth2/resource/profile',
                headers={'Authorization': f'Bearer {tok.json()["access_token"]}'}, timeout=10)
            prof.raise_for_status()
            profile = prof.json()
        except Exception as exc:
            app.logger.warning('OAuth callback failed: %s', exc)
            return 'OAuth login failed', 500
        cid, username = profile.get('sub'), profile.get('username')
        if not cid or not username:
            return 'OAuth profile missing required fields', 500
        session.clear()
        session['centralauth_id'] = int(cid)
        session['wiki_username']  = username
        return redirect(url_for('rate.rate'))

    @app.post('/logout')
    def logout():
        from src.auth import verify_csrf
        verify_csrf()
        session.clear()
        return redirect(url_for('index'))

    if app.debug:
        @app.get('/dev-login')
        def dev_login():
            username = request.args.get('username', '').strip()
            if not username:
                return 'Usage: /dev-login?username=YourName', 400
            session.clear()
            session['centralauth_id'] = abs(hash(username)) % 10_000_000
            session['wiki_username']  = username
            return redirect(url_for('rate.rate'))

    return app


app = create_app()
