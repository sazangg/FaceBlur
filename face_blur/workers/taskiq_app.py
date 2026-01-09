"""Taskiq broker entrypoint used by the worker CLI."""

from face_blur.workers import tasks  # noqa: F401
from face_blur.workers.broker import broker

__all__ = ["broker"]
