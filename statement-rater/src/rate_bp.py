"""Rating flow: serve one random un-judged item, record a verdict, retire at K."""
import json

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import func

from src.auth import (current_centralauth_id, current_wiki_username,
                      login_required, verify_csrf)
from src.models import Item, Judgment, RatingSet, db

rate_bp = Blueprint('rate', __name__)


def _random_func():
    # SQLite uses random(); MariaDB/MySQL uses rand().
    return func.rand() if db.engine.dialect.name == 'mysql' else func.random()


def _next_item(uid: int) -> Item | None:
    """A random active, non-retired item this user has not yet judged."""
    judged = db.session.query(Judgment.item_id).filter(Judgment.centralauth_id == uid)
    return (Item.query
            .join(RatingSet, RatingSet.id == Item.set_id)
            .filter(RatingSet.is_active.is_(True),
                    Item.retired.is_(False),
                    ~Item.id.in_(judged))
            .order_by(_random_func())
            .first())


@rate_bp.get('/rate')
@login_required
def rate():
    uid = current_centralauth_id()
    item = _next_item(uid)
    if item is None:
        done = Judgment.query.filter_by(centralauth_id=uid).count()
        return render_template('done.html', done=done)
    return render_template('rate.html', item=item, candidates=item.candidate_list())


@rate_bp.post('/rate')
@login_required
def submit():
    verify_csrf()
    uid = current_centralauth_id()
    item = db.session.get(Item, request.form.get('item_id', type=int))
    if item is None:
        return redirect(url_for('rate.rate'))

    # Parse the verdict from the form.
    none_selected = request.form.get('none_selected') == '1'
    ratings: dict[str, str] = {}
    if not none_selected:
        for c in item.candidate_list():
            v = request.form.get(f'rating__{c["id"]}')
            if v in ('full', 'partial'):
                ratings[c['id']] = v
    # An empty non-"none" submission is treated as "none of these".
    verdict = {'none': none_selected or not ratings, 'ratings': ratings}

    # Skip if this user already judged it (unique constraint / double submit).
    exists = Judgment.query.filter_by(item_id=item.id, centralauth_id=uid).first()
    if exists is None:
        db.session.add(Judgment(
            item_id=item.id, set_id=item.set_id,
            centralauth_id=uid, wiki_username=current_wiki_username() or '',
            verdict=json.dumps(verdict, ensure_ascii=False),
        ))
        item.n_judgments = (item.n_judgments or 0) + 1
        rs = db.session.get(RatingSet, item.set_id)
        if rs and item.n_judgments >= rs.k_target:
            item.retired = True
        db.session.commit()

    return redirect(url_for('rate.rate'))
