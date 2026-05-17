"""Provides models used to abstract the VM allocation problem.

======= =========================================================================
Classes Description
------- -------------------------------------------------------------------------
Context Datacenter context, containing populated servers with various capacities.
Server  Model representing a server with a capacity and running VMs.
Solver  Interface providing the template for VM allocation problem solvers.
VM      Model representing a VM with requirements.
======= =========================================================================
"""

from .context import Context
from .server import Server
from .solver import Solver
from .vm import VM

__all__ = ["Context", "Server", "Solver", "VM"]
