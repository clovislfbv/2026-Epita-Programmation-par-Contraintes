"""Provides the Context class."""

from __future__ import annotations

from typing import List

import matplotlib.pyplot as plt
import matplotlib.patches as patches

from .server import Server


class Context[ID_T]:
    """Datacenter context, containing populated servers with various capacities.

    Attributes
    ----------
    servers : List[Server] | None, optional
        List of servers to populate the context with at setup, by default None.
    """

    _VM_PALETTE = [
        "#4C72B0",
        "#DD8452",
        "#55A868",
        "#C44E52",
        "#8172B3",
        "#937860",
        "#DA8BC3",
        "#8C8C8C",
        "#CCB974",
        "#64B5CD",
    ]

    def __init__(self, servers: List[Server[ID_T]] | None = None):
        self.servers: dict[ID_T, Server] = {}
        if servers is not None:
            for server in servers:
                self.add_server(server)

    def add_server(self, server: Server[ID_T]) -> bool:
        """Adds a server to the context.

        Parameters
        ----------
        server : Server
            The server to add.

        Returns
        -------
        bool
            True if addition was successful, False otherwise (already present).
        """
        if server.id in self.servers.keys():
            return False
        self.servers[server.id] = server
        return True

    def remove_server(self, server_id: ID_T) -> bool:
        """Removes a server from the context by id.

        Parameters
        ----------
        server_id : ID_T
            The id of the server to remove.

        Returns
        -------
        bool:
            True if removal successful, False otherwise.
        """
        if server_id not in self.servers.keys():
            return False
        self.servers.pop(server_id)
        return True

    def get_server(self, server_id: ID_T) -> Server[ID_T]:
        """Gets a specific server object from the context.

        Parameters
        ----------
        server_id : ID_T
            The id of the server to get.

        Returns
        -------
        Server
            The fetched server.

        Raises
        ------
        KeyError
            The server id didn't exist.
        """
        return self.servers[server_id]

    def get_servers(self) -> List[Server[ID_T]]:
        """Gets a list of all servers.

        Returns
        -------
        List[Server]
            The list of all the servers.
        """
        return list(server for server in self.servers.values())

    def copy(self) -> Context[ID_T]:
        """Creates a new context instance from this context.

        Returns
        -------
        Context
            The copied context.
        """
        return Context([server.copy() for server in self.get_servers()])

    def plot(
        self,
        title: str = "Datacenter - Resource allocation",
        figsize: tuple | None = None,
        max_cols: int = 3,
    ) -> plt.Figure | None:
        """Matplotlib visualization.

        Parameters
        ----------
        title : str, optional
            Title of the figure.
        figsize : tuple | None, optional
            Matplotlib figure's figsize.
        max_cols : int, optional
            Maximum number of columns in grid layout.

        Returns
        -------
        matplotlib.figure.Figure
        """
        n = len(self.servers)
        if n == 0:
            return None

        # Colors
        all_vm_ids: list = []
        for s in self.servers.values():
            for vm in s.vms:
                if vm.id not in all_vm_ids:
                    all_vm_ids.append(vm.id)
        vm_colors = {
            vid: self._VM_PALETTE[i % len(self._VM_PALETTE)]
            for i, vid in enumerate(all_vm_ids)
        }

        # Grid layout
        cols = min(n, max_cols)
        rows = (n + cols - 1) // cols

        if figsize is None:
            figsize = (cols * 6, rows * 4 + 1)

        fig, axes_grid = plt.subplots(
            rows, cols, figsize=figsize, squeeze=False
        )
        fig.suptitle(title, fontweight="bold")

        # Server plotting

        for idx, server in zip(range(rows * cols), self.servers.values()):
            row, col = divmod(idx, cols)
            ax = axes_grid[row][col]

            server.draw(ax, vm_colors)

        # Legend

        if all_vm_ids:
            handles = [
                patches.Patch(
                    color=vm_colors[vid],
                    label=f"VM {vid}",
                )
                for vid in all_vm_ids
            ]
            fig.legend(
                handles=handles,
                loc="lower center",
                ncol=min(len(handles), 5),
                title="VMs",
            )

        fig.tight_layout(pad=2)

        plt.close(fig)
        return fig

    def __str__(self) -> str:
        total_vms = sum(len(s.vms) for s in self.servers.values())
        n_srv = len(self.servers)

        header = (
            f"===== Context - {n_srv} server{'s' if n_srv != 1 else ''}"
            f", {total_vms} VM{'s' if total_vms != 1 else ''} total ====="
        )
        lines = [header, ""]
        for srv in self.servers.values():
            lines.append(str(srv))
            lines.append("")
        lines.append(len(header) * "=")
        return "\n".join(lines)
