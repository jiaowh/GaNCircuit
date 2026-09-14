"""Small, validity-aware DC model bridge.

This module intentionally fits only a Shockley diode fixture.  It does not
claim device fabrication, TCAD calibration, or validity outside the declared
data domain.
"""

from __future__ import annotations

import math
import re
import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence
from types import MappingProxyType


class ModelValidationError(ValueError):
    pass


def _finite(value: Any, where: str) -> None:
    if isinstance(value, bool):
        raise ModelValidationError(f"{where} must be finite numeric")
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ModelValidationError(f"{where} must be finite")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _finite(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _finite(item, f"{where}[{index}]")


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class CharacterizationDataset:
    records: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    train_ids: frozenset[str]
    holdout_ids: frozenset[str]

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ModelValidationError("dataset provenance is required")
        try:
            json.dumps(_thaw(self.provenance), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ModelValidationError("provenance must be finite JSON") from exc
        ids: set[str] = set()
        normalized = []
        for record in self.records:
            if not isinstance(record, Mapping) or not isinstance(record.get("id"), str) or not record["id"]:
                raise ModelValidationError("each record requires a non-empty string id")
            rid = record["id"]
            if rid in ids:
                raise ModelValidationError(f"duplicate record id: {rid}")
            ids.add(rid)
            _finite(record, f"record {rid}")
            if not isinstance(record.get("voltage"), (int, float)) or not isinstance(record.get("current"), (int, float)):
                raise ModelValidationError(f"record {rid} requires numeric voltage/current")
            normalized.append(dict(record))
        if self.train_ids & self.holdout_ids:
            raise ModelValidationError("train and holdout IDs must be disjoint")
        if not self.train_ids <= ids or not self.holdout_ids <= ids:
            raise ModelValidationError("split contains unknown record ID")
        if not self.train_ids or not self.holdout_ids:
            raise ModelValidationError("both train and holdout splits are required")
        object.__setattr__(self, "records", tuple(_freeze(r) for r in normalized))
        object.__setattr__(self, "provenance", _freeze(dict(self.provenance)))

    @property
    def fingerprint(self) -> str:
        value = {"records": _thaw(self.records), "provenance": _thaw(self.provenance), "train": sorted(self.train_ids), "holdout": sorted(self.holdout_ids)}
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

    @classmethod
    def from_records(cls, records: Sequence[Mapping[str, Any]], provenance: Mapping[str, Any], train_ids: Sequence[str], holdout_ids: Sequence[str]) -> "CharacterizationDataset":
        return cls(tuple(records), provenance, frozenset(train_ids), frozenset(holdout_ids))

    def split(self, ids: frozenset[str]) -> tuple[Mapping[str, Any], ...]:
        return tuple(record for record in self.records if record["id"] in ids)


@dataclass(frozen=True)
class DCModel:
    name: str
    device_revision: str
    temperature_bounds: tuple[float, float]
    bias_bounds: tuple[float, float]
    supports: tuple[str, ...] = ("OP", "DC")
    validated: bool = False
    validation: Mapping[str, Any] | None = None
    dataset_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.device_revision, str) or not self.device_revision:
            raise ModelValidationError("device_revision is required")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in self.temperature_bounds + self.bias_bounds):
            raise ModelValidationError("bounds must be finite numeric")
        if self.temperature_bounds[0] > self.temperature_bounds[1] or self.temperature_bounds[0] <= 0:
            raise ModelValidationError("invalid temperature bounds")
        if self.bias_bounds[0] > self.bias_bounds[1]:
            raise ModelValidationError("invalid bias bounds")
        if not set(self.supports) <= {"OP", "DC"}:
            raise ModelValidationError("unsupported analysis")
        if self.validated and (not self.validation or not self.dataset_hash):
            raise ModelValidationError("validated models require validation evidence and dataset identity")
        if self.validation is not None:
            object.__setattr__(self, "validation", _freeze(dict(self.validation)))

    def in_domain(self, voltage: float, temperature: float) -> bool:
        return self.bias_bounds[0] <= voltage <= self.bias_bounds[1] and self.temperature_bounds[0] <= temperature <= self.temperature_bounds[1]


