"""Run a stress-free interior block and export particle positions/velocities."""
import json
from pathlib import Path
import numpy as np
from femlab.mpm import MPM2D, Particles


def main():
    x, y = np.meshgrid(np.linspace(.4, .5, 5), np.linspace(.4, .5, 5))
    points = np.column_stack((x.ravel(), y.ravel()))
    p = Particles.create(points, [.1, 0], .001, .0001)
    solver = MPM2D(); history = []
    for step in range(21):
        history.append({"step": step, "time": step*1e-4, **solver.diagnostics(p)})
        if step < 20: p = solver.step(p, 1e-4)
    path = Path("outputs"); path.mkdir(exist_ok=True)
    np.savetxt(path/"mpm_particles.csv", np.column_stack((p.x, p.v)), delimiter=",",
               header="x,y,vx,vy", comments="")
    (path/"mpm_diagnostics.json").write_text(json.dumps(history, indent=2)+"\n", encoding="utf-8")
    print("Saved outputs/mpm_particles.csv and outputs/mpm_diagnostics.json")


if __name__ == "__main__": main()
