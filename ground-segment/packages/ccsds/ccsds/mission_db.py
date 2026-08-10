"""Load and validate the mission database (etana.yaml) into typed objects.

The YAML is a three-level reference chain: a container field references a
parameter, a parameter references a parameter type. This module resolves that
chain at load time so consumers (encoder, decoder) walk a container's fields
without re-parsing YAML or following references.

Only byte-aligned field sizes (multiples of 8 bits) and big-endian byte order
are supported, matching the current mission database.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_ENCODINGS = {"unsigned_int", "signed_int"}
_SUPPORTED_BYTE_ORDER = "big_endian"
_APID_MAX = 2047


class MissionDatabaseError(ValueError):
    """Raised when the mission database is malformed or inconsistent."""


@dataclass(frozen=True)
class Calibrator:
    """A polynomial calibration curve: engineering = sum(coeff[i] * raw**i)."""

    kind: str
    coefficients: tuple[float, ...]

    def apply(self, raw: float) -> float:
        """Convert a raw value to engineering units (Horner evaluation)."""
        result = 0.0
        for coeff in reversed(self.coefficients):
            result = result * raw + coeff
        return result


@dataclass(frozen=True)
class ParameterType:
    """How a value is encoded on the wire and, optionally, calibrated."""

    name: str
    encoding: str          # "unsigned_int" | "signed_int"
    size_bits: int
    unit: str | None = None
    calibrator: Calibrator | None = None
    enumeration: dict[int, str] | None = None

    @property
    def size_bytes(self) -> int:
        return self.size_bits // 8

    @property
    def signed(self) -> bool:
        return self.encoding == "signed_int"


@dataclass(frozen=True)
class Field:
    """A resolved field in a container: its name plus the fully-resolved type.

    parameter_name is the mission-database parameter this field came from, or
    None for inline structural fields such as onboard_time.
    """

    name: str
    type: ParameterType
    parameter_name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Container:
    """One packet definition, identified by APID, with an ordered field list."""

    name: str
    apid: int
    rate_hz: float
    description: str
    fields: tuple[Field, ...]

    @property
    def data_length_bytes(self) -> int:
        """Total size of the data field (excludes the 6-byte primary header)."""
        return sum(f.type.size_bytes for f in self.fields)


@dataclass(frozen=True)
class MissionDatabase:
    """The whole mission database, with references resolved."""

    name: str
    vehicle: str
    byte_order: str
    ccsds_version: int
    sequence_flags: int
    parameter_types: dict[str, ParameterType]
    containers: dict[str, Container]

    def __post_init__(self) -> None:
        by_apid: dict[int, Container] = {}
        for container in self.containers.values():
            by_apid[container.apid] = container
        object.__setattr__(self, "_by_apid", by_apid)

    def container_for_apid(self, apid: int) -> Container:
        """Return the container matching an APID, or raise if none does."""
        try:
            return self._by_apid[apid]
        except KeyError:
            raise MissionDatabaseError(f"no container defined for APID {apid}")

    def container(self, name: str) -> Container:
        try:
            return self.containers[name]
        except KeyError:
            raise MissionDatabaseError(f"no container named {name!r}")


def load_mission_db(path: str | Path) -> MissionDatabase:
    """Load, validate, and resolve a mission database YAML file."""
    with open(path) as handle:
        raw = yaml.safe_load(handle)
    return _build(raw)


def _build(raw: dict) -> MissionDatabase:
    mission = _require(raw, "mission", "top level")
    byte_order = mission.get("byte_order", _SUPPORTED_BYTE_ORDER)
    if byte_order != _SUPPORTED_BYTE_ORDER:
        raise MissionDatabaseError(
            f"unsupported byte_order {byte_order!r}; only {_SUPPORTED_BYTE_ORDER} is supported"
        )
    ccsds = mission.get("ccsds", {})

    parameter_types = _build_types(_require(raw, "parameter_types", "top level"))
    parameters = _build_parameters(
        _require(raw, "parameters", "top level"), parameter_types
    )
    containers = _build_containers(
        _require(raw, "containers", "top level"), parameter_types, parameters
    )

    return MissionDatabase(
        name=mission.get("name", "unnamed"),
        vehicle=mission.get("vehicle", "unnamed"),
        byte_order=byte_order,
        ccsds_version=ccsds.get("version", 0),
        sequence_flags=ccsds.get("sequence_flags", 0b11),
        parameter_types=parameter_types,
        containers=containers,
    )


def _build_types(raw_types: dict) -> dict[str, ParameterType]:
    types: dict[str, ParameterType] = {}
    for name, spec in raw_types.items():
        encoding = _require(spec, "encoding", f"type {name!r}")
        if encoding not in _ENCODINGS:
            raise MissionDatabaseError(
                f"type {name!r}: unknown encoding {encoding!r}; expected one of {sorted(_ENCODINGS)}"
            )
        size_bits = _require(spec, "size_bits", f"type {name!r}")
        if size_bits <= 0 or size_bits % 8 != 0:
            raise MissionDatabaseError(
                f"type {name!r}: size_bits {size_bits} must be a positive multiple of 8"
            )

        calibrator = None
        if "calibrator" in spec:
            cal = spec["calibrator"]
            kind = cal.get("type")
            if kind != "polynomial":
                raise MissionDatabaseError(
                    f"type {name!r}: unsupported calibrator type {kind!r}; only polynomial is supported"
                )
            coeffs = cal.get("coefficients")
            if not coeffs:
                raise MissionDatabaseError(
                    f"type {name!r}: polynomial calibrator needs coefficients"
                )
            calibrator = Calibrator(kind="polynomial", coefficients=tuple(float(c) for c in coeffs))

        enumeration = None
        if "enumeration" in spec:
            enumeration = {int(k): str(v) for k, v in spec["enumeration"].items()}

        types[name] = ParameterType(
            name=name,
            encoding=encoding,
            size_bits=size_bits,
            unit=spec.get("unit"),
            calibrator=calibrator,
            enumeration=enumeration,
        )
    return types


def _build_parameters(
    raw_params: dict, types: dict[str, ParameterType]
) -> dict[str, dict]:
    """Return a name -> {type, description} map, validating type references."""
    params: dict[str, dict] = {}
    for name, spec in raw_params.items():
        type_name = _require(spec, "type", f"parameter {name!r}")
        if type_name not in types:
            raise MissionDatabaseError(
                f"parameter {name!r} references unknown type {type_name!r}"
            )
        params[name] = {"type": type_name, "description": spec.get("description")}
    return params


def _build_containers(
    raw_containers: dict,
    types: dict[str, ParameterType],
    params: dict[str, dict],
) -> dict[str, Container]:
    containers: dict[str, Container] = {}
    seen_apids: dict[int, str] = {}

    for name, spec in raw_containers.items():
        apid = _require(spec, "apid", f"container {name!r}")
        if not 0 <= apid <= _APID_MAX:
            raise MissionDatabaseError(
                f"container {name!r}: apid {apid} out of range 0..{_APID_MAX}"
            )
        if apid in seen_apids:
            raise MissionDatabaseError(
                f"container {name!r}: apid {apid} already used by {seen_apids[apid]!r}"
            )
        seen_apids[apid] = name

        fields = tuple(
            _resolve_field(raw_field, types, params, name)
            for raw_field in _require(spec, "fields", f"container {name!r}")
        )

        containers[name] = Container(
            name=name,
            apid=apid,
            rate_hz=float(spec.get("rate_hz", 0.0)),
            description=spec.get("description", ""),
            fields=fields,
        )
    return containers


def _resolve_field(
    raw_field: dict,
    types: dict[str, ParameterType],
    params: dict[str, dict],
    container_name: str,
) -> Field:
    """Resolve one container field (inline or parameter reference) to a Field."""
    if "parameter" in raw_field:
        param_name = raw_field["parameter"]
        if param_name not in params:
            raise MissionDatabaseError(
                f"container {container_name!r} references unknown parameter {param_name!r}"
            )
        param = params[param_name]
        return Field(
            name=param_name,
            type=types[param["type"]],
            parameter_name=param_name,
            description=param["description"],
        )

    # Inline field: defines its own name and type directly.
    field_name = _require(raw_field, "name", f"inline field in container {container_name!r}")
    type_name = _require(raw_field, "type", f"inline field {field_name!r} in {container_name!r}")
    if type_name not in types:
        raise MissionDatabaseError(
            f"inline field {field_name!r} in container {container_name!r} references unknown type {type_name!r}"
        )
    return Field(
        name=field_name,
        type=types[type_name],
        parameter_name=None,
        description=raw_field.get("description"),
    )


def _require(mapping: dict, key: str, where: str):
    if key not in mapping:
        raise MissionDatabaseError(f"{where}: missing required key {key!r}")
    return mapping[key]