@dataclass(frozen=True)
class ShockleyDiodeModel(DCModel):
    saturation_current: float = 0.0
    ideality: float = 0.0
    reference_temperature: float = 300.0
    thermal_voltage: float = 0.025851999786

    def __post_init__(self) -> None:
        super().__post_init__()
        for value, name in ((self.saturation_current, "saturation_current"), (self.ideality, "ideality"), (self.reference_temperature, "reference_temperature"), (self.thermal_voltage, "thermal_voltage")):
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ModelValidationError(f"{name} must be finite and positive")

    @classmethod
    def fit(cls, dataset: CharacterizationDataset, *, device_revision: str, temperature_bounds: tuple[float, float] = (300.0, 300.0), bias_bounds: tuple[float, float] | None = None, name: str = "DIODE") -> "ShockleyDiodeModel":
        if dataset.provenance.get("device_revision") != device_revision:
            raise ModelValidationError("dataset device_revision does not match model device_revision")
        if temperature_bounds != (300.0, 300.0):
            raise ModelValidationError("the fixture supports 300 K only")
        train = dataset.split(dataset.train_ids)
        if any(float(r.get("temperature", 300.0)) != 300.0 for r in dataset.records):
            raise ModelValidationError("the fixture requires all records at 300 K")
        if any(float(r["current"]) <= 0 for r in train):
            raise ModelValidationError("Shockley log fit requires positive training currents")
        if bias_bounds is None:
            bias_bounds = (min(float(r["voltage"]) for r in train), max(float(r["voltage"]) for r in train))
        xs = [float(r["voltage"]) for r in train]
        ys = [math.log(float(r["current"])) for r in train]
        xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
        denom = sum((x - xbar) ** 2 for x in xs)
        if denom <= 0:
            raise ModelValidationError("training voltages must vary")
        slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / denom
        if slope <= 0:
            raise ModelValidationError("fit produced non-positive diode slope")
        intercept = ybar - slope * xbar
        return cls(name=name, device_revision=device_revision, temperature_bounds=temperature_bounds, bias_bounds=bias_bounds, saturation_current=math.exp(intercept), ideality=1.0 / (slope * 0.025851999786), reference_temperature=300.0, dataset_hash=dataset.fingerprint)

    def current(self, voltage: float, temperature: float = 300.0) -> float:
        if not self.in_domain(voltage, temperature):
            raise ModelValidationError("bias or temperature is outside model domain")
        vt = 0.025851999786 * temperature / self.reference_temperature
        return self.saturation_current * math.expm1(float(voltage) / (self.ideality * vt))

    def heldout_error(self, dataset: CharacterizationDataset) -> float:
        errors = []
        for record in dataset.split(dataset.holdout_ids):
            actual = float(record["current"])
            predicted = self.current(float(record["voltage"]), float(record.get("temperature", self.reference_temperature)))
            errors.append(abs(predicted - actual) / max(abs(actual), 1e-300))
        return sum(errors) / len(errors)

    def validate(self, dataset: CharacterizationDataset, *, max_relative_error: float) -> "ShockleyDiodeModel":
        if not isinstance(max_relative_error, (int, float)) or isinstance(max_relative_error, bool) or not math.isfinite(max_relative_error) or max_relative_error <= 0:
            raise ModelValidationError("max_relative_error must be finite and positive")
        if dataset.fingerprint != self.dataset_hash:
            raise ModelValidationError("validation dataset does not match fitted dataset")
        error = self.heldout_error(dataset)
        if error > max_relative_error:
            raise ModelValidationError(f"held-out relative error {error} exceeds {max_relative_error}")
        return replace(self, validated=True, validation={"dataset_provenance": dict(dataset.provenance), "heldout_relative_error": error, "max_relative_error": max_relative_error})

    def export_spice(self) -> str:
        if not self.validated:
            raise ModelValidationError("SPICE export requires held-out validation")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.name):
            raise ModelValidationError("unsafe SPICE model name")
        return f".model {self.name} D(Is={self.saturation_current:.17g} N={self.ideality:.17g} TNOM=26.85)\n"
