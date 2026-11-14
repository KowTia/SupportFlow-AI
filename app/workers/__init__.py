"""Celery worker package for asynchronous ticket triage and outbound routing."""

from app.workers.celery_app import celery_app

__all__ = ["celery_app"]
