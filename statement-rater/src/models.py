"""Data model — generic rating sets → items → judgments.

A *set* is a batch of items with a configurable target number of independent
judgments (K). An *item* is one source statement plus a list of candidate
statements. A *judgment* is one user's verdict on one item; a user judges each
item at most once, and an item retires once it has K judgments.
"""
import json
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, Index

db = SQLAlchemy()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RatingSet(db.Model):
    __tablename__ = 'rating_sets'
    id         = db.Column(String(64), primary_key=True)          # slug, e.g. 'de-en-npov'
    name       = db.Column(String(255), nullable=False)
    k_target   = db.Column(Integer, nullable=False, default=3)     # desired judgments per item
    is_active  = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=_now)


class Item(db.Model):
    __tablename__ = 'items'
    id          = db.Column(Integer, primary_key=True, autoincrement=True)
    set_id      = db.Column(String(64), db.ForeignKey('rating_sets.id', ondelete='CASCADE'), nullable=False)
    ext_id      = db.Column(String(255), nullable=True)            # external ref, e.g. 'dewiki:npov:5'
    source_text = db.Column(Text, nullable=False)                  # English (shown primary)
    source_sub  = db.Column(Text, nullable=True)                   # original language (shown smaller)
    candidates  = db.Column(Text, nullable=False)                  # JSON: [{"id":..., "text":...}, ...]
    n_judgments = db.Column(Integer, nullable=False, default=0)    # denormalised count for retirement
    retired     = db.Column(Boolean, nullable=False, default=False)
    created_at  = db.Column(DateTime, nullable=False, default=_now)
    __table_args__ = (
        Index('ix_items_set_retired', 'set_id', 'retired'),
        UniqueConstraint('set_id', 'ext_id', name='uq_item_set_ext'),
    )

    def candidate_list(self) -> list[dict]:
        return json.loads(self.candidates)


class Judgment(db.Model):
    __tablename__ = 'judgments'
    id             = db.Column(Integer, primary_key=True, autoincrement=True)
    item_id        = db.Column(Integer, db.ForeignKey('items.id', ondelete='CASCADE'), nullable=False)
    set_id         = db.Column(String(64), nullable=False)         # denormalised for easy export
    centralauth_id = db.Column(Integer, nullable=False)
    wiki_username  = db.Column(String(255), nullable=False)
    # verdict JSON: {"none": bool, "ratings": {"<candidate_id>": "full"|"partial", ...}}
    verdict        = db.Column(Text, nullable=False)
    created_at     = db.Column(DateTime, nullable=False, default=_now)
    __table_args__ = (
        UniqueConstraint('item_id', 'centralauth_id', name='uq_judgment_item_user'),
        Index('ix_judgments_set', 'set_id'),
    )
