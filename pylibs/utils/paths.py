"""Path and resource helpers for pyLIBS."""

from pathlib import Path


def app_base_dir() -> Path:
    """Directory of the application root, used for pyLIBS.ini, databases and resources."""
    try:
        return Path(__file__).resolve().parents[2]
    except Exception:
        return Path.cwd()


def resource_path(filename: str) -> Path:
    """Return a resource beside the application, falling back to the current directory."""
    path = app_base_dir() / filename
    if path.exists():
        return path
    return Path.cwd() / filename


def docs_dir() -> Path:
    return app_base_dir() / "docs"


def manual_path() -> Path:
    return docs_dir() / "pyLIBS_Manual.pdf"


def icon_dirs() -> list[Path]:
    base_dir = app_base_dir()
    return [base_dir / "icons", base_dir / "Icons"]


def find_icon_path(filename):
    if not filename:
        return None
    for icon_dir in icon_dirs():
        icon_path = icon_dir / filename
        if icon_path.exists():
            return icon_path
    filename_lower = str(filename).lower()
    for icon_dir in icon_dirs():
        if not icon_dir.exists():
            continue
        for icon_path in sorted(icon_dir.iterdir()):
            if icon_path.name.lower() == filename_lower:
                return icon_path
    return None
