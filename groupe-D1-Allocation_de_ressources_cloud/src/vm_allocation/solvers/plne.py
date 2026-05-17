from __future__ import annotations

from typing import Callable, List

import pulp

from vm_allocation.models import Context, Server, Solver, VM


RESOURCES = ("cpu", "ram", "storage", "bw")

# Mapping representing VM assignation to Server (1 if assigned)
AssignmentVars = dict[tuple[int, int], pulp.LpVariable]
# Mapping representing Server usage (1 if used)
ServerUsageVars = dict[int, pulp.LpVariable]
# Mapping  representing fragmentation (1 if server used and with space left)
FragmentationVars = dict[int, pulp.LpVariable]


class PLNESolver(Solver):
    """Solve VM allocation as an integer linear program with PuLP/CBC.

    Parameters
    ----------
    migration_weight : float, default=0
        Penalty applied when an existing VM is moved away from its current
        server.
    fragmentation_weight : float, default=0
        Penalty applied to active servers with at least one free resource.
    """

    def __init__(
        self,
        migration_weight: float = 0,
        fragmentation_weight: float = 0,
    ):
        self.migration_weight = migration_weight
        self.fragmentation_weight = fragmentation_weight

    def solve[ID_T](
        self, modifications: List[VM[ID_T]], context: Context[ID_T]
    ) -> Context[ID_T] | None:
        """Build and solve the ILP model.

        Parameters
        ----------
        modifications : List[VM]
            VMs to add or replace before solving. If a VM id already exists in
            the context, the VM from ``modifications`` replaces it.
        context : Context
            Current allocation context containing servers and already hosted
            VMs.

        Returns
        -------
        Context | None
            New allocation context if an optimal solution is found, otherwise
            ``None``.
        """
        servers = context.get_servers()
        vms = self._target_vms(modifications, context)
        if not servers and vms:
            return None

        problem = pulp.LpProblem("VM_Allocation_PLNE", pulp.LpMinimize)

        x = self._create_assignment_variables(vms, servers)
        y = self._create_server_usage_variables(servers)
        f = self._create_fragmentation_variables(servers)

        self._add_presence_constraints(problem, x, vms, servers)
        self._add_server_usage_constraints(problem, x, y, vms, servers)
        self._add_capacity_constraints(problem, x, y, vms, servers)
        self._add_affinity_constraints(problem, x, vms, servers)
        self._add_anti_affinity_constraints(problem, x, vms, servers)
        self._add_fragmentation_constraints(problem, x, y, f, vms, servers)

        problem += self._objective_expression(x, y, f, vms, servers, context)

        status = problem.solve(self._make_pulp_solver())
        if status != pulp.LpStatusOptimal:
            return None

        return self._build_solution_context(x, vms, servers)

    def _create_assignment_variables[ID_T](
        self, vms: list[VM[ID_T]], servers: list[Server[ID_T]]
    ) -> AssignmentVars:
        """Create VM-to-server assignment variables.

        Parameters
        ----------
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.

        Returns
        -------
        AssignmentVars
            Binary variables ``x[i, j]`` equal to 1 when VM ``i`` is assigned
            to server ``j``.
        """
        return {
            (i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary")
            for i in range(len(vms))
            for j in range(len(servers))
        }

    def _create_server_usage_variables[ID_T](
        self, servers: list[Server[ID_T]]
    ) -> ServerUsageVars:
        """Create server usage variables.

        Parameters
        ----------
        servers : list[Server]
            Candidate servers.

        Returns
        -------
        ServerUsageVars
            Binary variables ``y[j]`` equal to 1 when server ``j`` hosts at
            least one VM.
        """
        return {
            j: pulp.LpVariable(f"y_{j}", cat="Binary")
            for j in range(len(servers))
        }

    def _create_fragmentation_variables[ID_T](
        self, servers: list[Server[ID_T]]
    ) -> FragmentationVars:
        """Create server fragmentation variables.

        Parameters
        ----------
        servers : list[Server]
            Candidate servers.

        Returns
        -------
        FragmentationVars
            Binary variables ``f[j]`` equal to 1 when an active server has at
            least one free resource.
        """
        return {
            j: pulp.LpVariable(f"f_{j}", cat="Binary")
            for j in range(len(servers))
        }

    def _target_vms[ID_T](
        self, modifications: List[VM[ID_T]], context: Context[ID_T]
    ) -> list[VM[ID_T]]:
        """Return the VMs that must exist in the final allocation.

        Parameters
        ----------
        modifications : List[VM]
            VMs to add or replace.
        context : Context
            Current allocation context.

        Returns
        -------
        list[VM]
            Copied VMs from the context plus copied VMs from ``modifications``.
            New ids are appended, existing ids are replaced.
        """
        vms_by_id = {}
        ordered_ids = []

        for server in context.get_servers():
            for vm in server.vms:
                if vm.id not in vms_by_id:
                    ordered_ids.append(vm.id)
                vms_by_id[vm.id] = vm.copy()

        for vm in modifications:
            if vm.id not in vms_by_id:
                ordered_ids.append(vm.id)
            vms_by_id[vm.id] = vm.copy()

        return [vms_by_id[vm_id] for vm_id in ordered_ids]

    def _add_presence_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add constraints forcing every VM onto exactly one server.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.
        """
        number_of_servers = len(servers)

        for vm_index in range(len(vms)):
            possible_assignments = []

            for server_index in range(number_of_servers):
                assignment = x[(vm_index, server_index)]
                possible_assignments.append(assignment)

            vm_assignment_count = pulp.lpSum(possible_assignments)
            constraint_name = f"presence_vm_{vm_index}"

            problem += (vm_assignment_count == 1, constraint_name)

    def _add_server_usage_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        y: ServerUsageVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add constraints linking assignments to server usage.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        y : ServerUsageVars
            Server usage variables ``y[j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.

        Notes
        -----
        If ``x[i, j]`` is 1, then ``y[j]`` must also be 1. Since the objective
        minimizes the sum of ``y[j]``, unused servers naturally stay at 0.
        """
        number_of_vms = len(vms)
        number_of_servers = len(servers)

        for vm_index in range(number_of_vms):
            for server_index in range(number_of_servers):
                vm_assigned_to_server = x[(vm_index, server_index)]
                server_is_used = y[server_index]
                constraint_name = (
                    f"server_usage_vm_{vm_index}_server_{server_index}"
                )

                problem += (
                    vm_assigned_to_server <= server_is_used,
                    constraint_name,
                )

    def _add_capacity_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        y: ServerUsageVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add multi-resource capacity constraints.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        y : ServerUsageVars
            Server usage variables ``y[j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.
        """
        for server_index, server in enumerate(servers):
            server_capacities = server.capacities()

            for resource in RESOURCES:
                total_resource_usage = self._server_usage_expression(
                    x,
                    vms,
                    server_index,
                    resource,
                )
                server_capacity = server_capacities[resource]
                server_is_used = y[server_index]
                available_capacity = server_capacity * server_is_used
                constraint_name = f"capacity_{resource}_server_{server_index}"

                problem += (
                    total_resource_usage <= available_capacity,
                    constraint_name,
                )

    def _add_affinity_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add affinity constraints.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.

        Notes
        -----
        For every affinity pair and every server, both VMs must have the same
        assignment value.
        """
        affinity_pairs = self._vm_relation_pairs(vms, lambda vm: vm.affinity)
        number_of_servers = len(servers)

        for left_vm_index, right_vm_index in affinity_pairs:
            for server_index in range(number_of_servers):
                left_vm_assignment = x[(left_vm_index, server_index)]
                right_vm_assignment = x[(right_vm_index, server_index)]
                constraint_name = (
                    f"affinity_vm_{left_vm_index}_vm_{right_vm_index}"
                    f"_server_{server_index}"
                )

                problem += (
                    left_vm_assignment == right_vm_assignment,
                    constraint_name,
                )

    def _add_anti_affinity_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add anti-affinity constraints.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.

        Notes
        -----
        For every anti-affinity pair and every server, at most one of the two
        VMs can be assigned to that server.
        """
        anti_affinity_pairs = self._vm_relation_pairs(
            vms, lambda vm: vm.anti_affinity
        )
        number_of_servers = len(servers)

        for left_vm_index, right_vm_index in anti_affinity_pairs:
            for server_index in range(number_of_servers):
                left_vm_assignment = x[(left_vm_index, server_index)]
                right_vm_assignment = x[(right_vm_index, server_index)]
                assignment_count_on_server = (
                    left_vm_assignment + right_vm_assignment
                )
                constraint_name = (
                    f"anti_affinity_vm_{left_vm_index}_vm_{right_vm_index}"
                    f"_server_{server_index}"
                )

                problem += (
                    assignment_count_on_server <= 1,
                    constraint_name,
                )

    def _add_fragmentation_constraints[ID_T](
        self,
        problem: pulp.LpProblem,
        x: AssignmentVars,
        y: ServerUsageVars,
        f: FragmentationVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ):
        """Add constraints identifying active servers with free resources.

        Parameters
        ----------
        problem : pulp.LpProblem
            PuLP problem receiving the constraints.
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        y : ServerUsageVars
            Server usage variables ``y[j]``.
        f : FragmentationVars
            Fragmentation variables ``f[j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.

        Notes
        -----
        ``f[j]`` is forced to 1 when server ``j`` is active and has slack in at
        least one resource. Inactive servers are not counted as fragmented.
        """
        for server_index, server in enumerate(servers):
            server_capacities = server.capacities()
            server_is_used = y[server_index]
            server_is_fragmented = f[server_index]

            problem += (
                server_is_fragmented <= server_is_used,
                f"fragmentation_requires_usage_server_{server_index}",
            )

            for resource in RESOURCES:
                capacity = server_capacities[resource]
                if capacity <= 0:
                    continue

                used = self._server_usage_expression(
                    x,
                    vms,
                    server_index,
                    resource,
                )
                free_capacity = capacity * server_is_used - used

                problem += (
                    free_capacity <= capacity * server_is_fragmented,
                    f"fragmentation_{resource}_server_{server_index}",
                )

    def _vm_relation_pairs[ID_T](
        self, vms: list[VM[ID_T]], related_vm_ids: Callable[[VM[ID_T]], set]
    ) -> set[tuple[int, int]]:
        """Return unique VM index pairs for an affinity-like relation.

        Parameters
        ----------
        vms : list[VM]
            VMs to inspect.
        related_vm_ids : Callable[[VM], set]
            Function returning related VM ids for one VM.

        Returns
        -------
        set[tuple[int, int]]
            Unique pairs of VM indices involved in the relation.
        """
        vm_index = {vm.id: i for i, vm in enumerate(vms)}
        pairs = set()

        for vm in vms:
            for other_vm_id in related_vm_ids(vm):
                if other_vm_id not in vm_index:
                    continue
                pairs.add(
                    tuple(sorted((vm_index[vm.id], vm_index[other_vm_id])))
                )

        return pairs

    def _objective_expression[ID_T](
        self,
        x: AssignmentVars,
        y: ServerUsageVars,
        f: FragmentationVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
        context: Context[ID_T],
    ) -> pulp.LpAffineExpression:
        """Build the objective expression.

        Parameters
        ----------
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        y : ServerUsageVars
            Server usage variables ``y[j]``.
        f : FragmentationVars
            Fragmentation variables ``f[j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.
        context : Context
            Current allocation context.

        Returns
        -------
        pulp.LpAffineExpression
            Objective minimizing used servers plus optional soft penalties.
        """
        terms = [pulp.lpSum(y[j] for j in range(len(servers)))]

        if self.migration_weight:
            terms.append(
                self.migration_weight
                * self._migration_expression(x, vms, servers, context)
            )

        if self.fragmentation_weight:
            terms.append(
                self.fragmentation_weight * self._fragmentation_expression(f)
            )

        return pulp.lpSum(terms)

    def _migration_expression[ID_T](
        self,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
        context: Context[ID_T],
    ) -> pulp.LpAffineExpression:
        """Build the migration penalty expression.

        Parameters
        ----------
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs to place.
        servers : list[Server]
            Candidate servers.
        context : Context
            Current allocation context.

        Returns
        -------
        pulp.LpAffineExpression
            Sum of assignments moving existing VMs away from their current
            server.
        """
        current_assignment = self._current_assignment(context)
        server_index = {server.id: j for j, server in enumerate(servers)}
        terms = []

        for i, vm in enumerate(vms):
            current_server_id = current_assignment.get(vm.id)
            if current_server_id not in server_index:
                continue

            current_server_index = server_index[current_server_id]
            terms.extend(
                x[(i, j)]
                for j in range(len(servers))
                if j != current_server_index
            )

        return pulp.lpSum(terms)

    def _fragmentation_expression(
        self, f: FragmentationVars
    ) -> pulp.LpAffineExpression:
        """Build the fragmentation penalty expression.

        Parameters
        ----------
        f : FragmentationVars
            Fragmentation variables ``f[j]``.

        Returns
        -------
        pulp.LpAffineExpression
            Number of active servers with at least one free resource.
        """
        return pulp.lpSum(f[j] for j in f)

    def _server_usage_expression[ID_T](
        self,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        server_index: int,
        resource: str,
    ) -> pulp.LpAffineExpression:
        """Return total usage of one resource on one server.

        Parameters
        ----------
        x : AssignmentVars
            Assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs to place.
        server_index : int
            Index of the server whose usage is computed.
        resource : str
            Resource whose VM requirements must be summed.

        Returns
        -------
        pulp.LpAffineExpression
            Total symbolic usage of the selected resource on the selected
            server.
        """
        return pulp.lpSum(
            vm.requirements()[resource] * x[(i, server_index)]
            for i, vm in enumerate(vms)
        )

    def _make_pulp_solver(self) -> pulp.PULP_CBC_CMD:
        """Create the PuLP CBC solver.

        Returns
        -------
        pulp.PULP_CBC_CMD
            CBC solver instance with solver messages disabled.
        """
        return pulp.PULP_CBC_CMD(msg=False)

    def _current_assignment[ID_T](
        self, context: Context[ID_T]
    ) -> dict[ID_T, ID_T]:
        """Map each currently hosted VM id to its server id.

        Parameters
        ----------
        context : Context
            Current allocation context.

        Returns
        -------
        dict
            Mapping from VM ids to server ids.
        """
        assignment = {}
        for server in context.get_servers():
            for vm in server.vms:
                assignment[vm.id] = server.id
        return assignment

    def _build_solution_context[ID_T](
        self,
        x: AssignmentVars,
        vms: list[VM[ID_T]],
        servers: list[Server[ID_T]],
    ) -> Context[ID_T]:
        """Convert solved assignment variables into a concrete context.

        Parameters
        ----------
        x : AssignmentVars
            Solved assignment variables ``x[i, j]``.
        vms : list[VM]
            VMs placed by the model.
        servers : list[Server]
            Candidate servers used to preserve capacities and ids.

        Returns
        -------
        Context
            Allocation context built from the solved assignment values.
        """
        solution_servers = [
            Server(
                server.id,
                server.cpu_capacity,
                server.ram_capacity,
                server.storage_capacity,
                server.bw_capacity,
            )
            for server in servers
        ]

        for i, vm in enumerate(vms):
            for j, server in enumerate(solution_servers):
                if pulp.value(x[(i, j)]) > 0.5:
                    server.add_vm(vm.copy())
                    break

        return Context(solution_servers)
