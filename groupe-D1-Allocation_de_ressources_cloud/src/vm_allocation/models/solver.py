"""Provides the Solver interface."""

from abc import ABC, abstractmethod
from typing import List

from .context import Context
from .vm import VM


class Solver(ABC):
    """Interface providing the template for VM allocation problem solvers."""

    @abstractmethod
    def solve[ID_T](
        self, modifications: List[VM[ID_T]], context: Context[ID_T]
    ) -> Context[ID_T] | None:
        """Returns the solution to a vm allocation problem.

        Parameters
        ----------
        modifications : List[VM]
            The list of added or modified VMs configurations.
        context : Context
            The context with the servers, their allocated VMs.

        Returns
        -------
        Context | None
            A new context to accommodate for the changes, None if impossible.
        """
        ...
