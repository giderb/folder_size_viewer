"""Windows file metadata: owner, created/modified timestamps."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.models import FileMetadata

logger = logging.getLogger(__name__)

try:
    import win32security
    import pywintypes
    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


def get_metadata(path: Path) -> FileMetadata | None:
    """Return FileMetadata for path, or None on error."""
    try:
        stat = path.stat()
    except OSError:
        return None

    created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    owner = _get_owner(path)

    return FileMetadata(owner=owner, created=created, modified=modified)


def _get_owner(path: Path) -> str:
    if not _WIN32_AVAILABLE:
        return "unknown"
    try:
        sd = win32security.GetFileSecurity(
            str(path), win32security.OWNER_SECURITY_INFORMATION
        )
        sid = sd.GetSecurityDescriptorOwner()
        name, domain, _ = win32security.LookupAccountSid(None, sid)
        return f"{domain}\\{name}" if domain else name
    except Exception:
        logger.debug("Could not get owner for %s", path)
        return "unknown"
