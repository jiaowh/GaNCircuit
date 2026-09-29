"""Immutable artifact storage and a deliberately small circuit representation.

The module has no simulator or device-physics claims.  It only provides the
identity, validation, and patching foundations that those layers can consume.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from types import MappingProxyType


class ValidationError(ValueError):
    """An artifact or circuit does not satisfy the core contract."""


class RevisionConflict(RuntimeError):
    """A patch was based on an older immutable circuit revision."""


_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_KINDS = {"R", "V", "D", "M"}
_TERMINALS = {"R": ("p", "n"), "V": ("p", "n"), "D": ("a", "k"), "M": ("d", "g", "s", "b")}
_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _finite(value: Any, where: str = "value") -> None:
    if isinstance(value, bool):
        raise ValidationError(f"{where} must be finite numeric")
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValidationError(f"{where} must be finite")
        return
    if isinstance(value, Mapping):
        for k, v in value.items():
            _finite(v, f"{where}.{k}")
        return
    if isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _finite(v, f"{where}[{i}]")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value


class ArtifactStore:
    """Content-addressed JSON artifacts with a tiny SQLite provenance index."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.objects.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(self.root / "index.sqlite3"))
        self.db.execute("CREATE TABLE IF NOT EXISTS artifacts (hash TEXT PRIMARY KEY, kind TEXT NOT NULL, parents TEXT NOT NULL, size INTEGER NOT NULL)")
        self.db.commit()

    def close(self) -> None:
        """Release the index file; Windows cannot delete a store while it is open."""
        self.db.close()

    def __enter__(self) -> "ArtifactStore":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def put(self, kind: str, payload: Any, parents: Sequence[str] = ()) -> str:
        if not isinstance(kind, str) or not kind or not _NAME.fullmatch(kind):
            raise ValidationError("kind must be a safe non-empty name")
        parent_ids = tuple(parents)
        for parent in parent_ids:
            if not self.has(parent):
                raise ValidationError(f"missing parent artifact: {parent}")
        try:
            encoded_payload = _json(payload)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"payload must be JSON-safe and finite: {exc}") from exc
        document = {"kind": kind, "parents": list(parent_ids), "payload": json.loads(encoded_payload)}
        encoded = _json(document).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        path = self.objects / f"{digest}.json"
        if not path.exists():
            path.write_bytes(encoded)
        self.db.execute("INSERT OR IGNORE INTO artifacts(hash,kind,parents,size) VALUES (?,?,?,?)", (digest, kind, _json(parent_ids), len(encoded)))
        self.db.commit()
        return digest

    def has(self, digest: str) -> bool:
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            return False
        return bool(self.db.execute("SELECT 1 FROM artifacts WHERE hash=?", (digest,)).fetchone())

    def get(self, digest: str) -> dict[str, Any]:
        if not self.has(digest):
            raise KeyError(digest)
        raw = (self.objects / f"{digest}.json").read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValidationError(f"artifact content hash mismatch: {digest}")
        return json.loads(raw.decode("utf-8"))

    def parents(self, digest: str) -> tuple[str, ...]:
        row = self.db.execute("SELECT parents FROM artifacts WHERE hash=?", (digest,)).fetchone()
        if row is None:
            raise KeyError(digest)
        return tuple(json.loads(row[0]))


