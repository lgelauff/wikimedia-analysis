"""Minimal progress view (superadmin only) + CSV export of judgments."""
import csv
import io

from flask import Blueprint, Response, render_template
from sqlalchemy import func

from src.auth import superadmin_required
from src.models import Item, Judgment, RatingSet, db

admin_bp = Blueprint('admin', __name__)


@admin_bp.get('/stats')
@superadmin_required
def stats():
    rows = []
    for rs in RatingSet.query.order_by(RatingSet.created_at).all():
        n_items    = Item.query.filter_by(set_id=rs.id).count()
        n_retired  = Item.query.filter_by(set_id=rs.id, retired=True).count()
        n_judg     = Judgment.query.filter_by(set_id=rs.id).count()
        n_raters   = (db.session.query(func.count(func.distinct(Judgment.centralauth_id)))
                      .filter(Judgment.set_id == rs.id).scalar())
        rows.append(dict(set=rs, n_items=n_items, n_retired=n_retired,
                         n_judg=n_judg, n_raters=n_raters,
                         pct=round(100 * n_retired / n_items) if n_items else 0))
    return render_template('stats.html', rows=rows)


@admin_bp.get('/export/<set_id>.csv')
@superadmin_required
def export(set_id: str):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['item_id', 'ext_id', 'centralauth_id', 'wiki_username', 'verdict', 'created_at'])
    q = (db.session.query(Judgment, Item.ext_id)
         .join(Item, Item.id == Judgment.item_id)
         .filter(Judgment.set_id == set_id)
         .order_by(Judgment.item_id))
    for j, ext_id in q:
        w.writerow([j.item_id, ext_id, j.centralauth_id, j.wiki_username, j.verdict, j.created_at.isoformat()])
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename={set_id}_judgments.csv'})
