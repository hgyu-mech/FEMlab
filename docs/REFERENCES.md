# Public references and implementation boundaries

These are conceptual references, not assertions of exact reproduction. No source
code, figures or private reports are copied into the package.

1. Jiang, C., Schroeder, C., Selle, A., Teran, J., Stomakhin, A. (2015).
   *The Affine Particle-In-Cell Method*. ACM Transactions on Graphics.
   DOI: 10.1145/2766996.
   https://disneyanimation.com/publications/the-affine-particle-in-cell-method/
   Relevant to affine particle-grid transfers in `mpm.py`.
2. Hu, Y. et al. (2018). *A Moving Least Squares Material Point Method with
   Displacement Discontinuity and Two-Way Rigid Body Coupling*.
   DOI: 10.1145/3197517.3201293.
   https://yuanming.taichi.graphics/publication/2018-mlsmpm/
   Future extension reference: the current solver is standard gradient MPM,
   not this MLS-MPM/CPIC implementation.
3. Sanchez-Gonzalez, A. et al. (2020). *Learning to Simulate Complex Physics with
   Graph Networks*. https://arxiv.org/abs/2002.09405
   Graph simulation research context; the small GNN here is not a reproduction.
4. Hu, Y. et al. (2019). *ChainQueen: A Real-Time Differentiable Physical Simulator
   for Soft Robotics*. https://arxiv.org/abs/1810.01054
   Future differentiable simulation/design context, not an implemented capability.
5. Sigmund, O. (2001). *A 99 line topology optimization code written in Matlab*.
   Structural and Multidisciplinary Optimization 21, 120-127.
   DOI: 10.1007/s001580050176.
   https://orbit.dtu.dk/en/publications/a-99-line-topology-optimization-code-written-in-matlab/
   SIMP research context. Our fixed-graph truss example is not this continuum code.
6. SciPy `minimize(method='SLSQP')` documentation.
   https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html
   The constrained optimizer is supplied by SciPy; truss mechanics and analytic
   density sensitivities are implemented here.
7. PyTorch `Tensor.index_add_` documentation.
   https://docs.pytorch.org/docs/stable/generated/torch.Tensor.index_add_.html
   The graph aggregation uses standard PyTorch operations and autograd.

Future EFG, SPH, finite-spheres, GIMP, CPDI, peridynamic and learned-quadrature
implementations must add exact formulation references and their own verification
cases before claiming those methods as implemented.