def _validate_element(element: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(element, Mapping):
        raise ValidationError("each element must be an object")
    name, kind = element.get("name"), element.get("kind")
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValidationError(f"unsafe element name: {name!r}")
    if not isinstance(kind, str) or kind.upper() not in _KINDS:
        raise ValidationError(f"unsupported element kind: {kind!r}")
    kind = kind.upper()
    if name[0].upper() != kind:
        raise ValidationError(f"element {name!r} must use {kind} prefix")
    terminals = element.get("terminals")
    if not isinstance(terminals, Mapping) or set(terminals.keys()) != set(_TERMINALS[kind]):
        raise ValidationError(f"{kind} terminals must be exactly {_TERMINALS[kind]}")
    terms = {}
    for pin in _TERMINALS[kind]:
        net = terminals[pin]
        if not isinstance(net, str) or (net != "0" and not _NAME.fullmatch(net)):
            raise ValidationError(f"unsafe net name: {net!r}")
        terms[pin] = net
    result = {"name": name, "kind": kind, "terminals": terms}
    if kind in {"R", "V"}:
        value = element.get("value")
        _finite(value, f"{name}.value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValidationError(f"{name}.value must be numeric")
        if kind == "R" and value <= 0:
            raise ValidationError(f"{name}.value must be positive")
        result["value"] = value
    else:
        model = element.get("model", kind)
        if not isinstance(model, str) or not _NAME.fullmatch(model):
            raise ValidationError(f"unsafe model name: {model!r}")
        result["model"] = model
        params = element.get("params", {})
        if not isinstance(params, Mapping):
            raise ValidationError(f"{name}.params must be an object")
        for key, value in params.items():
            if not isinstance(key, str) or not _NAME.fullmatch(key):
                raise ValidationError(f"unsafe parameter name: {key!r}")
            _finite(value, f"{name}.params.{key}")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValidationError(f"{name}.params.{key} must be numeric")
        result["params"] = dict(sorted(params.items()))
    return result


@dataclass(frozen=True)
class Circuit:
    elements: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(_validate_element(e) for e in self.elements)
        names = [e["name"].lower() for e in normalized]
        if len(names) != len(set(names)):
            raise ValidationError("element names must be unique")
        object.__setattr__(self, "elements", tuple(_freeze(e) for e in normalized))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Circuit":
        if not isinstance(data, Mapping) or not isinstance(data.get("elements", []), Sequence):
            raise ValidationError("circuit requires an elements list")
        return cls(tuple(data.get("elements", [])))

    def to_dict(self) -> dict[str, Any]:
        return _thaw({"elements": self.elements})

    @property
    def revision(self) -> str:
        return hashlib.sha256(_json(self.to_dict()).encode()).hexdigest()

    def export_spice(self) -> str:
        lines = []
        for e in self.elements:
            t = e["terminals"]
            if e["kind"] in {"R", "V"}:
                lines.append(f"{e['name']} {t['p']} {t['n']} {e['value']}")
            elif e["kind"] == "D":
                lines.append(f"{e['name']} {t['a']} {t['k']} {e['model']}{_params(e['params'])}")
            else:
                lines.append(f"{e['name']} {t['d']} {t['g']} {t['s']} {t['b']} {e['model']}{_params(e['params'])}")
        return "\n".join(lines) + ("\n" if lines else "")

    def patch(self, patch: "CircuitPatch", expected_revision: str | None = None) -> "Circuit":
        expected = patch.expected_revision if expected_revision is None else expected_revision
        if expected != self.revision:
            raise RevisionConflict(f"expected revision {expected}, current is {self.revision}")
        items = {e["name"]: e for e in self.elements}
        for name in patch.remove:
            if name not in items:
                raise ValidationError(f"cannot remove missing element: {name}")
            del items[name]
        for change in patch.upsert:
            element = _validate_element(change)
            items[element["name"]] = element
        for name, updates in patch.connect.items():
            if name not in items:
                raise ValidationError(f"cannot connect missing element: {name}")
            element = dict(items[name]); terms = dict(element["terminals"])
            for pin, net in updates.items():
                if pin not in terms or not isinstance(net, str) or (net != "0" and not _NAME.fullmatch(net)):
                    raise ValidationError(f"invalid terminal connection {name}.{pin}")
                terms[pin] = net
            element["terminals"] = terms
            items[name] = _validate_element(element)
        return Circuit(tuple(items[name] for name in sorted(items)))


def _params(params: Mapping[str, Any]) -> str:
    return "".join(f" {key}={value}" for key, value in sorted(params.items()))


@dataclass(frozen=True)
class CircuitPatch:
    expected_revision: str
    upsert: tuple[dict[str, Any], ...] = ()
    remove: tuple[str, ...] = ()
    connect: Mapping[str, Mapping[str, str]] = None

    def __post_init__(self) -> None:
        if self.connect is None:
            object.__setattr__(self, "connect", {})
