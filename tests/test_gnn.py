import pytest
torch = pytest.importorskip("torch")
from femlab.gnn import MechanicsGNN


def graph():
    torch.manual_seed(3)
    nodes = torch.randn(4, 3)
    index = torch.tensor([[0, 1, 1, 2, 2, 3], [1, 0, 2, 1, 3, 2]])
    edges = torch.randn(6, 2)
    return nodes, index, edges


def test_gnn_permutation_equivariance_and_backward():
    nodes, index, edges = graph()
    model = MechanicsGNN(3, 2, 2)
    out = model(nodes, index, edges)
    permutation = torch.tensor([2, 0, 3, 1]); inverse = torch.argsort(permutation)
    reordered = model(nodes[permutation], inverse[index], edges)
    torch.testing.assert_close(reordered, out[permutation])
    out.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters())


def test_gnn_dirichlet_values():
    nodes, index, edges = graph(); model = MechanicsGNN(3, 2, 2)
    mask = torch.zeros((4, 2), dtype=torch.bool); mask[0] = True
    prescribed = torch.ones((4, 2))*3
    out = model(nodes, index, edges, mask, prescribed)
    torch.testing.assert_close(out[0], prescribed[0])


def test_gnn_can_optimize_a_toy_loss():
    nodes, index, edges = graph(); model = MechanicsGNN(3, 2, 1, hidden=8, steps=2)
    target = nodes[:, :1]*.25
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    initial = float((model(nodes, index, edges)-target).square().mean().detach())
    for _ in range(60):
        optimizer.zero_grad(); loss = (model(nodes, index, edges)-target).square().mean()
        loss.backward(); optimizer.step()
    assert float(loss.detach()) < initial*.1
