"""Linear Newmark average-acceleration reference integrator on free DOFs."""
import numpy as np
from .core import array, positive, solve_static


def newmark(mass, damping, stiffness, force_history, dt, u0=None, v0=None):
    """beta=1/4, gamma=1/2. Caller must eliminate constrained DOFs first.

    Constant linear M,C,K; no nonlinear Newton iterations or moving constraints.
    Forces have shape (number_of_steps+1, ndof), including the initial force.
    """
    positive(dt=dt)
    m, c, k, f = array(mass, 2), array(damping, 2), array(stiffness, 2), array(force_history, 2)
    n = len(m)
    if n < 1 or any(a.shape != (n, n) for a in (m, c, k)) or f.shape[1] != n or len(f) < 2:
        raise ValueError("Invalid dynamic system shapes")
    for a in (m, c, k):
        if not np.allclose(a, a.T, rtol=1e-12, atol=1e-14):
            raise ValueError("Require symmetric linear matrices")
    if np.min(np.linalg.eigvalsh(m)) <= 0:
        raise ValueError("Mass matrix must be positive definite")
    for a in (c, k):
        eig = np.linalg.eigvalsh(a)
        if eig[0] < -1e-12*max(np.max(abs(eig)), 1e-30):
            raise ValueError("Stiffness/damping must be positive semidefinite")
    u = np.zeros_like(f); v = np.zeros_like(f); acceleration = np.zeros_like(f)
    if u0 is not None:
        value = array(u0, 1)
        if value.shape != (n,): raise ValueError("u0 shape mismatch")
        u[0] = value
    if v0 is not None:
        value = array(v0, 1)
        if value.shape != (n,): raise ValueError("v0 shape mismatch")
        v[0] = value
    acceleration[0] = np.linalg.solve(m, f[0]-c@v[0]-k@u[0])
    effective = m+.5*dt*c+.25*dt*dt*k
    for i in range(len(f)-1):
        up = u[i]+dt*v[i]+.25*dt*dt*acceleration[i]
        vp = v[i]+.5*dt*acceleration[i]
        acceleration[i+1] = solve_static(effective, f[i+1]-c@vp-k@up, {}).displacement
        u[i+1] = up+.25*dt*dt*acceleration[i+1]
        v[i+1] = vp+.5*dt*acceleration[i+1]
    return u, v, acceleration
