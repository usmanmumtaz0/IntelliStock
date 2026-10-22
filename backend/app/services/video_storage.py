"""Private media storage for video jobs; only opaque keys leave this module."""
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import BACKEND_DIR, settings

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov"}
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SUPPORTED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "application/octet-stream",
}
SUPPORTED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def storage_root() -> Path:
    configured = Path(settings.VIDEO_STORAGE_ROOT).expanduser()
    root = configured if configured.is_absolute() else BACKEND_DIR.parent / configured
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def storage_node_id() -> str:
    """Return a stable opaque ID shared only by processes using this media volume."""
    marker = storage_root() / ".storage-node-id"
    try:
        return str(UUID(marker.read_text(encoding="ascii").strip()))
    except FileNotFoundError:
        value = str(uuid4())
        try:
            with marker.open("x", encoding="ascii") as stream:
                stream.write(value)
            return value
        except FileExistsError:
            return str(UUID(marker.read_text(encoding="ascii").strip()))
    except (ValueError, OSError) as exc:
        raise RuntimeError("Media storage node marker is invalid or unreadable") from exc


def storage_queue_stage() -> str:
    """Internal durable queue stage that legacy workers cannot claim."""
    return f"storage_queued:{storage_node_id()}"


def safe_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError("Supported video formats are MP4, AVI, and MOV")
    return extension


def safe_image_extension(filename: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError("Supported image formats are JPG, PNG, and WebP")
    return extension


def new_upload_key(job_id: str, filename: str | None) -> str:
    return f"{job_id}/source-{uuid4().hex}{safe_extension(filename)}"


def new_image_key(job_id: str, filename: str | None) -> str:
    return f"{job_id}/source-{uuid4().hex}{safe_image_extension(filename)}"


def new_annotated_key(job_id: str, sequence: int) -> str:
    return f"{job_id}/annotated/frame-{sequence:06d}.jpg"


def resolve_storage_key(key: str) -> Path:
    if not key or Path(key).is_absolute():
        raise ValueError("Invalid media key")
    root = storage_root()
    candidate = (root / key).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Invalid media key") from exc
    return candidate


def remove_job_media(job_id: str) -> None:
    """Remove only files within a validated job directory."""
    root = storage_root()
    directory = (root / job_id).resolve()
    try:
        directory.relative_to(root)
    except ValueError as exc:
        raise ValueError("Invalid job media directory") from exc
    if not directory.is_dir():
        return
    for path in sorted(directory.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            path.rmdir()
    directory.rmdir()
