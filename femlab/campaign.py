"""Bounded, checkpointable 2D MPM reference runs on a workstation, CI or HPC.

No background cloud service is created. Every invocation has an explicit step
and wall-time cap. A single writer owns each run directory. Resumption requires
identical scientific config, source fingerprint and Python/NumPy environment.
"""
import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import signal
import time
import numpy as np
from .mpm import MPM2D, Particles


@dataclass(frozen=True)
class CampaignConfig:
    target_steps: int = 200
    dt: float = 0.0001
    cells: int = 24
    particles_per_axis: int = 5
    young: float = 1000.
    poisson: float = .2
    density: float = 1000.
    transfer: str = "apic"
    flip_ratio: float = .95
    initial_strain: float = .02
    seed: int = 7
    checkpoint_every: int = 25
    max_compute_seconds: float = 600.
    max_calendar_days: float = 7.
    max_relative_energy_drift: float = 1.

    def validate(self):
        for name in ("target_steps", "cells", "particles_per_axis", "checkpoint_every", "seed"):
            v = getattr(self, name)
            if type(v) is not int or v < (0 if name == "seed" else 1):
                raise ValueError(f"Invalid integer: {name}")
        if self.cells < 8 or self.particles_per_axis < 2:
            raise ValueError("Grid/particle resolution is too small")
        for name in ("dt", "young", "density", "max_compute_seconds", "max_calendar_days",
                     "max_relative_energy_drift"):
            v = getattr(self, name)
            if not np.isfinite(v) or v <= 0:
                raise ValueError(f"Invalid positive parameter: {name}")
        if not np.isfinite(self.initial_strain) or not 0 < self.initial_strain <= .1:
            raise ValueError("Require a nonzero small initial deformation in (0,0.1]")
        MPM2D(cells=self.cells, dx=1/self.cells, young=self.young, poisson=self.poisson,
              transfer=self.transfer, flip_ratio=self.flip_ratio)
        return self


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fingerprint():
    root = Path(__file__).parent
    return hashlib.sha256(b"".join(
        name.encode()+b"\0"+(root/name).read_bytes()
        for name in ("core.py", "mpm.py", "campaign.py"))).hexdigest()


def environment():
    return {"python": platform.python_version(), "numpy": np.__version__}


