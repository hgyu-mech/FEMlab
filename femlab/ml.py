"""Small trainable baselines and physics acceptance gates, not pretrained solvers."""
from collections.abc import Mapping
import numpy as np
from numpy.typing import ArrayLike
from .core import array, partition, solve_static


class RidgeSurrogate:
    """Standardized multi-output ridge with an unpenalized intercept."""
    def __init__(self, regularization: float = 1e-8):
        if not np.isfinite(regularization) or regularization <= 0:
            raise ValueError("Regularization must be positive")
        self.regularization = regularization
        self.coef = None

    def fit(self, x: ArrayLike, y: ArrayLike):
        x, y = array(x, 2), array(y)
        if y.ndim not in (1, 2) or len(x) != len(y) or len(x) < 2 or x.shape[1] == 0:
            raise ValueError("Invalid training shapes")
        self.mean = x.mean(axis=0)
        self.scale = x.std(axis=0); self.scale[self.scale < 1e-12] = 1
        z = np.column_stack((np.ones(len(x)), (x-self.mean)/self.scale))
        penalty = self.regularization*np.eye(z.shape[1]); penalty[0, 0] = 0
        self.coef = np.linalg.solve(z.T@z+penalty, z.T@y)
        self.minimum, self.maximum = x.min(axis=0), x.max(axis=0)
        return self

    def predict(self, x: ArrayLike):
        if self.coef is None:
            raise RuntimeError("Fit before prediction")
        x = array(x, 2)
        if x.shape[1] != len(self.mean):
            raise ValueError("Feature count mismatch")
        return np.column_stack((np.ones(len(x)), (x-self.mean)/self.scale))@self.coef

    def in_training_box(self, x: ArrayLike):
        """Necessary domain screen only, not calibrated uncertainty or proof of safety."""
        self.predict(x)
        x = array(x, 2)
        return np.all((x >= self.minimum) & (x <= self.maximum), axis=1)


def group_split(groups: ArrayLike, test_fraction: float = .2, seed: int = 0):
    """Keep complete trajectories/geometries in one partition to avoid leakage."""
    g = np.asarray(groups)
    if g.ndim != 1 or not 0 < test_fraction < 1:
        raise ValueError("Invalid groups or fraction")
    unique = np.unique(g)
    if len(unique) < 2:
        raise ValueError("At least two independent groups are required")
    unique = np.random.default_rng(seed).permutation(unique)
    ntest = max(1, min(len(unique)-1, int(np.ceil(len(unique)*test_fraction))))
    mask = np.isin(g, unique[:ntest])
    return np.flatnonzero(~mask), np.flatnonzero(mask)


def guarded_static(k: ArrayLike, force: ArrayLike, prescribed: Mapping[int, float],
                   predicted: ArrayLike, *, in_domain: bool, rtol: float = 1e-6,
                   atol: float = 1e-10):
    """Accept BC-corrected ML output only inside domain and with a small free residual.

    Residual is not a displacement error certificate for ill-conditioned systems.
    The full fallback solve currently also validates the system; this prototype
    intentionally makes NO speedup claim. Later certification can be cached.
    """
    if not np.isfinite(rtol) or not np.isfinite(atol) or rtol < 0 or atol < 0:
        raise ValueError("Invalid tolerances")
    baseline = solve_static(k, force, prescribed)
    k, f = array(k, 2), array(force, 1)
    pred = np.asarray(predicted, dtype=float)
    if pred.shape != f.shape:
        raise ValueError("Prediction shape mismatch")
    if not in_domain or not np.all(np.isfinite(pred)):
        return baseline.displacement, False
    free, fixed, u = partition(len(f), prescribed)
    u[free] = pred[free]
    residual = k@u-f
    rhs = f[free]-k[np.ix_(free, fixed)]@u[fixed]
    accepted = bool(np.linalg.norm(residual[free]) <= atol+rtol*np.linalg.norm(rhs))
    return (u, True) if accepted else (baseline.displacement, False)


def bounded_transfer_prediction(model: RidgeSurrogate, features: ArrayLike,
                                fallback: float = .95):
    """Scalar global PIC/FLIP ratio proposal. No alpha/beta paper reproduction.

    Bounds and training-box membership alone do NOT ensure conservation or
    trajectory stability. Use a separate held-out rollout before deployment.
    """
    if not np.isfinite(fallback) or not 0 <= fallback <= 1:
        raise ValueError("Fallback must lie in [0,1]")
    features = array(features, 2)
    pred = np.asarray(model.predict(features)).reshape(-1)
    if len(pred) != len(features):
        raise ValueError("Transfer policy must have one scalar output per sample")
    valid = model.in_training_box(features) & np.isfinite(pred) & (pred >= 0) & (pred <= 1)
    return np.where(valid, pred, fallback), valid
