"""Provides the FFDSolver class."""

from typing import List

from vm_allocation.models import VM, Context, Server, Solver


class FFDSolver(Solver):
    """First Fit Decreasing solver.

    We sort VMs by decreasing order, then we place each of them in the first
    server that can hold them.

    For affinity constraints, we group the VMs that should be together and we
    place them all at once.

    Attributes
    ----------
    verbose : bool, optional
        Should the model print debug messages, by default False.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

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

        if self.verbose:
            print("\n===== FFD CLEAN SOLVER =====")

        context = context.copy()
        servers = context.get_servers()

        # 1. Remove old versions of modified VMs
        modified_ids = {vm.id for vm in modifications}

        for server in servers:
            server.vms = [vm for vm in server.vms if vm.id not in modified_ids]

            # Reset server usage
            server.cpu_usage = sum(vm.cpu for vm in server.vms)
            server.ram_usage = sum(vm.ram for vm in server.vms)
            server.storage_usage = sum(vm.storage for vm in server.vms)
            server.bw_usage = sum(vm.bw for vm in server.vms)

        # 2. Rebuild full VM list
        all_vms = []
        for server in servers:
            all_vms.extend(server.vms)

        all_vms.extend(modifications)

        if self.verbose:
            print(f"[DEBUG] total VMs = {len(all_vms)}")

        # 3. Build groups (affinity safe)
        groups = self._build_affinity_groups(all_vms)

        groups.sort(
            key=lambda g: sum(vm.total_requirement() for vm in g), reverse=True
        )

        # 4. Clear servers from displaced VMs
        for server in servers:
            server.vms.clear()
            server.cpu_usage = 0
            server.ram_usage = 0
            server.storage_usage = 0
            server.bw_usage = 0

        # 5. Place groups
        for group in groups:
            placed = False

            for server in servers:
                if self._can_place_group(server, group):
                    for vm in group:
                        if not server.add_vm(vm):
                            return None
                    placed = True
                    break

            if not placed:
                if self.verbose:
                    print("[FAIL] cannot place group")
                return None

        return context

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_affinity_groups[ID_T](
        self, vms: List[VM[ID_T]]
    ) -> List[List[VM[ID_T]]]:
        """Groups VMs by affinity using union-find method.

        Each group should be placed as a whole on one server.

        Parameters
        ----------
        vms : List[VM]
            VMs to group.

        Returns
        -------
        List[List[VM]]
            List of VM groups.
        """
        vm_by_id = {vm.id: vm for vm in vms}
        parent = {vm.id: vm.id for vm in vms}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # path compression
                x = parent[x]
            return x

        def union(x, y):
            parent[find(x)] = find(y)

        for vm in vms:
            for affinity_id in vm.affinity:
                if affinity_id in vm_by_id:
                    union(vm.id, affinity_id)

        # Regroup by root
        groups: dict = {}
        for vm in vms:
            root = find(vm.id)
            groups.setdefault(root, []).append(vm)

        return list(groups.values())

    def _place_group[ID_T](
        self, group: List[VM[ID_T]], servers: List[Server]
    ) -> bool:
        """Attempts placing a group on the first accepting server.

        Parameters
        ----------
        group : List[VM]
            Group of VMs with common affinity.
        servers : List[Server]
            List of candidate servers to insert into.

        Returns
        -------
        bool
            True if the insertion was successful, False otherwise.
        """
        for server in servers:
            if self._can_place_group(server, group):
                for vm in group:
                    if not server.add_vm(vm):
                        return False
                return True

        return False

    def _can_place_group[ID_T](
        self, server: Server, group: List[VM[ID_T]]
    ) -> bool:
        """Checks whether the whole group can be placed on the server.

        Parameters
        ----------
        server : Server
            The server to insert the group into.
        group : List[VM]
            The group of VMs to insert.

        Returns
        -------
        bool
            True if the insertion is possible, False otherwise.
        """
        cpu_usage = server.cpu_usage
        ram_usage = server.ram_usage
        storage_usage = server.storage_usage
        bw_usage = server.bw_usage

        for vm in group:
            if any(existing_vm.id == vm.id for existing_vm in server.vms):
                return False

            for existing_vm in server.vms:
                if (
                    existing_vm.id in vm.anti_affinity
                    or vm.id in existing_vm.anti_affinity
                ):
                    return False

            for other_vm in group:
                if other_vm.id == vm.id:
                    continue
                if (
                    other_vm.id in vm.anti_affinity
                    or vm.id in other_vm.anti_affinity
                ):
                    return False

            cpu_usage += vm.cpu
            ram_usage += vm.ram
            storage_usage += vm.storage
            bw_usage += vm.bw

        return (
            cpu_usage <= server.cpu_capacity
            and ram_usage <= server.ram_capacity
            and storage_usage <= server.storage_capacity
            and bw_usage <= server.bw_capacity
        )
