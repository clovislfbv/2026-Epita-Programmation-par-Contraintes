"""Provides the Server class."""

from __future__ import annotations

from typing import List, Mapping

import matplotlib.pyplot as plt

from .vm import VM


class Server[ID_T]:
    """Model representing a server with a capacity and running VMs.

    Attributes
    ----------
    server_id : ID_T
        The id of the server, supposed to be unique per server.
    cpu : int
        CPU capacity of the server.
    ram : int
        RAM capacity of the server.
    storage : int
        Storage capacity of the server.
    bw : int
        Bandwidth capacity of the server.
    cpu_usage : int
        Current usage of the CPU.
    ram_usage : int
        Current usage of the RAM.
    storage_usage : int
        Current usage of the storage.
    bw_usage : int
        Current usage of the bandwidth.
    vms : List[VM]
        Active VMs running on the server.
    """

    _RESOURCE_INFO = [
        ("cpu_usage", "cpu_capacity", "cpu", "CPU"),
        ("ram_usage", "ram_capacity", "ram", "RAM"),
        ("storage_usage", "storage_capacity", "storage", "Storage"),
        ("bw_usage", "bw_capacity", "bw", "BW"),
    ]

    def __init__(
        self, server_id: ID_T, cpu: int, ram: int, storage: int, bw: int
    ):

        self.id = server_id
        self.cpu_capacity = cpu
        self.ram_capacity = ram
        self.storage_capacity = storage
        self.bw_capacity = bw

        self.cpu_usage = 0
        self.ram_usage = 0
        self.storage_usage = 0
        self.bw_usage = 0

        self.vms: List[VM[ID_T]] = []

    def get_vms(self) -> List[VM[ID_T]]:
        return self.vms

    def remove_vm_by_id(self, vm_id: ID_T) -> bool:
        """Removes a running VM by id.

        Parameters
        ----------
        vm_id : UUID
            The id of the VM to remove.

        Returns
        -------
        bool
            True if removal successful, False otherwise.
        """
        removed = False

        new_vms = []
        for vm in self.vms:
            if vm.id == vm_id:
                self.cpu_usage -= vm.cpu
                self.ram_usage -= vm.ram
                self.storage_usage -= vm.storage
                self.bw_usage -= vm.bw
                removed = True
            else:
                new_vms.append(vm)

        self.vms = new_vms
        return removed

    def add_vm(self, vm: VM[ID_T]) -> bool:
        """Adds a running VM.

        Parameters
        ----------
        vm : VM
            The VM to add.

        Returns
        -------
        bool
            True if addition successful, False otherwise (in case of lack of
            capacity for example).
        """
        if any(existing_vm.id == vm.id for existing_vm in self.vms):
            return False
        if not self.can_host(vm):
            return False
        self.vms.append(vm)

        self.cpu_usage += vm.cpu
        self.ram_usage += vm.ram
        self.storage_usage += vm.storage
        self.bw_usage += vm.bw

        return True

    def can_host(self, vm: VM[ID_T]) -> bool:
        """Whether the server can host the given VM.

        Parameters
        ----------
        vm : VM
            The VM to check for.

        Returns
        -------
        bool
            True if possible, False otherwise.
        """

        if (
            self.cpu_usage + vm.cpu > self.cpu_capacity
            or self.ram_usage + vm.ram > self.ram_capacity
            or self.storage_usage + vm.storage > self.storage_capacity
            or self.bw_usage + vm.bw > self.bw_capacity
        ):
            return False

        for other_vm in self.vms:
            if other_vm.id in vm.anti_affinity:
                return False

        return True

    def capacities(self) -> dict[str, int]:
        """Return the server capacities by resource name.

        Returns
        -------
        dict[str, int]
            Mapping from resource names to server capacities.
        """
        return {
            "cpu": self.cpu_capacity,
            "ram": self.ram_capacity,
            "storage": self.storage_capacity,
            "bw": self.bw_capacity,
        }

    def copy(self) -> Server[ID_T]:
        """ "Creates a new server instance from this server.

        Returns
        -------
        Server
            The copied server.
        """
        c = Server(
            self.id,
            self.cpu_capacity,
            self.ram_capacity,
            self.storage_capacity,
            self.bw_capacity,
        )
        for vm in self.vms:
            c.add_vm(vm.copy())

        return c

    def draw(self, ax: plt.Axes, vm_colors: Mapping[ID_T, str]):
        """Draws the server representation on the given matplotlib axes.

        Parameters
        ----------
        ax : plt.Axes
            The Axes to draw on.
        vm_colors : Mapping[UUID, str]
            Color mapping for VMs.
        """
        for spine in ax.spines.values():
            spine.set_visible(False)

        n_res = len(self._RESOURCE_INFO)

        y_positions = list(range(n_res - 1, -1, -1))

        for i, (usage_attr, cap_attr, vm_attr, label) in enumerate(
            self._RESOURCE_INFO
        ):
            capacity = getattr(self, cap_attr)
            used = getattr(self, usage_attr)
            ratio = used / capacity if capacity else 0
            y = y_positions[i]

            ax.barh(
                y,
                100,
                color="#bbb",
                linewidth=0.5,
            )

            left = 0.0
            for vm in self.vms:
                vm_requirement = getattr(vm, vm_attr)
                percentage = (
                    (vm_requirement / capacity * 100) if capacity else 0
                )
                color = vm_colors.get(vm.id, "#aaa")
                ax.barh(
                    y,
                    percentage,
                    left=left,
                    color=color,
                    linewidth=0.6,
                )

                left += percentage

            ax.text(
                -2,
                y,
                label,
                ha="right",
                va="center",
            )

            ax.text(
                102,
                y,
                f"{ratio:.0%}",
                ha="left",
                va="center",
            )

        ax.set_xlim(-18, 116)
        ax.set_ylim(-0.7, n_res - 0.3)
        ax.set_yticks([])
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.tick_params(axis="x", length=0, pad=2)

        n_vms = len(self.vms)
        ax.set_title(
            f"Server  [{self.id}]\n{n_vms} VM{'s' if n_vms != 1 else ''}  active",
            pad=8,
            loc="left",
        )

    def __str__(self) -> str:
        def bar(used: int, cap: int, bar_width: int) -> str:
            ratio = used / cap if cap else 0
            n_fill = round(ratio * bar_width)
            filled = "█" * n_fill + "░" * (bar_width - n_fill)
            raw = f"{used}/{cap}".rjust(9)
            pct = f"({ratio:>4.0%})"
            return f"[{filled}]{raw}  {pct}"

        n_vms = len(self.vms)

        bar_width = min(
            64,
            max(
                self.cpu_capacity,
                self.ram_capacity,
                self.storage_capacity,
                self.bw_capacity,
            ),
        )

        start_line = f"Server [{self.id}] {'─' * 3} {n_vms} VM{'s ' if n_vms != 1 else ' '}"

        server_lines = [
            f"CPU     {bar(self.cpu_usage, self.cpu_capacity, bar_width)}",
            f"RAM     {bar(self.ram_usage, self.ram_capacity, bar_width)}",
            f"Storage {bar(self.storage_usage, self.storage_capacity, bar_width)}",
            f"BW      {bar(self.bw_usage, self.bw_capacity, bar_width)}",
        ]

        vm_lines = []
        if self.vms:
            server_lines.append("VMs:")
            for vm in self.vms:
                raw = f"  · {vm}"
                # Truncate if too long
                if len(raw) > 64:
                    raw = raw[:61] + "…"
                server_lines.append(raw)

        max_length = max(
            len(start_line),
            *[len(line) for line in server_lines],
            *[len(line) for line in vm_lines],
        )

        lines = ["┌─ " + start_line.ljust(max_length, "─") + "─┐"]
        for line in server_lines:
            lines.append("│  " + line.ljust(max_length, " ") + " │")
        for line in vm_lines:
            lines.append("│  " + line.ljust(max_length, " ") + " │")
        lines.append("└──" + "─" * max_length + "─┘")

        return "\n".join(lines)
