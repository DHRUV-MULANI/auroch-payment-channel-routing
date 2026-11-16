#!/usr/bin/env python3
"""Run the full Auroch-paper-sized parameter grid using documented proxies.

The workload grid and primary metrics match the paper's reported setup, but the
Bitcoin amount trace and exact Spider/SpeedyMurmurs implementations are absent.
Accordingly the algorithms here are explicit, non-paper-faithful proxies and
the output must not be presented as an exact reproduction.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import random
import time
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


METHODS = {
    "Auroch-inspired multipath (3 candidates)": "auroch_proxy",
    "Modified Dijkstra (single feasible shortest path)": "dijkstra_proxy",
    "Spider-inspired probed multipath (4 edge-disjoint candidates)": "spider_proxy",
    "SpeedyMurmurs-inspired 3-landmark route": "speedymurmurs_proxy",
}
METRICS = [
    ("success_ratio", "Success ratio", "Fraction"),
    ("success_volume", "Success volume", "Fraction"),
    ("routing_cost", "Routing cost", "Fees / successful satoshi"),
    ("mean_hops", "Mean successful route length", "Hops"),
    ("mean_route_seconds", "Mean routing time", "Seconds per payment"),
    ("mean_paths", "Mean paths used per successful payment", "Paths"),
]


def loopless(path: list[str]) -> list[str]:
    stack: list[str] = []
    positions: dict[str, int] = {}
    for node in path:
        if node in positions:
            stack = stack[: positions[node] + 1]
            positions = {n: i for i, n in enumerate(stack)}
        else:
            positions[node] = len(stack)
            stack.append(node)
    return stack


def load_topology(path: Path, fee_seed: int):
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    graph.add_nodes_from(node["pub_key"] for node in data["nodes"])
    base_directional = defaultdict(int)
    for edge in data["edges"]:
        u, v = edge["node1_pub"], edge["node2_pub"]
        cap = int(edge["capacity"])
        if cap <= 0:
            continue
        # Parallel physical channels are aggregated for fast repeated runs.
        for a, b in ((u, v), (v, u)):
            base_directional[(a, b)] += cap // 2
    rng = random.Random(fee_seed)
    for (u, v), bal in base_directional.items():
        graph.add_edge(u, v, weight=1 + rng.randint(0, 10))
    largest = max(nx.weakly_connected_components(graph), key=len)
    graph = graph.subgraph(largest).copy()
    base_directional = {edge: value for edge, value in base_directional.items()
                        if edge[0] in largest and edge[1] in largest}
    return graph, list(largest), base_directional, len(data["nodes"]), len(data["edges"])


def precompute_routes(graph: nx.DiGraph, nodes: list[str], pair_count: int, seed: int, landmarks_count: int):
    rng = random.Random(seed)
    pairs = []
    seen = set()
    while len(pairs) < pair_count:
        s, d = rng.sample(nodes, 2)
        if (s, d) not in seen:
            seen.add((s, d))
            pairs.append((s, d))

    # High-degree landmarks act as fixed routing landmarks in the proxy.
    landmarks = sorted(nodes, key=lambda n: graph.degree(n), reverse=True)[:landmarks_count]
    trees = {lm: nx.single_source_dijkstra_path(graph, lm, weight="weight") for lm in landmarks}
    route_cache = {}
    for i, (source, target) in enumerate(pairs, 1):
        paths = []
        try:
            path_iter = nx.shortest_simple_paths(graph, source, target, weight="weight")
            paths = list(itertools.islice(path_iter, 20))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass
        disjoint, used_edges = [], set()
        for candidate in paths:
            edge_set = set(zip(candidate, candidate[1:]))
            if edge_set.isdisjoint(used_edges):
                disjoint.append(candidate)
                used_edges.update(edge_set)
            if len(disjoint) == 4:
                break
        landmark_paths = []
        for lm in landmarks:
            if source in trees[lm] and target in trees[lm]:
                path = loopless(list(reversed(trees[lm][source])) + trees[lm][target][1:])
                if len(path) > 1:
                    landmark_paths.append(path)
        landmark_paths.sort(key=lambda p: sum(graph[u][v]["weight"] for u, v in zip(p, p[1:])))
        route_cache[(source, target)] = {
            "shortest": paths[:1], "auroch": paths[:3], "spider": disjoint,
            "speedymurmurs": landmark_paths,
        }
        if i % 25 == 0:
            print(f"Precomputed route candidates for {i}/{pair_count} OD pairs", flush=True)
    return pairs, route_cache, landmarks


def route_fee(graph: nx.DiGraph, path: list[str], amount: int) -> int:
    # Paper's fee equation is base_fee + rate_fee * amount. We use a fixed,
    # seeded integer rate in [0,10] per directed hop and base fee 1 sat/hop.
    return sum(1 + (graph[u][v]["weight"] - 1) * amount for u, v in zip(path, path[1:]))


def route_one(method: str, graph: nx.DiGraph, balances: dict, cached: dict,
              source: str, target: str, amount: int):
    bundle = cached.get((source, target), {})
    if method == "dijkstra_proxy":
        candidates = bundle.get("shortest", [])
        if not candidates:
            return False, 0, 0, 0, 0
        path = candidates[0]
        if min((balances.get((u, v), 0) for u, v in zip(path, path[1:])), default=0) < amount:
            return False, 0, 0, 0, 0
        fee = route_fee(graph, path, amount)
        for u, v in zip(path, path[1:]):
            balances[(u, v)] -= amount
        return True, fee, len(path) - 1, 1, amount

    if method == "auroch_proxy":
        candidates, limit = bundle.get("auroch", []), 3
    elif method == "spider_proxy":
        candidates, limit = bundle.get("spider", []), 4
    else:
        # SpeedyMurmurs proxy uses the cheapest landmark-tree route that can
        # carry the entire payment; it does not implement the original embedding.
        candidates = bundle.get("speedymurmurs", [])
        for path in candidates:
            if min((balances.get((u, v), 0) for u, v in zip(path, path[1:])), default=0) >= amount:
                fee = route_fee(graph, path, amount)
                for u, v in zip(path, path[1:]):
                    balances[(u, v)] -= amount
                return True, fee, len(path) - 1, 1, amount
        return False, 0, 0, 0, 0

    allocations, reserved, left = [], defaultdict(int), amount
    for path in candidates[:limit]:
        available = min((balances.get((u, v), 0) - reserved[(u, v)]
                         for u, v in zip(path, path[1:])), default=0)
        take = min(left, max(0, available))
        if take:
            allocations.append((path, take))
            for u, v in zip(path, path[1:]):
                reserved[(u, v)] += take
            left -= take
        if left == 0:
            break
    if left:
        return False, 0, 0, 0, 0
    fee, weighted_hops = 0, 0
    for path, take in allocations:
        fee += route_fee(graph, path, take)
        weighted_hops += (len(path) - 1) * take
        for u, v in zip(path, path[1:]):
            balances[(u, v)] -= take
    return True, fee, round(weighted_hops / amount), len(allocations), amount


def simulate(method: str, graph: nx.DiGraph, base_balances: dict, cache: dict, workload: list):
    balances = dict(base_balances)
    successes = delivered = attempted_amount = fees = 0
    hops, paths_used, route_seconds = 0, 0, 0.0
    for source, target, amount in workload:
        attempted_amount += amount
        start = time.perf_counter()
        ok, fee, tx_hops, tx_paths, received = route_one(method, graph, balances, cache, source, target, amount)
        route_seconds += time.perf_counter() - start
        if ok:
            successes += 1
            delivered += received
            fees += fee
            hops += tx_hops
            paths_used += tx_paths
    count = len(workload)
    return {
        "attempted_payments": count,
        "successful_payments": successes,
        "attempted_sats": attempted_amount,
        "successful_sats": delivered,
        "total_fees_sats": fees,
        "success_ratio": successes / count if count else 0.0,
        "success_volume": delivered / attempted_amount if attempted_amount else 0.0,
        "routing_cost": fees / delivered if delivered else 0.0,
        "mean_hops": hops / successes if successes else 0.0,
        "mean_paths": paths_used / successes if successes else 0.0,
        "mean_route_seconds": route_seconds / count if count else 0.0,
        "elapsed_seconds": route_seconds,
    }


def write_csv(path: Path, rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def create_plots(averaged: list[dict], out: Path):
    plot_dir = out / "plots" / "comparison"
    plot_dir.mkdir(parents=True, exist_ok=True)
    for metric, title, ylabel in METRICS:
        fig, axes = plt.subplots(1, 3, figsize=(17, 5), sharey=False)
        for ax, scale in zip(axes, (30, 50, 70)):
            for label in METHODS:
                rows = sorted((r for r in averaged if r["protocol"] == label and r["capacity_scale"] == scale),
                              key=lambda r: r["transaction_count"])
                x = [r["transaction_count"] for r in rows]
                y = [r[metric] for r in rows]
                e = [r[f"{metric}_std"] for r in rows]
                ax.errorbar(x, y, yerr=e, marker="o", capsize=3, label=label)
            ax.set_title(f"Capacity ×{scale}")
            ax.set_xlabel("Transactions per run")
            ax.set_xticks([5000, 7000, 9000])
            ax.grid(alpha=0.25)
        axes[0].set_ylabel(ylabel)
        axes[-1].legend(fontsize=8, loc="best")
        fig.suptitle(f"Assumption-based protocol proxies: {title}\n20 runs per setting; not a faithful paper reproduction")
        fig.tight_layout()
        fig.savefig(plot_dir / f"{metric}.png", dpi=180)
        fig.savefig(plot_dir / f"{metric}.pdf")
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lngraph_2021_11_27__00_00.json"))
    parser.add_argument("--output", type=Path, default=Path("final_results"))
    parser.add_argument("--counts", type=int, nargs="+", default=[5000, 7000, 9000])
    parser.add_argument("--scales", type=int, nargs="+", default=[30, 50, 70])
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--od-pairs", type=int, default=128,
                        help="Sampled OD pair pool reused with replacement to keep full grid tractable.")
    parser.add_argument("--seed", type=int, default=20261116)
    args = parser.parse_args()
    out = args.output
    for sub in ("raw", "plots/comparison", "plots/topology", "docs"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    graph, nodes, base_balances, node_count, channel_count = load_topology(args.input, args.seed + 1)
    print(f"Loaded graph: {node_count} nodes, {channel_count} channels; LCC {len(nodes)} nodes", flush=True)
    print(f"Precomputing route candidates for {args.od_pairs} OD pairs", flush=True)
    pairs, cache, landmarks = precompute_routes(graph, nodes, args.od_pairs, args.seed + 2, 3)
    print(f"Route cache ready; landmarks={landmarks}", flush=True)

    raw_runs = []
    workload_rows = []
    work_by_run = {}
    for run in range(args.runs):
        seed = args.seed + run
        rng = random.Random(seed)
        workload = []
        for idx in range(max(args.counts)):
            source, target = pairs[rng.randrange(len(pairs))]
            # Trace is absent; use a reproducible log-uniform 1,000–1,000,000 sat workload.
            amount = int(round(10 ** rng.uniform(3, 6)))
            workload.append((source, target, amount))
            if run == 0:
                workload_rows.append({"seed": seed, "transaction_index": idx,
                                      "source": source, "destination": target,
                                      "amount_sats": amount})
        work_by_run[run] = workload

    # One simulation per protocol × setting × repetition. Every protocol shares
    # the exact workload and independently reset channel balances.
    total_configs = len(args.counts) * len(args.scales) * args.runs * len(METHODS)
    completed = 0
    for run in range(args.runs):
        for scale in args.scales:
            scaled_balances = {edge: amount * scale for edge, amount in base_balances.items()}
            for count in args.counts:
                workload = work_by_run[run][:count]
                for label, method in METHODS.items():
                    metrics = simulate(method, graph, scaled_balances, cache, workload)
                    raw_runs.append({
                        "protocol": label, "method": method, "transaction_count": count,
                        "capacity_scale": scale, "run": run + 1,
                        "seed": args.seed + run, **metrics,
                    })
                    completed += 1
                    if completed % 20 == 0 or completed == total_configs:
                        print(f"Completed {completed}/{total_configs} simulations", flush=True)
                # Persist checkpoint data so an interrupted long job leaves useful work.
                write_csv(out / "raw" / "per_run_checkpoint.csv", raw_runs)

    write_csv(out / "raw" / "per_run.csv", raw_runs)
    # Input workloads: all 9k requests for each run, then prefix subsets form 5k/7k settings.
    with (out / "raw" / "workload_manifest.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(workload_rows[0]))
        writer.writeheader()
        for run in range(args.runs):
            seed = args.seed + run
            for idx, (source, target, amount) in enumerate(work_by_run[run]):
                writer.writerow({"seed": seed, "transaction_index": idx,
                                 "source": source, "destination": target, "amount_sats": amount})

    averaged = []
    for (label, method, count, scale), group_iter in itertools.groupby(
            sorted(raw_runs, key=lambda r: (r["protocol"], r["transaction_count"], r["capacity_scale"])),
            key=lambda r: (r["protocol"], r["method"], r["transaction_count"], r["capacity_scale"])):
        group = list(group_iter)
        row = {"protocol": label, "method": method, "transaction_count": count,
               "capacity_scale": scale, "runs": len(group)}
        for metric, _, _ in METRICS:
            values = np.asarray([g[metric] for g in group], dtype=float)
            row[metric] = float(values.mean())
            row[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        averaged.append(row)
    write_csv(out / "raw" / "averaged.csv", averaged)
    create_plots(averaged, out)

    metadata = {
        "experiment": "full_parameter_grid_assumption_based_proxy_evaluation",
        "input_snapshot": str(args.input),
        "input_nodes": node_count, "input_channels": channel_count,
        "largest_component_nodes": len(nodes),
        "transaction_counts": args.counts, "capacity_scales": args.scales,
        "runs_per_configuration": args.runs,
        "configuration_count": len(args.counts) * len(args.scales),
        "simulations_including_protocols": total_configs,
        "total_attempts_per_protocol": sum(args.counts) * len(args.scales) * args.runs,
        "od_pair_pool": args.od_pairs,
        "seed": args.seed,
        "initial_liquidity": "50:50 directional balance assumption",
        "payment_amounts": "synthetic log-uniform 1,000 to 1,000,000 sat; Bitcoin trace unavailable",
        "source_destination": "random draws with replacement from a seeded pool of OD pairs in the largest component",
        "channel_policies": "ignored; current baseline implementations do not uniformly honor policy fields",
        "parallel_channels": "aggregated by directed endpoint pair for runtime tractability",
        "fee_model": "base fee 1 sat per hop plus seeded integer rate fee in [0,10] multiplied by amount, following the paper equation's form; units remain an interpretation assumption",
        "routing_time_scope": "mean route time includes cached path selection and allocation only; excludes one-time graph/path-cache construction",
        "protocol_definitions": {
            "Auroch-inspired multipath": "greedy capacity split across up to 3 cached low-weight simple paths; no auction/bidding/Eq.6 LP",
            "Modified Dijkstra": "single cached fee-weighted shortest path; fails if path bottleneck is insufficient",
            "Spider-inspired": "greedy capacity split across up to 4 cached edge-disjoint paths; probe-inspired proxy, not Spider implementation",
            "SpeedyMurmurs-inspired": "single route through one of 3 fixed high-degree landmark shortest-path trees; not the original embedding protocol",
        },
        "paper_faithful_reproduction": False,
        "elapsed_seconds": time.perf_counter() - started,
        "caveat": "Full parameter grid and 20 repetitions were run, but missing trace/protocol implementations require these results to be reported as assumption-based proxy evaluation, not as reproducing the paper's claims.",
    }
    (out / "raw" / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)
    print(f"Final outputs: {out.resolve()}", flush=True)


if __name__ == "__main__":
    main()
