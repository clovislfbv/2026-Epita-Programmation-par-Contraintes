"""Main package of the VM allocation optimization library.

To use this package, you can model your problem using the classes contained
in models, with notably your `Context` representing your infrastructure with
`Server`s with running `VM`s at a specific time. You would then provide a
`Solver` with a list of `VM` representing VM additions or modifications and the
context to find an optimal solution minimizing server usage.

One can find example of usage in the example notebooks.

========== ===========================================================
Subpackage Description
---------- -----------------------------------------------------------
datasets   Provides functions to generate VM allocation problems.
models     Provides models used to abstract the VM allocation problem.
solvers    Provides different solvers for the VM allocation problem.
========== ===========================================================
"""

__version__ = "1.0.0"
