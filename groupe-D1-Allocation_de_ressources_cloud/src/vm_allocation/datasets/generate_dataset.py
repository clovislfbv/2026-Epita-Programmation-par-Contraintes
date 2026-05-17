"""Provides experiment generation functions for the VM allocation problem."""

import random
from typing import List

from vm_allocation.models import VM, Context, Server

from .utils import random_even, random_power_of_two

__all__ = ["generate_n_servers", "generate_n_vms_with_context", "generate_vm"]


def generate_n_servers(n: int) -> List[Server[int]]:
    """Generate a list of random servers.

    Each server is initialized with randomly generated
    resources:
    - CPU: powers of two between 32 and 128
    - RAM: even values between 64 and 256
    - Storage: between 500 and 2000
    - Bandwidth: between 200 and 2000

    Parameters
    ----------
    n : int
        Number of servers to generate.

    Returns
    -------
    List[Server[int]]
        A list containing `n` randomly generated servers with ids from 0 to n-1.
    """
    servers = []
    for i in range(n):
        server = Server(
            i,
            cpu=random_power_of_two(5, 7),  # 32 à 128
            ram=random_even(64, 256),
            storage=random.randint(500, 2000),
            bw=random.randint(200, 2000),
        )
        servers.append(server)
    return servers


def generate_n_vms_with_context(
    n: int,
    context: Context[int],
    affinity_chance: float = 0.1,
    anti_affinity_server_selection_chance: float = 0.1,
    anti_affinity_chance: float = 0.1,
    verbose: bool = False,
) -> tuple[list[VM[int]], Context[int]]:
    """Generate virtual machines and place them on servers.

    VMs are generated one by one and assigned to a random
    compatible server from the provided context.

    Affinity and anti-affinity relationships may also
    be randomly created between VMs.

    Parameters
    ----------
    n : int
        Number of VMs to generate.
    context : Context[int]
        Initial infrastructure context containing servers with integer ids.
    affinity_chance : float, optional
        Probability of creating an affinity relation between colocated VMs,
        by default 0.1.
    anti_affinity_server_selection_chance : float, optional
        Probability of selecting another server for anti-affinity generation,
        by default 0.1.
    anti_affinity_chance : float, optional
        Probability of creating an anti-affinity relation with a VM from
        another server, by default 0.1.
    verbose : bool, optional
        Enable debug prints, by default False.

    Returns
    -------
    tuple[list[VM[int]], Context[int]]:
        A tuple containing the generated VMs and the updated infrastructure context.
    """
    if verbose:
        print(f"Creating {n} VMs")
    servers = [server.copy() for server in context.get_servers()]
    nb_server = len(servers)
    if verbose:
        print(f"Server number : {nb_server}")
    all_vms = []

    for i in range(n):
        if verbose:
            print(f"Creating VM {i}")
        vm = generate_vm(i)

        accepting_server_idx = [
            i for i, server in enumerate(servers) if server.can_host(vm)
        ]

        if len(accepting_server_idx) == 0:
            if verbose:
                print("Could not insert it")
            # No place left
            break

        chosen_server_id = random.choice(accepting_server_idx)

        if verbose:
            print(f"Chosen server id : {chosen_server_id}")

        servers[chosen_server_id].add_vm(vm)

        # For all neighbors, affinity_chance to develop an affinity
        server = servers[chosen_server_id]
        list_vm = server.get_vms()

        for friend in list_vm:
            if friend.id != vm.id:
                if random.random() < affinity_chance:
                    print("Affinity added with vm :", friend.id)
                    vm.add_affinity(friend)

        for j in range(nb_server):
            if (
                j != chosen_server_id
                and random.random() < anti_affinity_server_selection_chance
            ):
                for not_friend in servers[j].get_vms():
                    if random.random() < anti_affinity_chance:
                        print("antiffinity added with vm :", not_friend.id)
                        vm.add_anti_affinity(not_friend)
                        not_friend.add_anti_affinity(vm)

        all_vms.append(vm)

    random.shuffle(all_vms)

    return all_vms, Context(servers)


def generate_vm[ID_T](i: ID_T) -> VM[ID_T]:
    """Generate a random valued VM with id i.

    The generated values follow the following generation:
    - CPU has 80% chance of being 2, 4 or 8 equiprobably, 20% of being 8 or 16.
    - RAM random even number between 2 and 32
    - Storage random number between 10 and 200
    - Bandwidth random number between 1 and 100

    Parameters
    ----------
    i : ID_T
        The id to use for the generated VM.

    Returns
    -------
    VM[ID_T]
        Generated VM.
    """

    if random.random() < 0.8:
        cpu = random_power_of_two(1, 3)  # 2,4,8
    else:
        cpu = random_power_of_two(3, 4)  # 8,16

    res = VM(
        i,
        cpu=cpu,
        ram=random_even(2, 32),
        storage=random.randint(10, 200),
        bw=random.randint(1, 100),
    )
    return res
