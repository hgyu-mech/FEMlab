"""Neutral comparison boundary. No installed commercial solver is assumed."""
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import numpy as np
from .core import array


@dataclass(frozen=True)
class CaseMetadata:
    case_id: str
    solver: str
    solver_version: str
    units: str
    mesh_id: str
    load_case: str
    boundary_conditions: str
    material: str


class ExternalSolver(Protocol):
    def run(self, input_path: Path, work_directory: Path) -> Path: ...


class AbaqusAdapter:
    def run(self, input_path: Path, work_directory: Path) -> Path:
        raise NotImplementedError("Abaqus execution/ODB extraction requires a local licensed implementation")


class AnsysAdapter:
    def run(self, input_path: Path, work_directory: Path) -> Path:
        raise NotImplementedError("ANSYS execution/result extraction requires a local licensed implementation")


def write_nodal_csv(path, ids, displacement):
    ids, u = np.asarray(ids), array(displacement, 2)
    if (ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer)
            or len(ids) != len(u) or u.shape[1] not in (1, 2, 3)
            or len(np.unique(ids)) != len(ids)):
        raise ValueError("Invalid unique node IDs or displacement shape")
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["node_id", *[f"u{i}" for i in range(u.shape[1])]])
        writer.writerows([[int(i), *row] for i, row in zip(ids, u)])


def read_nodal_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f); header = next(reader, [])
        if header not in [["node_id", *[f"u{i}" for i in range(n)]] for n in (1, 2, 3)]:
            raise ValueError("Expected node_id,u0[,u1,u2] columns")
        rows = list(reader)
    if not rows or any(len(r) != len(header) for r in rows):
        raise ValueError("Empty or malformed nodal CSV")
    ids = np.array([int(r[0]) for r in rows], dtype=int)
    u = array([[float(v) for v in r[1:]] for r in rows], 2)
    if len(np.unique(ids)) != len(ids):
        raise ValueError("Duplicate node IDs")
    order = np.argsort(ids)
    return ids[order], u[order]


def compare_nodal_csv(reference, candidate, reference_meta: CaseMetadata, candidate_meta: CaseMetadata):
    for field in ("case_id", "units", "mesh_id", "load_case", "boundary_conditions", "material"):
        if not getattr(reference_meta, field) or getattr(reference_meta, field) != getattr(candidate_meta, field):
            raise ValueError(f"Comparison mismatch: {field}")
    a, u = read_nodal_csv(reference); b, v = read_nodal_csv(candidate)
    if not np.array_equal(a, b) or u.shape != v.shape:
        raise ValueError("Node ID or DOF mismatch; different meshes require explicit projection")
    error = float(np.linalg.norm(v-u)); scale = float(np.linalg.norm(u))
    return {"absolute_l2": error, "relative_l2": error/scale if scale > 0 else None,
            "max_abs": float(np.max(abs(v-u)))}
