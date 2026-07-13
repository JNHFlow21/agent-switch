from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SKILL_HUB = Path.home() / "AgentWorkspace" / "skill-hub"
SKIP_DIRECTORIES = {".git", ".hg", ".svn", "node_modules", "__pycache__", "archives"}


@dataclass(frozen=True)
class SkillSourceInfo:
    id: str
    type: str
    path: str
    ref: str | None
    revision: str | None
    updated_at: str | None
    installed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "type": self.type,
            "path": self.path,
            "ref": self.ref,
            "revision": self.revision,
            "updatedAt": self.updated_at,
            "installed": self.installed,
        }


@dataclass(frozen=True)
class SkillProfileInfo:
    id: str
    project: str
    skill_count: int

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "project": self.project, "skillCount": self.skill_count}


@dataclass(frozen=True)
class SkillInfo:
    id: str
    name: str
    source: str
    path: str
    absolute_path: str
    source_type: str
    ref: str | None
    revision: str | None
    profiles: tuple[str, ...]
    global_active: bool
    status: str
    exists: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "path": self.path,
            "absolutePath": self.absolute_path,
            "sourceType": self.source_type,
            "ref": self.ref,
            "revision": self.revision,
            "profiles": list(self.profiles),
            "globalActive": self.global_active,
            "status": self.status,
            "exists": self.exists,
        }


@dataclass(frozen=True)
class SkillReport:
    hub_path: str
    sources: tuple[SkillSourceInfo, ...]
    profiles: tuple[SkillProfileInfo, ...]
    skills: tuple[SkillInfo, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "hubPath": self.hub_path,
            "sources": [item.to_dict() for item in self.sources],
            "profiles": [item.to_dict() for item in self.profiles],
            "skills": [item.to_dict() for item in self.skills],
            "dormantCount": sum(item.status == "dormant" for item in self.skills),
        }


def skill_hub_path() -> Path:
    return Path(os.environ.get("SKILL_HUB_HOME", DEFAULT_SKILL_HUB)).expanduser().resolve()


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object in {path}")
    return value


def _source_root(hub: Path, spec: dict[str, object]) -> Path:
    if spec.get("type") == "git":
        base = hub / str(spec.get("checkout", ""))
    else:
        base = Path(str(spec.get("path", ""))).expanduser()
    return (base / str(spec.get("skillPath", "."))).resolve()


def _discover_skill_paths(root: Path) -> set[str]:
    if not root.is_dir():
        return set()
    discovered: set[str] = set()
    for current, directories, files in os.walk(root):
        directories[:] = [name for name in directories if name not in SKIP_DIRECTORIES and not name.startswith(".")]
        if "SKILL.md" not in files:
            continue
        relative = Path(current).relative_to(root)
        discovered.add("." if relative == Path(".") else relative.as_posix())
    return discovered


def load_skill_report(hub: Path | None = None) -> SkillReport:
    hub = (hub or skill_hub_path()).expanduser().resolve()
    registry = _read_json(hub / "config" / "registry.json")
    locks = _read_json(hub / "skills.lock.json").get("sources", {})
    source_specs = registry.get("sources", {})
    if not isinstance(source_specs, dict):
        raise ValueError("Skill Hub registry sources must be an object")
    if not isinstance(locks, dict):
        locks = {}

    active: dict[tuple[str, str], dict[str, object]] = {}
    profiles: list[SkillProfileInfo] = []
    for profile_path in sorted((hub / "profiles").glob("*.json")):
        payload = _read_json(profile_path)
        entries = payload.get("skills", [])
        if not isinstance(entries, list):
            entries = []
        profile_id = profile_path.stem
        profiles.append(SkillProfileInfo(profile_id, str(payload.get("project", "")), len(entries)))
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            source = str(entry.get("source", ""))
            relative = str(entry.get("path", "."))
            slot = active.setdefault((source, relative), {"profiles": [], "name": entry.get("name")})
            slot["profiles"].append(profile_id)  # type: ignore[union-attr]

    sources: list[SkillSourceInfo] = []
    skills: list[SkillInfo] = []
    seen: set[tuple[str, str]] = set()
    for source_id, raw_spec in sorted(source_specs.items()):
        if not isinstance(raw_spec, dict):
            continue
        spec = raw_spec
        root = _source_root(hub, spec)
        lock = locks.get(source_id, {})
        if not isinstance(lock, dict):
            lock = {}
        source_type = str(spec.get("type", "local"))
        ref = str(spec["ref"]) if spec.get("ref") is not None else None
        revision = str(lock["shortRevision"]) if lock.get("shortRevision") is not None else None
        sources.append(
            SkillSourceInfo(
                id=source_id,
                type=source_type,
                path=str(root),
                ref=ref,
                revision=revision,
                updated_at=str(lock["updatedAt"]) if lock.get("updatedAt") is not None else None,
                installed=root.is_dir(),
            )
        )
        relative_paths = _discover_skill_paths(root) | {path for source, path in active if source == source_id}
        for relative in sorted(relative_paths):
            key = (source_id, relative)
            seen.add(key)
            activation = active.get(key, {})
            profile_names = tuple(sorted(str(value) for value in activation.get("profiles", [])))
            global_active = "global" in profile_names
            status = "global" if global_active else "project" if profile_names else "dormant"
            absolute = root if relative == "." else root / relative
            name = str(activation.get("name") or (root.name if relative == "." else Path(relative).name))
            skills.append(
                SkillInfo(
                    id=f"{source_id}:{relative}",
                    name=name,
                    source=source_id,
                    path=relative,
                    absolute_path=str(absolute),
                    source_type=source_type,
                    ref=ref,
                    revision=revision,
                    profiles=profile_names,
                    global_active=global_active,
                    status=status if absolute.joinpath("SKILL.md").is_file() else "missing",
                    exists=absolute.joinpath("SKILL.md").is_file(),
                )
            )

    for (source_id, relative), activation in sorted(active.items()):
        if (source_id, relative) in seen:
            continue
        profile_names = tuple(sorted(str(value) for value in activation.get("profiles", [])))
        skills.append(
            SkillInfo(
                id=f"{source_id}:{relative}",
                name=str(activation.get("name") or Path(relative).name),
                source=source_id,
                path=relative,
                absolute_path="",
                source_type="missing",
                ref=None,
                revision=None,
                profiles=profile_names,
                global_active="global" in profile_names,
                status="missing",
                exists=False,
            )
        )

    skills.sort(key=lambda item: (item.status != "global", item.status != "project", item.name.lower(), item.source))
    return SkillReport(str(hub), tuple(sources), tuple(profiles), tuple(skills))


def update_git_skill_sources(hub: Path | None = None) -> str:
    hub = (hub or skill_hub_path()).expanduser().resolve()
    skillctl = hub / "scripts" / "skillctl"
    if not skillctl.is_file():
        raise FileNotFoundError(f"Skill Hub controller not found: {skillctl}")
    result = subprocess.run(
        [str(skillctl), "--hub", str(hub), "fetch"],
        cwd=hub,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        raise RuntimeError(output or f"skillctl fetch exited with code {result.returncode}")
    return output
