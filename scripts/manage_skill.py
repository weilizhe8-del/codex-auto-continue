"""Install or remove the bundled skill. Python 3.10+, standard library only.

This is a file installer, not the continuation engine. No network calls,
background processes, account access, or automation changes occur here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

SKILL_NAME = "auto-continue"
FILES = ("SKILL.md", "agents/openai.yaml")
RECEIPT = ".auto-continue-install.json"
PACKAGE_ID = "codex-auto-continue"
SOURCE = Path(__file__).resolve().parents[1] / "skills" / SKILL_NAME


class InstallError(Exception):
    """A checked refusal that should be shown without a traceback."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_links(path: Path) -> None:
    # Check before resolve(), which would hide a symlink/junction redirect.
    for part in (path, *path.parents):
        junction = getattr(part, "is_junction", lambda: False)()
        if part.is_symlink() or junction:
            raise InstallError(f"Refusing symbolic link or junction: {part}")
        # Python 3.10/3.11 do not expose Path.is_junction on Windows.
        if os.name == "nt" and part.exists():
            import stat
            attrs = getattr(part.lstat(), "st_file_attributes", 0)
            if attrs & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise InstallError(f"Refusing reparse point: {part}")


def skill_target(codex_home: Path) -> Path:
    home = Path(os.path.abspath(codex_home.expanduser()))
    target = home / "skills" / SKILL_NAME
    reject_links(target)
    resolved = target.resolve()
    if not resolved.is_relative_to(home.resolve()) or resolved.name != SKILL_NAME:
        raise InstallError("Skill path must remain inside the selected Codex home")
    return resolved


def install(codex_home: Path, source: Path = SOURCE) -> Path:
    target = skill_target(codex_home)
    if target.exists():
        raise InstallError(f"Already exists; no files changed: {target}")
    payload = {}
    for relative in FILES:
        file = source / relative
        reject_links(file)
        payload[relative] = file.read_bytes()
    # Read and validate every source before creating anything in the destination.
    if not payload["SKILL.md"].decode("utf-8").startswith("---\n"):
        # Accept CRLF checkouts too.
        if not payload["SKILL.md"].decode("utf-8").startswith("---\r\n"):
            raise InstallError("Source SKILL.md has no YAML frontmatter")
    receipt = {
        "package": PACKAGE_ID,
        "schema": 1,
        "files": {name: digest(data) for name, data in payload.items()},
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.mkdir()  # Exclusive: never merge into an existing installation.
    written: list[Path] = []
    agents_created = False
    try:
        (target / "agents").mkdir()
        agents_created = True
        for relative, data in payload.items():
            file = target / relative
            with file.open("xb") as stream:
                written.append(file)
                stream.write(data)
        with (target / RECEIPT).open("x", encoding="utf-8", newline="\n") as stream:
            written.append(target / RECEIPT)
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    except OSError:
        # Remove only files this call created; never recursively remove a tree.
        for file in reversed(written):
            file.unlink()
        if agents_created:
            (target / "agents").rmdir()
        target.rmdir()
        raise
    return target


def uninstall(codex_home: Path) -> Path:
    target = skill_target(codex_home)
    if not target.is_dir():
        raise InstallError(f"No installed directory: {target}")
    receipt_file = target / RECEIPT
    reject_links(receipt_file)
    if not receipt_file.is_file():
        raise InstallError("No installer receipt; keep this manually installed skill unchanged")
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise InstallError("Invalid installer receipt; no files changed") from exc
    if not isinstance(receipt, dict) or receipt.get("package") != PACKAGE_ID or receipt.get("schema") != 1:
        raise InstallError("Receipt belongs to another package or format")
    hashes = receipt.get("files")
    if not isinstance(hashes, dict) or set(hashes) != set(FILES):
        raise InstallError("Receipt must contain exactly this package's files")
    expected = set(FILES) | {"agents", RECEIPT}
    observed = set()
    # Do not follow unexpected directory links during discovery.
    for directory, dirs, files in os.walk(target, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            reject_links(path)
            observed.add(path.relative_to(target).as_posix())
    if observed != expected:
        raise InstallError("Extra or missing files found; preserve the installation for manual review")
    for relative in FILES:
        file = target / relative
        if not file.is_file() or digest(file.read_bytes()) != hashes[relative]:
            raise InstallError(f"Locally modified file; no files changed: {relative}")
    # Every target is fixed, checked, and remains within the selected skill folder.
    for relative in FILES:
        (target / relative).unlink()
    receipt_file.unlink()
    (target / "agents").rmdir()
    target.rmdir()
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "uninstall"))
    parser.add_argument("--codex-home", type=Path,
                        default=Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex"),
                        help="Codex home (default: CODEX_HOME, otherwise ~/.codex)")
    args = parser.parse_args(argv)
    try:
        target = install(args.codex_home) if args.action == "install" else uninstall(args.codex_home)
    except (InstallError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"{'Installed' if args.action == 'install' else 'Removed'}: {target}")
    if args.action == "uninstall":
        print("Existing scheduled tasks were not changed. Stop them in Codex separately.")
    else:
        print("Open a new Codex turn; invoke $auto-continue in the task chat when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