def atomic_bytes(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+f".tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as out:
            out.write(payload); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists(): temporary.unlink()


def atomic_json(path, value):
    atomic_bytes(path, (json.dumps(value, indent=2, allow_nan=False)+"\n").encode())


@contextmanager
def run_lock(directory):
    """OS advisory lock; a crash releases it without a stale lock-directory trap."""
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    handle = (path/"writer.lock").open("a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0); handle.write(b"0"); handle.flush(); handle.seek(0)
            try: msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc: raise RuntimeError("Run directory already has a writer") from exc
        else:
            import fcntl
            try: fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc: raise RuntimeError("Run directory already has a writer") from exc
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == "nt":
                import msvcrt
                handle.seek(0); msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def initial_state(config):
    n = config.particles_per_axis
    axis = .4+(np.arange(n)+.5)*.2/n
    xx, yy = np.meshgrid(axis, axis)
    reference = np.column_stack((xx.ravel(), yy.ravel()))
    f = np.diag([1+config.initial_strain, 1/(1+config.initial_strain)])
    x = (reference-.5)@f.T+.5
    # The perturbation is deterministic and RNG state is checkpointed for extensions.
    rng = np.random.default_rng(config.seed)
    v = rng.normal(0., .0001, size=x.shape); v -= v.mean(axis=0)
    vol = (.2/n)**2
    particles = Particles.create(x, v, config.density*vol, vol)
    particles.deformation[:] = f
    return particles, rng


def diagnostics(solver, particles):
    d = solver.diagnostics(particles)
    # Pointwise continuum energy; APIC affine energy is disclosed separately.
    d["continuum_energy"] = d["translational_kinetic"]+d["strain_energy"]
    d["energy_with_affine"] = d["continuum_energy"]+d["affine_kinetic"]
    x, v, m = particles.x, particles.v, particles.mass
    angular = float(m @ (x[:, 0]*v[:, 1]-x[:, 1]*v[:, 0]))
    if solver.transfer == "apic":
        angular += float(solver.dx**2/4 * (m @ (particles.affine[:, 1, 0]-particles.affine[:, 0, 1])))
    d["angular_with_affine"] = angular
    return d


def state_digest(arrays, metadata):
    h = hashlib.sha256(canonical(metadata).encode())
    for name in sorted(arrays):
        a = np.ascontiguousarray(arrays[name])
        h.update(name.encode()); h.update(str(a.dtype).encode())
        h.update(str(a.shape).encode()); h.update(a.tobytes())
    return h.hexdigest()


def save_checkpoint(directory, particles, metadata):
    names = ("x", "v", "mass", "volume0", "deformation", "affine")
    arrays = {name: np.asarray(getattr(particles, name)) for name in names}
    envelope = {"metadata": metadata, "sha256": state_digest(arrays, metadata)}
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays, envelope=np.array(canonical(envelope)))
    atomic_bytes(Path(directory)/"checkpoint.npz", buffer.getvalue())


def load_checkpoint(directory, config):
    with np.load(Path(directory)/"checkpoint.npz", allow_pickle=False) as z:
        envelope = json.loads(str(z["envelope"]))
        meta = envelope["metadata"]
        names = ("x", "v", "mass", "volume0", "deformation", "affine")
        arrays = {name: z[name].copy() for name in names}
    if state_digest(arrays, meta) != envelope["sha256"]:
        raise ValueError("Checkpoint integrity check failed")
    if meta.get("schema") != 1 or meta["config"] != asdict(config):
        raise ValueError("Checkpoint/config mismatch; use a new run directory")
    if meta["source_fingerprint"] != fingerprint() or meta["environment"] != environment():
        raise ValueError("Source/environment mismatch; do not silently continue a different experiment")
    p = Particles(*(arrays[name] for name in names))
    n = config.particles_per_axis**2
    shapes = ((n, 2), (n, 2), (n,), (n,), (n, 2, 2), (n, 2, 2))
    if any(arrays[name].shape != shape or not np.all(np.isfinite(arrays[name]))
           for name, shape in zip(names, shapes)) or np.any(p.mass <= 0) or np.any(p.volume0 <= 0):
        raise ValueError("Invalid checkpoint state")
    if not 0 <= meta["step"] <= config.target_steps:
        raise ValueError("Invalid checkpoint step")
    return p, meta


def run_segment(config, directory, *, chunk_steps=100, max_seconds=60., should_stop=lambda: False):
    """Advance at most chunk_steps and max_seconds, saving only accepted states.

    Time cap is checked BETWEEN solver steps. A single step may exceed it; use an
    external scheduler hard limit with a grace period. Budgets count measured
    process runtime, not provider billing/idle/queue time. Only one CPU case runs.
    """
    config.validate()
    if type(chunk_steps) is not int or chunk_steps < 1 or not np.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Positive finite invocation budgets are required")
    directory = Path(directory)
    with run_lock(directory):
        solver = MPM2D(cells=config.cells, dx=1/config.cells, young=config.young,
                       poisson=config.poisson, transfer=config.transfer, flip_ratio=config.flip_ratio)
        if (directory/"checkpoint.npz").exists():
            p, meta = load_checkpoint(directory, config)
            if meta.get("status") == "failed":
                raise ValueError("Failed campaign is frozen; investigate and create a new run")
            rng = np.random.default_rng(); rng.bit_generator.state = meta["rng_state"]
        else:
            p, rng = initial_state(config)
            meta = {"schema": 1, "config": asdict(config), "step": 0, "compute_seconds": 0.,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(), "history": [],
                    "source_fingerprint": fingerprint(), "environment": environment(),
                    "initial": diagnostics(solver, p), "rng_state": rng.bit_generator.state}
            atomic_json(directory/"config.json", asdict(config))
        start = time.perf_counter(); previous_seconds = meta["compute_seconds"]
        initial_step = meta["step"]; target = min(config.target_steps, initial_step+chunk_steps)
        initial = meta["initial"]; energy_scale = max(abs(initial["continuum_energy"]), 1e-20)
        status, error = "paused", None
        terminal = False

        def record(current_status):
            d = diagnostics(solver, p)
            d.update(step=meta["step"], simulation_time=meta["step"]*config.dt,
                     relative_energy_drift=(d["continuum_energy"]-initial["continuum_energy"])/energy_scale,
                     linear_momentum_drift=float(np.linalg.norm(np.asarray(d["momentum"])-initial["momentum"])))
            if not meta["history"] or meta["history"][-1]["step"] != meta["step"]:
                meta["history"].append(d)
            meta["history"] = meta["history"][-1000:]
            meta.update(status=current_status, error=error,
                        compute_seconds=previous_seconds+time.perf_counter()-start,
                        updated_at_utc=datetime.now(timezone.utc).isoformat(), rng_state=rng.bit_generator.state)
            save_checkpoint(directory, p, meta)
            atomic_json(directory/"records"/f'{meta["step"]:012d}.json', d)
            progress = {**meta, "latest": d, "history": meta["history"][-200:],
                        "fraction_complete": meta["step"]/config.target_steps,
                        "scope": "Experimental free-block MPM; not thesis reproduction or ML-MPM"}
            atomic_json(directory/"progress.json", progress)
            return progress

        record("running")
        while meta["step"] < target:
            runtime = previous_seconds+time.perf_counter()-start
            age = (datetime.now(timezone.utc)-datetime.fromisoformat(meta["created_at_utc"])).total_seconds()
            if should_stop() or (directory/"STOP").exists(): status="stopped"; break
            if runtime >= config.max_compute_seconds: status="budget_exhausted"; break
            if age >= config.max_calendar_days*86400: status="deadline_reached"; break
            if time.perf_counter()-start >= max_seconds: break
            try:
                candidate = solver.step(p, config.dt)
                d = diagnostics(solver, candidate)
                drift = (d["continuum_energy"]-initial["continuum_energy"])/energy_scale
                if abs(drift) > config.max_relative_energy_drift:
                    raise FloatingPointError(f"Full-step energy gate failed: signed relative drift {drift:.6g}")
            except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                status, error = "failed", f"Attempted step {meta['step']+1}: {type(exc).__name__}: {exc}"
                terminal = True; break
            p = candidate; meta["step"] += 1
            if meta["step"] % config.checkpoint_every == 0:
                summary = record("running")
                print(f"step={meta['step']} time={summary['latest']['simulation_time']:.6g} "
                      f"energy_drift={summary['latest']['relative_energy_drift']:.6g}", flush=True)
        if meta["step"] == config.target_steps and not terminal: status="completed"
        progress = record(status)
        # Checkpoint records are authoritative only up to the saved step.
        return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--chunk-steps", type=int, default=100)
    parser.add_argument("--max-seconds", type=float, default=60.)
    args = parser.parse_args()
    config = CampaignConfig(**json.loads(Path(args.config).read_text(encoding="utf-8")))
    stop = [False]
    def interrupt(signum, frame): stop[0] = True
    for sig in (signal.SIGINT, signal.SIGTERM): signal.signal(sig, interrupt)
    report = run_segment(config, args.run_dir, chunk_steps=args.chunk_steps,
                         max_seconds=args.max_seconds, should_stop=lambda: stop[0])
    print(json.dumps({key: report[key] for key in ("status", "step", "compute_seconds", "error")}, indent=2))
    if report["status"] == "failed": raise SystemExit(1)


if __name__ == "__main__": main()
