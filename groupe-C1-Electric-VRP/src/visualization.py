from __future__ import annotations
from typing import List, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from .instance import EVRPInstance, DEPOT, CUSTOMER, STATION, DIST_SCALE
ROUTE_COLORS = plt.cm.tab10.colors

def plot_instance(instance: EVRPInstance, ax: Optional[plt.Axes]=None, title: str='') -> plt.Axes:
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 7))
    inst = instance
    xs = [c[0] for c in inst.coords]
    ys = [c[1] for c in inst.coords]
    ax.scatter(xs[0], ys[0], c='red', s=250, marker='s', zorder=5, label='Depot')
    ax.annotate('D', (xs[0], ys[0]), ha='center', va='center', fontsize=9, color='white', fontweight='bold')
    cx = [xs[i] for i in inst.customer_indices]
    cy = [ys[i] for i in inst.customer_indices]
    ax.scatter(cx, cy, c='steelblue', s=120, zorder=4, label=f'Customers ({inst.n_customers})')
    for i in inst.customer_indices:
        ax.annotate(str(i), (xs[i], ys[i]), textcoords='offset points', xytext=(5, 5), fontsize=7, color='steelblue')
    if inst.station_indices:
        sx = [xs[i] for i in inst.station_indices]
        sy = [ys[i] for i in inst.station_indices]
        ax.scatter(sx, sy, c='green', s=200, marker='^', zorder=4, label=f'Stations ({inst.n_stations})')
        for i in inst.station_indices:
            ax.annotate(f'S{i}', (xs[i], ys[i]), textcoords='offset points', xytext=(5, 5), fontsize=7, color='green')
    ax.set_title(title or f'EVRP instance — {inst.n_customers} customers, {inst.n_stations} stations')
    ax.set_xlabel('x (km)')
    ax.set_ylabel('y (km)')
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)
    return ax

def plot_routes(routes: List[List[int]], instance: EVRPInstance, ax: Optional[plt.Axes]=None, title: str='', total_dist_km: Optional[float]=None) -> plt.Axes:
    ax = plot_instance(instance, ax=ax)
    inst = instance
    xs = [c[0] for c in inst.coords]
    ys = [c[1] for c in inst.coords]
    legend_patches = []
    for k, route in enumerate(routes):
        if not route:
            continue
        color = ROUTE_COLORS[k % len(ROUTE_COLORS)]
        full_path = [0] + route + [0]
        px = [xs[i] for i in full_path]
        py = [ys[i] for i in full_path]
        ax.plot(px, py, color=color, linewidth=1.8, alpha=0.75, marker='o', markersize=4)
        load = sum((inst.demands[n] for n in route if inst.node_types[n] == CUSTOMER))
        legend_patches.append(mpatches.Patch(color=color, label=f'V{k}: {len([n for n in route if inst.node_types[n] == CUSTOMER])} cust, load={load}/{inst.vehicle_capacity}'))
    dist_str = f' — {total_dist_km:.1f} km' if total_dist_km is not None else ''
    ax.set_title(title + dist_str)
    ax.legend(handles=legend_patches, loc='upper right', fontsize=7)
    return ax

def plot_battery_profile(route: List[int], instance: EVRPInstance, vehicle_id: int=0, ax: Optional[plt.Axes]=None) -> plt.Axes:
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
    inst = instance
    from .instance import ENERGY_SCALE
    battery = inst.battery_capacity
    levels = [battery]
    labels = ['depot']
    full_path = [0] + route + [0]
    for idx in range(len(full_path) - 1):
        i, j = (full_path[idx], full_path[idx + 1])
        e = inst.energy(i, j, load=0)
        if inst.node_types[i] == STATION:
            battery = inst.battery_capacity
        battery = max(0, battery - e)
        levels.append(battery)
        if inst.node_types[j] == DEPOT:
            labels.append('depot')
        elif inst.node_types[j] == CUSTOMER:
            labels.append(f'C{j}')
        else:
            labels.append(f'S{j}')
    kWh_levels = [l / ENERGY_SCALE for l in levels]
    ax.plot(kWh_levels, marker='o', linewidth=2, color='darkorange')
    ax.fill_between(range(len(kWh_levels)), kWh_levels, alpha=0.2, color='orange')
    ax.axhline(inst.battery_capacity / ENERGY_SCALE, color='green', linestyle='--', label='Full battery')
    ax.axhline(0, color='red', linestyle='--', label='Empty battery')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylabel('Battery (kWh)')
    ax.set_title(f'Battery profile — Vehicle {vehicle_id}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax

def plot_comparison(labels: List[str], distances: List[float], times: List[float], ax: Optional[plt.Axes]=None) -> plt.Axes:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    colors = ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
    axes[0].bar(labels, distances, color=colors[:len(labels)])
    axes[0].set_ylabel('Total distance (km)')
    axes[0].set_title('Solution quality')
    axes[0].grid(True, axis='y', alpha=0.3)
    axes[1].bar(labels, times, color=colors[:len(labels)])
    axes[1].set_ylabel('Solve time (s)')
    axes[1].set_title('Computation time')
    axes[1].set_yscale('log')
    axes[1].grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    return axes
