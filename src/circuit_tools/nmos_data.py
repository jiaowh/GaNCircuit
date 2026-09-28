"""Immutable, validity-aware NMOS DC characterization data."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

class NMOSDataError(ValueError):
    """A characterization dataset violates its declared software contract."""

_TERMINALS = frozenset({"gate", "drain", "source", "body"})
_REQUIRED_PROVENANCE = ("device_revision", "mesh_sha256", "physics_sha256")

def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value

def _thaw(value):
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(v) for v in value]
    return value

def _number(value, where):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise NMOSDataError(f"{where} must be finite numeric")
    return float(value)

@dataclass(frozen=True)
class NMOSDataset:
    records: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    train_ids: frozenset[str]
    holdout_ids: frozenset[str]
    temperature_k: float = 300.0

    def __post_init__(self):
        temperature = _number(self.temperature_k, "temperature_k")
        if temperature != 300.0:
            raise NMOSDataError("NMOS DC fixture supports 300 K only")
        if not isinstance(self.provenance, Mapping):
            raise NMOSDataError("provenance is required")
        provenance = dict(self.provenance)
        try:
            json.dumps(provenance, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise NMOSDataError("provenance must be finite JSON") from exc
        for key in _REQUIRED_PROVENANCE:
            value = provenance.get(key)
            if not isinstance(value, str) or not value:
                raise NMOSDataError(f"provenance.{key} must be a non-empty string")
        seen_ids = set()
        seen_biases = set()
        normalized = []
        for record in self.records:
            if not isinstance(record, Mapping):
                raise NMOSDataError("each record must be a mapping")
            rid = record.get("id")
            if not isinstance(rid, str) or not rid:
                raise NMOSDataError("each record requires a non-empty string id")
            if rid in seen_ids:
                raise NMOSDataError(f"duplicate record id: {rid}")
            seen_ids.add(rid)
            vgs = _number(record.get("vgs_v"), f"record {rid}.vgs_v")
            vds = _number(record.get("vds_v"), f"record {rid}.vds_v")
            bias = (vgs, vds)
            if bias in seen_biases:
                raise NMOSDataError(f"duplicate bias point: {bias}")
            seen_biases.add(bias)
            if "temperature_k" in record and _number(record["temperature_k"], f"record {rid}.temperature_k") != 300.0:
                raise NMOSDataError("all records must be at 300 K")
            currents = record.get("currents_a_per_cm")
            if not isinstance(currents, Mapping) or set(currents) != _TERMINALS:
                raise NMOSDataError(f"record {rid}.currents_a_per_cm must contain exactly {_TERMINALS}")
            current_values = {name: _number(currents[name], f"record {rid}.currents_a_per_cm.{name}") for name in _TERMINALS}
            scale = max((abs(v) for v in current_values.values()), default=0.0)
            if scale == 0.0:
                imbalance = 0.0
            else:
                imbalance = abs(sum(v / scale for v in current_values.values())) / sum(abs(v) / scale for v in current_values.values())
            if imbalance > 1e-4:
                raise NMOSDataError(f"record {rid} current imbalance exceeds 1e-4: {imbalance}")
            if record.get("solver_converged") is not True:
                raise NMOSDataError(f"record {rid} solver_converged must be true")
            normalized.append({"id": rid, "vgs_v": vgs, "vds_v": vds,
                               "currents_a_per_cm": current_values, "solver_converged": True})
        if not normalized:
            raise NMOSDataError("at least one record is required")
        train, holdout = frozenset(self.train_ids), frozenset(self.holdout_ids)
        if not train or not holdout:
            raise NMOSDataError("train_ids and holdout_ids must both be nonempty")
        if train & holdout or train | holdout != seen_ids:
            raise NMOSDataError("train and holdout IDs must be disjoint and cover all records")
        object.__setattr__(self, "records", tuple(_freeze(r) for r in normalized))
        object.__setattr__(self, "provenance", _freeze(provenance))
        object.__setattr__(self, "train_ids", train)
        object.__setattr__(self, "holdout_ids", holdout)
        object.__setattr__(self, "temperature_k", temperature)

    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, Any]], provenance: Mapping[str, str],
                     train_ids: Sequence[str], holdout_ids: Sequence[str], temperature_k: float = 300.0):
        return cls(tuple(records), provenance, frozenset(train_ids), frozenset(holdout_ids), temperature_k)

    @property
    def fingerprint(self):
        payload = {"records": _thaw(self.records), "provenance": _thaw(self.provenance),
                   "train_ids": sorted(self.train_ids), "holdout_ids": sorted(self.holdout_ids),
                   "temperature_k": self.temperature_k}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(encoded).hexdigest()

    def to_dict(self):
        return {"schema": "nmos-dc-dataset/1", "records": _thaw(self.records),
                "provenance": _thaw(self.provenance), "train_ids": sorted(self.train_ids),
                "holdout_ids": sorted(self.holdout_ids), "temperature_k": self.temperature_k}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise NMOSDataError("dataset document must be a mapping")
        if value.get("schema") != "nmos-dc-dataset/1":
            raise NMOSDataError("unsupported dataset schema")
        return cls.from_records(value.get("records", ()), value.get("provenance", {}),
                                value.get("train_ids", ()), value.get("holdout_ids", ()),
                                value.get("temperature_k", 300.0))
