#!/usr/bin/env python3
"""Build reproducible local release archives from the public repository."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {"AGENTS.md", "README.md", "ROADMAP.md", "CONTRIBUTING.md", ".gitignore", ".gitattributes", "LICENSE", "NOTICE.md"}
PUBLIC_DIRS = {"docs", "scripts", "tests", "skills"}
EXCLUDED_PARTS = {".git", "__pycache__", ".tmp", "node_modules", ".venv", "venv",
                  "build", "dist", ".pytest_cache"}
PRIVATE_PARTS = {"work", ".codex", ".claude", ".agents", ".vscode", ".idea"}
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
MANIFEST = "skills/civilization-os/references/manifest.json"
SKILL_PREFIX = "skills/civilization-os/"
REQUIRED_FILES = ROOT_FILES | {MANIFEST, SKILL_PREFIX + "SKILL.md", SKILL_PREFIX + "LICENSE", SKILL_PREFIX + "NOTICE.md"}
# Never emit matched private text; these checks report only the relative filename.
PRIVATE_TEXT = (
    ("local-user-path", re.compile(r"(?i)\b[A-Z]:[\\/]+Users[\\/]+(?![<{%$])[^\\/\s<>:\"'|]+")),
    ("private-conversation", re.compile(r"(?i)https?://(?:www\.)?chatgpt\.com/c/")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("credential-token", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b")),
    ("credential-assignment", re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|secret[_-]?key|password)\s*[:=]\s*[\"']([A-Za-z0-9/+_.=-]{16,})[\"']")),
)


class ReleaseError(ValueError):
    """A release cannot be safely or completely constructed."""


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def collect_public_files(root: Path) -> dict[str, bytes]:
    root = root.resolve()
    if not root.is_dir():
        raise ReleaseError("repository: missing directory")
    candidates = []
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED_PARTS)
        for name in directories:
            directory = Path(current) / name
            if directory.is_symlink() or (hasattr(directory, "is_junction") and directory.is_junction()):
                relative = directory.relative_to(root).as_posix()
                raise ReleaseError(f"{relative}: symbolic links are not release files")
        candidates.extend(Path(current) / name for name in filenames)
    files = {}
    for path in sorted(candidates, key=lambda p: p.relative_to(root).as_posix()):
        relative = path.relative_to(root)
        name = relative.as_posix()
        parts = relative.parts
        if any(part in EXCLUDED_PARTS for part in parts):
            continue
        if path.is_symlink():
            raise ReleaseError(f"{name}: symbolic links are not release files")
        if any(part in PRIVATE_PARTS or part.lower().startswith(".env") for part in parts):
            raise ReleaseError(f"{name}: private path is not allowed")
        if len(parts) == 1:
            allowed = name in ROOT_FILES
        else:
            allowed = parts[0] in PUBLIC_DIRS
        if not allowed:
            raise ReleaseError(f"{name}: outside the public file whitelist")
        if path.suffix.lower() in {".pyc", ".pyo", ".pem", ".key"}:
            raise ReleaseError(f"{name}: private or generated file type is not allowed")
        payload = path.read_bytes()
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ReleaseError(f"{name}: public file is not UTF-8 text") from exc
        normalized = content.replace("\\/", "/")
        for reason, pattern in PRIVATE_TEXT:
            if pattern.search(normalized):
                raise ReleaseError(f"{name}: public-content check rejected {reason}")
        files[name] = payload
    missing = sorted(REQUIRED_FILES - files.keys())
    if missing:
        raise ReleaseError("repository: missing required files " + ", ".join(missing))
    for legal_file in ("LICENSE", "NOTICE.md"):
        if files[legal_file] != files[SKILL_PREFIX + legal_file]:
            raise ReleaseError(f"{legal_file}: Skill copy differs from the canonical root bytes")
    return files


def release_version(files: dict[str, bytes]) -> str:
    try:
        value = json.loads(files[MANIFEST].decode("utf-8-sig"))
    except (KeyError, UnicodeDecodeError, ValueError) as exc:
        raise ReleaseError("manifest.json: cannot read release metadata") from exc
    version = value.get("library_version") if isinstance(value, dict) else None
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseError("manifest.json: library_version must be MAJOR.MINOR.PATCH")
    return version


def write_archive(path: Path, entries: dict[str, bytes]) -> None:
    # STORED avoids compression-version differences in otherwise identical ZIPs.
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
        for name in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.internal_attr = 0
            info.compress_type = zipfile.ZIP_STORED
            info.extra = b""
            info.comment = b""
            archive.writestr(info, entries[name])


def verify_archive(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path) as archive:
        if archive.namelist() != sorted(entries):
            raise ReleaseError(f"{path.name}: archive member mismatch")
        for info in archive.infolist():
            if archive.read(info.filename) != entries[info.filename]:
                raise ReleaseError(f"{path.name}: member bytes differ")
            if info.date_time != FIXED_TIME or (info.external_attr >> 16) != (stat.S_IFREG | 0o644):
                raise ReleaseError(f"{path.name}: archive metadata differs")
        if archive.testzip() is not None:
            raise ReleaseError(f"{path.name}: CRC validation failed")


def build_release(root: Path, output_dir: Path, overwrite: bool = False) -> dict:
    root = root.resolve()
    output_dir = output_dir.resolve()
    if output_dir == root or root in output_dir.parents:
        raise ReleaseError("output directory must be outside the repository")
    files = collect_public_files(root)
    version = release_version(files)
    repository_name = f"civilization-os-repository-v{version}.zip"
    skill_name = f"civilization-os-skill-v{version}.zip"
    names = (repository_name, skill_name, "checksums.txt")
    for name in names:
        target = output_dir / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ReleaseError(f"{name}: target must be a regular file")
        if target.exists() and not overwrite:
            raise ReleaseError(f"{name}: already exists; use --overwrite to rebuild")
    repository_entries = {"civilization-os-repo/" + name: data for name, data in files.items()}
    skill_entries = {"civilization-os/" + name[len(SKILL_PREFIX):]: data
                     for name, data in files.items() if name.startswith(SKILL_PREFIX)}
    if not skill_entries:
        raise ReleaseError("civilization-os: no Skill files")
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".civilization-release-", dir=output_dir) as staging_dir:
        staging = Path(staging_dir).resolve()
        if staging.parent != output_dir or not staging.name.startswith(".civilization-release-"):
            raise ReleaseError("staging directory escaped the output directory")
        packages = ((repository_name, repository_entries), (skill_name, skill_entries))
        summary = []
        for name, entries in packages:
            archive_path = staging / name
            write_archive(archive_path, entries)
            verify_archive(archive_path, entries)
            summary.append({"filename": name, "files": len(entries),
                            "sha256": digest(archive_path.read_bytes())})
        checksums = "".join(f"{item['sha256']}  {item['filename']}\n" for item in summary)
        (staging / "checksums.txt").write_text(checksums, encoding="utf-8", newline="\n")
        # Finish verification before modifying any previously built archive.
        for name in names:
            target = output_dir / name
            if overwrite:
                os.replace(staging / name, target)
            else:
                # Exclusive create preserves no-overwrite behavior at write time.
                with target.open("xb") as destination, (staging / name).open("rb") as source:
                    shutil.copyfileobj(source, destination)
        for name, entries in packages:
            verify_archive(output_dir / name, entries)
    return {"version": version, "archives": summary, "checksums": "checksums.txt"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Local directory outside the repository")
    parser.add_argument("--overwrite", action="store_true",
                        help="Replace previously generated local release files")
    args = parser.parse_args(argv)
    try:
        result = build_release(ROOT, args.output_dir, args.overwrite)
    except (ReleaseError, OSError, zipfile.BadZipFile) as exc:
        # OSError messages may carry user-specific absolute paths.
        detail = str(exc) if isinstance(exc, ReleaseError) else type(exc).__name__
        print(f"release error: {detail}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())

