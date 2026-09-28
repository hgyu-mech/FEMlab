# Long-running computation: execution, persistence and monitoring

GitHub is the source/CI/results hub, not an unlimited always-on compute service.
A virtual environment isolates Python dependencies; it does not supply a machine.
A 140-day project is feasible on provisioned, funded resources, but not as one
uninterrupted GitHub-hosted Actions job. Long elapsed time alone is not useful
scientific evidence. Profile and validate a small case first.

## Current platform facts, checked 2026-09-28

GitHub documents a 6-hour hosted-job limit, a 5-day self-hosted-job limit and a
35-day workflow-run limit including waiting. Codespaces has an idle timeout,
default 30 minutes and configurable 5-240 minutes; active compute is billed.
An idle timeout is not the same as a hard maximum lifetime, but Codespaces is not
our recommended unattended production scheduler.

- https://docs.github.com/en/actions/reference/limits
- https://docs.github.com/en/codespaces/setting-your-user-preferences/setting-your-timeout-period-for-github-codespaces
- https://docs.github.com/en/actions/tutorials/store-and-share-data
- https://docs.github.com/en/actions/reference/security/secure-use
- https://slurm.schedmd.com/sbatch.html

Use artifacts to retain CI outputs beyond the temporary runner. This workflow sets
14-day retention; that is **not** a 140-day archive. Download/backup checkpoints to
persistent storage well before expiry. Cache is not the authoritative checkpoint.
Never chain disposable jobs merely to evade platform limits or run unrelated free
compute. Real long campaigns belong on an authorized workstation, VM or HPC queue.

## What now works

```text
GitHub code + reviewed config + bounded CI
                    |
        workstation / rented VM / HPC allocation
                    |
       numerical step -> diagnostics -> checkpoint
                    |
        progress.json + records + checkpoint.npz
                    |
   read-only local dashboard / permitted result uploads
```

The runner executes **one configured free-block reference MPM case**, not the thesis
teacher-label optimization or an autonomous AI researcher. The checkpoint contains
positions, velocities, mass, reference volume, deformation gradient, affine velocity,
step, config, source fingerprint, environment, initial diagnostics and RNG state.
A file-content digest detects corruption but is not a cryptographic signature from
a trusted party. Do not use checkpoints from untrusted sources.

A temporary file is flushed and atomically replaced on the same filesystem. An OS
lock prevents concurrent writers. A killed job resumes from its last saved accepted
state, possibly repeating work since that checkpoint. For power-loss/HPC filesystem
semantics, keep independent backups and test recovery on the actual filesystem;
this is not a distributed fault-tolerance guarantee.

Source or Python/NumPy changes cause an explicit refusal to resume. Keep a pinned
environment and the exact commit for long experiments. The independent replay test
establishes exact agreement in the tested environment only, not bitwise portability
across CPUs/BLAS versions. Configuration cannot be silently changed mid-trajectory.
Records beyond the checkpoint step after a crash are uncommitted; ignore them.

## Start and resume locally

From the repository checkout after `pip install -e ".[dev]"`:

```bash
python -m femlab.campaign --config configs/mpm_smoke.json --run-dir outputs/demo --chunk-steps 80 --max-seconds 60
python -m femlab.campaign --config configs/mpm_smoke.json --run-dir outputs/demo --chunk-steps 120 --max-seconds 60
```

The second process loads the checkpoint rather than restarting from zero. The
supplied example ends at 200 steps / 0.02 seconds of **physical simulation time**.
Its default cumulative measured-runtime budget is 600 seconds. It does not waste
140 days waiting after the numerical task has completed.

`progress.json` reports status, physical time, actual measured runtime, energy drift,
momentum and source/config. `records/` retains checkpoint metrics; checkpoint history
stores the last 1000 records and dashboard progress shows the last 200. Storage grows
with the number of saved records. Plan its quota and backup schedule.

Create an empty `STOP` file in the run directory for a graceful stop. Remove it to
resume. SIGINT/SIGTERM also request a checkpoint at the next safe step boundary.
A numerical failure preserves the previous accepted state, records the attempted
step/error and freezes that campaign. Investigate it instead of looping on the failure.
A single expensive step can overrun the between-step time check, so use a scheduler
hard deadline with a safety margin.

## Run in GitHub without keeping your own computer on

The `research-audit` workflow performs a small automatic demonstration on relevant
main-branch pushes. It runs independent audits and starts/resumes the MPM example
in separate Python processes. See the Actions job summary and downloadable
`research-campaign` and `research-audit-results` artifacts.

For a manual segment: Actions -> research-audit -> Run workflow. Leave
`resume_run_id` empty to start; `chunk_steps=100` pauses halfway through this example.
To continue in a later runner, supply the previous workflow **run ID** and the same
source/config. The workflow downloads its checkpoint artifact and advances another
bounded segment. It must still exist, and environment checks must pass. This manual
cross-run path is configured; see the recorded evidence for what was actually tested.
There is no scheduled 24/7 chain, paid VM provisioning or deployed public dashboard.

## Opt-in workstation/server and HPC

```bash
python ops/worker.py --config configs/mpm_smoke.json --run-dir outputs/server-run --max-hours 1
```

The supervisor advances bounded segments until the task finishes, a stop/failure
occurs, or a runtime/calendar limit is reached. The server must stay powered and
connected for access; turning off a separate client laptop does not stop the server.
It does not register a GitHub self-hosted runner or execute arbitrary pull requests.

For a genuinely long experiment, create a **new config and run directory** with a
justified target-step count, stable dt, explicit `max_compute_seconds` and
`max_calendar_days` (70 or 140 only when appropriate), and a matching supervisor
budget. These are ceilings, not estimates or a promise of useful convergence.
The process-runtime counter is not a cloud billing meter; idle/provisioned/queued
resources may cost more. Set provider/HPC quotas separately.

`ops/campaign.sbatch` is an opt-in 12-hour Slurm template that runs up to 11 hours
with a shutdown margin. Configure your own account/partition and Python environment.
Submit a new job to resume; no allocation or requeue is automatically submitted here.
A multi-month campaign can comprise legitimate checkpointed allocations, subject to
your cluster's queue policies. The numerical time steps are sequential; independent
cases/teacher candidates can be parallelized, not magically all time steps at once.

## View progress without exposing the server

The worker copies a read-only `index.html` into its run directory. In another server
terminal, serve **only that results directory**, bound to localhost:

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory outputs/server-run
```

From your client, use an authorized SSH tunnel (`ssh -L 8765:127.0.0.1:8765 user@server`)
and open `http://127.0.0.1:8765`. The dashboard polls every 5 seconds but does not
perform simulation. Do not expose Python's development file server to the Internet
or serve your home directory. GitHub Actions logs stream while a job is running;
artifacts and job summaries are snapshots, not this continuously refreshed server UI.

Before using a self-hosted runner on a public repository, read GitHub's security
guide. Untrusted pull requests must not be allowed to run on a machine containing
private research data, credentials or a commercial-license connection.
