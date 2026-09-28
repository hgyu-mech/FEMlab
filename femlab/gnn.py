"""Optional PyTorch message-passing architecture. No trained checkpoint supplied.

Permutation equivariant, not guaranteed rotation equivariant or conservative.
Node/edge features must be nondimensionalized by the caller. Research scaffold.
"""
try:
    import torch
    from torch import nn
except ImportError as exc:
    raise ImportError('Install the optional ML extra: pip install -e ".[ml]"') from exc


class MechanicsGNN(nn.Module):
    def __init__(self, node_features: int, edge_features: int, output_features: int,
                 hidden: int = 32, steps: int = 3):
        super().__init__()
        if any(not isinstance(v, int) or v < 1 for v in
               (node_features, edge_features, output_features, hidden, steps)):
            raise ValueError("All dimensions and steps must be positive integers")
        self.encoder = nn.Linear(node_features, hidden)
        self.messages = nn.ModuleList([
            nn.Sequential(nn.Linear(2*hidden+edge_features, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
            for _ in range(steps)])
        self.updates = nn.ModuleList([
            nn.Sequential(nn.Linear(2*hidden, hidden), nn.SiLU(), nn.Linear(hidden, hidden))
            for _ in range(steps)])
        self.decoder = nn.Linear(hidden, output_features)

    def forward(self, nodes, edge_index, edges, fixed_mask=None, prescribed=None):
        if (nodes.ndim != 2 or edge_index.ndim != 2 or edge_index.shape[0] != 2
                or edge_index.dtype != torch.long or edges.ndim != 2
                or edges.shape[0] != edge_index.shape[1]):
            raise ValueError("Invalid graph shapes or edge dtype")
        if edge_index.numel() and (edge_index.min() < 0 or edge_index.max() >= len(nodes)):
            raise ValueError("Edge index out of bounds")
        src, dst = edge_index
        h = self.encoder(nodes)
        for message, update in zip(self.messages, self.updates):
            m = message(torch.cat((h[src], h[dst], edges), dim=-1))
            aggregate = torch.zeros_like(h).index_add(0, dst, m)
            h = h+update(torch.cat((h, aggregate), dim=-1))
        out = self.decoder(h)
        if fixed_mask is not None:
            if fixed_mask.dtype != torch.bool or fixed_mask.shape != out.shape:
                raise ValueError("fixed_mask must be bool with the full output shape")
            prescribed = torch.zeros_like(out) if prescribed is None else prescribed
            if prescribed.shape != out.shape:
                raise ValueError("Prescribed values must match the output shape")
            out = torch.where(fixed_mask, prescribed, out)
        return out
