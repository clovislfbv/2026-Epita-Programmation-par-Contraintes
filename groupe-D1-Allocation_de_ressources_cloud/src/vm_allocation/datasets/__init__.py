"""Provides functions to generate VM allocation problems.

=========================== ====================================================
Functions                   Description
--------------------------- ----------------------------------------------------
generate_n_servers          Generate a list of random servers.
generate_n_vms_with_context Generate virtual machines and place them on servers.
generate_vm                 Generate a random valued VM with id i.
=========================== ====================================================
"""

from .generate_dataset import (
    generate_n_servers,
    generate_n_vms_with_context,
    generate_vm,
)

__all__ = [
    "generate_n_servers",
    "generate_n_vms_with_context",
    "generate_vm",
]
