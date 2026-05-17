"""Provides different solvers for the VM allocation problem.

=========== ===============================================================
Solver      Description
----------- ---------------------------------------------------------------
CPSATSolver CP-SAT Solver for the VM allocation problem.
FFDSolver   Solve VM allocation as an integer linear program with PuLP/CBC.
PLNESolver  First Fit Decreasing solver.
=========== ===============================================================
"""

from .cp_sat import CPSATSolver
from .ffd import FFDSolver
from .plne import PLNESolver

__all__ = ["CPSATSolver", "FFDSolver", "PLNESolver"]
