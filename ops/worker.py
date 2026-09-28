"""Opt-in local/server supervisor. Does not provision resources or schedule jobs."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import time
from femlab.campaign import CampaignConfig, run_segment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', required=True)
    p.add_argument('--run-dir', required=True)
    p.add_argument('--max-hours', type=float, required=True)
    a = p.parse_args()
    if not 0 < a.max_hours <= 24*140:
        p.error('Explicit time budget must be between 0 and 3360 hours')
    config = CampaignConfig(**json.loads(Path(a.config).read_text(encoding='utf-8'))).validate()
    directory = Path(a.run_dir); directory.mkdir(parents=True, exist_ok=True)
    dashboard = Path(__file__).resolve().parents[1]/'web'/'campaign.html'
    shutil.copyfile(dashboard, directory/'index.html')
    stop = [False]
    def request_stop(signum, frame): stop[0] = True
    for s in (signal.SIGTERM, signal.SIGINT): signal.signal(s, request_stop)
    deadline = time.monotonic()+a.max_hours*3600
    while time.monotonic() < deadline and not stop[0]:
        report = run_segment(config, directory, chunk_steps=10000,
                             max_seconds=min(600., deadline-time.monotonic()),
                             should_stop=lambda: stop[0])
        print(json.dumps({key: report[key] for key in ('status', 'step', 'compute_seconds', 'error')}), flush=True)
        if report['status'] != 'paused':
            if report['status'] == 'failed': raise SystemExit(1)
            break


if __name__ == '__main__': main()
