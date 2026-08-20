"""Streamlit DB session helpers — no analytics logic."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

import streamlit as st
from sqlalchemy.orm import Session

from app.db.session import create_db_engine, create_session_factory


@st.cache_resource
def _engine():
    return create_db_engine()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    factory = create_session_factory(_engine())
    session = factory()
    try:
        yield session
    finally:
        session.close()
