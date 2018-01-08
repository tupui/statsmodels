"""Latin Hypercube Sampling methods."""
from __future__ import division
import copy
import numpy as np
from scipy.optimize import brute
try:
    from scipy.optimize import basinhopping
    have_basinhopping = True
except ImportError:
    have_basinhopping = False
from statsmodels.tools.sequences import discrepancy


def orthogonal_latin_hypercube(dim, n_sample, bounds=None):
    """Orthogonal array-based Latin hypercube sampling (OA-LHS).

    On top of the constraints from the Latin Hypercube, an orthogonal array of
    size n_sample is defined and only one point is allowed per subspace.

    Parameters
    ----------
    dim : int
        Dimension of the parameter space.
    n_sample : int
        Number of samples to generate in the parametr space.
    bounds : tuple or array_like ([min, k_vars], [max, k_vars])
        Desired range of transformed data. The transformation apply the bounds
        on the sample and not the theoretical space, unit cube. Thus min and
        max values of the sample will coincide with the bounds.

    Returns
    -------
    sample : ndarray (n_samples, k_vars)
        Latin hypercube Sampling.

    References
    ----------
    [1] Art B. Owen, "Orthogonal arrays for computer experiments, integration
    and visualization", Statistica Sinica, 1992.

    """
    sample = []
    step = 1.0 / n_sample

    for i in range(dim):
        # Enforce a unique point per grid        
        j = np.arange(n_sample) * step
        temp = j + np.random.uniform(low=0, high=step, size= n_sample)
        np.random.shuffle(temp)

        sample.append(temp)

    sample = np.array(sample).T

    # Sample scaling from unit hypercube to feature range
    if bounds is not None:
        min_ = bounds.min(axis=0)
        max_ = bounds.max(axis=0)
        sample = sample * (max_ - min_) + min_

    return sample


def latin_hypercube(dim, n_sample, bounds=None, centered=False):
    """Latin hypercube sampling (LHS).

    The parameter space is subdivided into an orthogonal grid of n_sample per
    dimension. Within this multi-dimensional grid, n_sample are selected by
    ensuring there is only one sample per row and column.

    Parameters
    ----------
    dim : int
        Dimension of the parameter space.
    n_sample : int
        Number of samples to generate in the parametr space.
    bounds : tuple or array_like ([min, k_vars], [max, k_vars])
        Desired range of transformed data. The transformation apply the bounds
        on the sample and not the theoretical space, unit cube. Thus min and
        max values of the sample will coincide with the bounds.

    Returns
    -------
    sample : ndarray (n_samples, k_vars)
        Latin hypercube Sampling.

    References
    ----------
    [1] Mckay et al., "A Comparison of Three Methods for Selecting Values of
    Input Variables in the Analysis of Output from a Computer Code",
    Technometrics, 1979.

    """
    if centered:
        r = 0.5
    else:
        r = np.random.random_sample((n_sample, dim))

    q = np.random.random_integers(low=1, high=n_sample, size=(n_sample, dim))

    sample = 1. / n_sample * (q - r)

    # Sample scaling from unit hypercube to feature range
    if bounds is not None:
        min_ = bounds.min(axis=0)
        max_ = bounds.max(axis=0)
        sample = sample * (max_ - min_) + min_

    return sample


def optimal_design(dim, n_sample, bounds=None, start_design=None, niter=1,
                   force=False, optimization=True):
    """Optimal design.

    Optimize the design by doing random permutations to lower the centered
    discrepancy. If `optimization` is False, `niter` design are generated and
    the one with lowest centered discrepancy is return. This option is faster.

    Centered discrepancy based design show better space filling robustness
    toward 2D and 3D subprojections. Distance based design better space filling
    but less robust to subprojections.

    Parameters
    ----------
    dim : int
        Dimension of the parameter space.
    n_sample : int
        Number of samples to generate in the parametr space.
    bounds : tuple or array_like ([min, k_vars], [max, k_vars])
        Desired range of transformed data. The transformation apply the bounds
        on the sample and not the theoretical space, unit cube. Thus min and
        max values of the sample will coincide with the bounds.
    start_design : array_like (n_samples, k_vars)
        Initial design of experiment to optimize.
    niter : int
        Number of iteration to perform.
    force : bool
        If `optimization`, force *basinhopping* optimization. Otherwise
        grid search is used.
    optimization : bool
        Optimal design using global optimization or random generation of
        `niter` samples.
    Returns
    -------
    sample : array_like (n_samples, k_vars)
        Optimal Latin hypercube Sampling.

    References
    ----------
    [1] Damblin et al., "Numerical studies of space filling designs:
    optimization of Latin Hypercube Samples and subprojection properties",
    Journal of Simulation, 2013.

    """
    doe = start_design
    if (bounds is None) and (doe is not None):
            bounds = np.array([doe.min(axis=0), doe.max(axis=0)])
    if optimization:
        if doe is None:
            doe = orthogonal_latin_hypercube(dim, n_sample, bounds)

        def _perturb_doe(x, sample, bounds):
            """Perturb the Design of Experiment.

            Parameters
            ----------
            x : list of int
                It is a list of:
                    idx : int
                        Index value of the components to compute
            sample : array_like (n_samples, k_vars)
                Sample to perturb.
            bounds : tuple or array_like ([min, k_vars], [max, k_vars])
                Desired range of transformed data. The transformation apply the
                bounds on the sample and not the theoretical space, unit cube.
                Thus min and max values of the sample will coincide with the
                bounds.

            Returns
            -------
            discrepancy : float
                Centered discrepancy.

            """
            doe = copy.deepcopy(sample)
            col, row_1, row_2 = np.round(x).astype(int)
            doe[row_1, col], doe[row_2, col] = doe[row_2, col], doe[row_1, col]

            return discrepancy(doe, bounds)

        # Total number of possible design
        complexity = dim * n_sample ** 2

        if have_basinhopping and ((complexity > 1e6) or force):
            bounds_optim = ([0, dim - 1], [0, n_sample - 1], [0, n_sample - 1])
        else:
            bounds_optim = (slice(0, dim - 1, 1), slice(0, n_sample - 1, 1),
                            slice(0, n_sample - 1, 1))

        for n in range(niter):
            if have_basinhopping and ((complexity > 1e6) or force):
                minimizer_kwargs = {"method": "L-BFGS-B",
                                    "bounds": bounds_optim,
                                    "args": (doe, bounds)}
                optimum = basinhopping(_perturb_doe, [0, 0, 0], niter=100,
                                       minimizer_kwargs=minimizer_kwargs).x
            else:
                optimum = brute(_perturb_doe, ranges=bounds_optim,
                                finish=None, args=(doe, bounds))

            col, row_1, row_2 = np.round(optimum).astype(int)
            doe[row_1, col], doe[row_2, col] = doe[row_2, col], doe[row_1, col]
    else:
        best_disc = np.inf
        for n in range(niter):
            doe = orthogonal_latin_hypercube(dim, n_sample, bounds)
            disc = discrepancy(doe, bounds)
            if disc < best_disc:
                best_disc = disc
                best = doe

        doe = best

    return doe
