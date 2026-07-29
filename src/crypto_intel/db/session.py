from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_intel.settings import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
   return create_engine(
      get_settings().postgres.url,
      pool_pre_ping=True,
      future=True 
   ) 


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return  sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )

@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

