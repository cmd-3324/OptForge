"""Inspect disk usage for a path or every mounted volume."""

from optforge.diskcheck.models import DiskInfo
from optforge.diskcheck.service import DiskService

__all__ = ["DiskInfo", "DiskService"]
