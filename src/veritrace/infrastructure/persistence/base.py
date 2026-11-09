"""SQLAlchemy Declarative Base for VeriTrace SQLite persistence."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all VeriTrace persistence models."""

