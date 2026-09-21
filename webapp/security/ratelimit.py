"""Rate limit persistente sem guardar IP ou e-mail em texto simples."""

from datetime import timedelta

from sqlalchemy.orm import Session

from models import utcnow_naive
from webapp.models_app import RateLimitBucket
from webapp.security.crypto import token_hash


def consume(
    db: Session,
    *,
    scope: str,
    identifier: str,
    secret: str,
    limit: int,
    window: timedelta,
) -> bool:
    now = utcnow_naive()
    key_hash = token_hash(f"{scope}:{identifier}", secret)
    bucket = db.query(RateLimitBucket).filter(RateLimitBucket.key_hash == key_hash).first()
    if bucket is None:
        bucket = RateLimitBucket(
            key_hash=key_hash,
            scope=scope,
            window_started_at=now,
            count=1,
        )
        db.add(bucket)
        db.commit()
        return True
    if bucket.window_started_at + window <= now:
        bucket.window_started_at = now
        bucket.count = 1
        db.commit()
        return True
    if bucket.count >= limit:
        return False
    bucket.count += 1
    db.commit()
    return True
