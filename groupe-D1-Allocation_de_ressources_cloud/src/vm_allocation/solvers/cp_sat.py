"""Provides the CPSATSolver class."""

import math

from fractions import Fraction
from typing import List

from ortools.sat.python import cp_model

from vm_allocation.models import VM, Context, Server, Solver


class CPSATSolver(Solver):
    """CP-SAT Solver for the VM allocation problem.

    Attributes
    ----------
    migration_weight : float
        Weight applied to hot swap penalty.
    fragmentation_weight : float
        Weight applied to fragmentation penalty.
    """

    def __init__(
        self,
        server_usage_weight: int = 10,
        migration_weight: float = 0.5,
        fragmentation_weight: float = 0.5,
        nb_search_workers: int = 8,
        max_time_in_seconds: float = 10.0,
        linearization_level: int = 2,
        log_search_progress: bool = False,
    ):
        self.server_usage_weight = server_usage_weight
        self.migration_weight = migration_weight
        self.fragmentation_weight = fragmentation_weight

        m_f = Fraction(migration_weight).limit_denominator(1000)
        f_f = Fraction(fragmentation_weight).limit_denominator(1000)
        self.scale = math.lcm(m_f.denominator, f_f.denominator)

        self.nb_search_workers = nb_search_workers
        self.max_time_in_seconds = max_time_in_seconds
        self.linearization_level = linearization_level
        self.log_search_progress = log_search_progress

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

        vms: dict[ID_T, VM] = {vm.id: vm for vm in modifications}
        servers: dict[ID_T, Server] = {}
        old_vm_tuples = []
        for server in context.get_servers():
            servers[server.id] = server
            id_set = set()
            for vm in server.vms:
                id_set.add(vm.id)
                old_vm_tuples.append((vm.id, server.id))
                if vm.id not in vms:
                    vms[vm.id] = vm

        model = cp_model.CpModel()

        # VM allocation
        x: dict[tuple[ID_T, ID_T], cp_model.IntVar] = {
            (vm_id, server_id): model.new_bool_var(f"x_{vm_id}_{server_id}")
            for vm_id in vms
            for server_id in servers
        }

        # Server activity
        y: dict[ID_T, cp_model.IntVar] = {
            server_id: model.new_bool_var(f"y_{server_id}")
            for server_id in servers
        }
        for server_id in servers:
            model.add_max_equality(
                y[server_id], [x[(vm_id, server_id)] for vm_id in vms.keys()]
            )

        # Unity
        for vm_id in vms:
            model.add_exactly_one(
                x[(vm_id, server_id)] for server_id in servers
            )

        # Capacity
        for server_id, server in servers.items():
            # CPU, RAM, Storage, Bandwidth
            model.add(
                sum(vm.cpu * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                <= server.cpu_capacity
            ).OnlyEnforceIf(y[server_id])
            model.add(
                sum(vm.ram * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                <= server.ram_capacity
            ).OnlyEnforceIf(y[server_id])
            model.add(
                sum(
                    vm.storage * x[(vm_id, server_id)]
                    for vm_id, vm in vms.items()
                )
                <= server.storage_capacity
            ).OnlyEnforceIf(y[server_id])
            model.add(
                sum(vm.bw * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                <= server.bw_capacity
            ).OnlyEnforceIf(y[server_id])

        # Affinity / Anti-affinity
        def create_affinity_set(
            vm: VM[ID_T], affinity_set: set[ID_T] | None = None
        ) -> set[ID_T]:
            new_set = affinity_set or set()
            for affinity in vm.affinity:
                if affinity not in new_set:
                    new_set.add(affinity)
                    create_affinity_set(vms[affinity], new_set)
            return new_set

        affinity_relations: set[tuple[ID_T, ID_T]] = set()
        anti_affinity_relations: set[tuple[ID_T, ID_T]] = set()
        for vm_id, vm in vms.items():
            affinities = create_affinity_set(vm)
            for other_vm in affinities:
                # We check if the inverse isn't already in effect
                # a = b is equivalent to b = a, same goes for addition
                if (
                    other_vm != vm_id
                    and other_vm in vms
                    and (vm_id, other_vm) not in affinity_relations
                    and (other_vm, vm_id) not in affinity_relations
                ):
                    for server_id in servers.keys():
                        model.add(
                            x[(vm_id, server_id)] == x[(other_vm, server_id)]
                        )
                    affinity_relations.add((vm_id, other_vm))

            for other_vm in vm.anti_affinity:
                if (
                    other_vm != vm_id
                    and other_vm in vms
                    and (vm_id, other_vm) not in anti_affinity_relations
                    and (other_vm, vm_id) not in anti_affinity_relations
                ):
                    for server_id in servers.keys():
                        model.add_at_most_one(
                            [x[(vm_id, server_id)], x[(other_vm, server_id)]]
                        )
                    anti_affinity_relations.add((vm_id, other_vm))

        # Dynamic consolidation
        d_list: list[cp_model.IntVar] = []
        for vm_id, server_id in old_vm_tuples:
            d_list.append(x[(vm_id, server_id)])

        # Fragmentation
        f_list: list[cp_model.IntVar] = []
        for server_id, server in servers.items():
            f = model.new_bool_var(f"f_{server_id}")
            f_list.append(f)
            model.add(f <= y[server_id])
            model.add(
                sum(vm.cpu * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                >= server.cpu_capacity * y[server_id]
            ).OnlyEnforceIf(f.Not())
            model.add(
                sum(vm.ram * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                >= server.ram_capacity * y[server_id]
            ).OnlyEnforceIf(f.Not())
            model.add(
                sum(
                    vm.storage * x[(vm_id, server_id)]
                    for vm_id, vm in vms.items()
                )
                >= server.storage_capacity * y[server_id]
            ).OnlyEnforceIf(f.Not())
            model.add(
                sum(vm.bw * x[(vm_id, server_id)] for vm_id, vm in vms.items())
                >= server.bw_capacity * y[server_id]
            ).OnlyEnforceIf(f.Not())

        # Objective
        # We scale up for integer manipulation
        model.minimize(
            self.server_usage_weight
            * self.scale
            * sum(y[server_id] for server_id in servers)
            - int(self.scale * self.migration_weight) * sum(d for d in d_list)
            + int(self.scale * self.fragmentation_weight)
            * sum(f for f in f_list)
        )

        # Solving
        solver = cp_model.CpSolver()
        solver.parameters.num_search_workers = self.nb_search_workers
        solver.parameters.max_time_in_seconds = self.max_time_in_seconds
        solver.parameters.linearization_level = self.linearization_level
        solver.parameters.log_search_progress = self.log_search_progress
        status = solver.solve(model)

        # Impossible case
        if status != cp_model.OPTIMAL and status != cp_model.FEASIBLE:
            return None

        # Context creation
        server_list = []
        for server_id, server in servers.items():
            new_server = Server(
                server_id,
                server.cpu_capacity,
                server.ram_capacity,
                server.storage_capacity,
                server.bw_capacity,
            )
            for vm_id, vm in vms.items():
                if solver.Value(x[(vm_id, server_id)]) == 1:
                    new_server.add_vm(vm.copy())
            server_list.append(new_server)

        return Context(server_list)
