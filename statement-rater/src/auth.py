"""Auth helpers — adapted from chatstream-moderate (Wikimedia OAuth2 identity)."""
import functools
import hmac

from flask import abort, current_app, redirect, request, session, url_for


def current_centralauth_id() -> int | None:
    return session.get('centralauth_id')


def current_wiki_username() -> str | None:
    return session.get('wiki_username')


def is_superadmin() -> bool:
    return current_wiki_username() in current_app.config.get('SUPERADMIN_USERS', [])


def verify_csrf() -> None:
    token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
    expected = session.get('csrf_token', '')
    if not token or not hmac.compare_digest(str(token), str(expected)):
        abort(403)


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if current_centralauth_id() is None:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def superadmin_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if current_centralauth_id() is None:
            return redirect(url_for('index'))
        if not is_superadmin():
            abort(403)
        return f(*args, **kwargs)
    return decorated
