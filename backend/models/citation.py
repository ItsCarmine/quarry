# Citation model is defined in report.py alongside Report and Conflict.
# This module re-exports for convenience.
from backend.models.report import Citation, Conflict

__all__ = ["Citation", "Conflict"]
