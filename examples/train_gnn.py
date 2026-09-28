"""Train a small GNN on FEM-generated static spring-chain responses.

Single geometry and material, held-out load amplitudes only. This proves the
training path runs, NOT generalization to new geometries or dynamic MPM states.
"""
import json
from pathlib import Path
import numpy as np
import torch
from femlab.core import add_element, solve_static
from femlab.fem import bar_stiffness
from femlab.gnn import MechanicsGNN


def dataset(loads):
    coordinates = np.linspace(0, 1, 4)
    k = np.zeros((4, 4))
    for i in range(3): add_element(k, [i, i+1], bar_stiffness(1, 1, 1/3))
    edge = np.array([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    nodes, indices, features, targets, masks = [], [], [], [], []
    for j, load in enumerate(loads):
        force = np.array([0., 0., 0., load])
        fixed = np.array([1., 0., 0., 0.])
        nodes.append(np.column_stack((coordinates, force, fixed)))
        indices.append(edge+4*j)
        features.append(np.column_stack((coordinates[edge[1]]-coordinates[edge[0]], np.full(6, 3.))))
        targets.append(solve_static(k, force, {0: 0}).displacement[:, None])
        masks.append(fixed.astype(bool)[:, None])
    return (torch.tensor(np.vstack(nodes), dtype=torch.float32),
            torch.tensor(np.hstack(indices), dtype=torch.long),
            torch.tensor(np.vstack(features), dtype=torch.float32),
            torch.tensor(np.vstack(targets), dtype=torch.float32),
            torch.tensor(np.vstack(masks), dtype=torch.bool))


def main():
    torch.manual_seed(42); torch.set_num_threads(1)
    train_loads = np.linspace(-1., 1., 15)
    test_loads = [-.73, -.31, .17, .59, .89]
    train, test = dataset(train_loads), dataset(test_loads)
    model = MechanicsGNN(3, 2, 1, hidden=32, steps=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=.003)
    for _ in range(500):
        optimizer.zero_grad()
        pred = model(train[0], train[1], train[2], train[4])
        loss = ((pred-train[3])[~train[4]]**2).mean()
        loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); optimizer.step()
    model.eval()
    with torch.no_grad():
        pred = model(test[0], test[1], test[2], test[4])
        relative = torch.linalg.vector_norm(pred-test[3])/torch.linalg.vector_norm(test[3])
    report = {"seed": 42, "steps": 500, "train_mse": float(loss.detach()),
              "heldout_load_relative_l2": float(relative), "test_loads": test_loads,
              "scope": "One 1D spring-chain geometry and material, load interpolation only.",
              "torch": torch.__version__, "device": "cpu", "pretrained_solver": False}
    path = Path("outputs/gnn_demo.json"); path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
