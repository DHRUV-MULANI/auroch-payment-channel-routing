#!/usr/bin/env python3
"""Run an explicitly exploratory multi-payment routing pilot.

This is a scalable workload harness, not a faithful implementation of Auroch,
Spider, or SpeedyMurmurs. It compares a greedy multipath proxy with single-path
fee-weighted Dijkstra over a 50:50-liquidity graph. It intentionally labels all
outputs as proxies until paper data and protocol implementations are supplied.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def load_graph(path: Path, scale: int, fee_seed: int) -> tuple[nx.DiGraph, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.DiGraph()
    graph.add_nodes_from(n["pub_key"] for n in data["nodes"])
    for row in data["edges"]:
        u, v = row["node1_pub"], row["node2_pub"]
        cap = int(row["capacity"]) * scale
        if cap <= 0:
            continue
        for a, b in ((u, v), (v, u)):
            if graph.has_edge(a, b):
                graph[a][b]["balance"] += cap // 2
                graph[a][b]["capacity"] += cap
            else:
                graph.add_edge(a, b, balance=cap // 2, capacity=cap)
    # Reproducible illustrative per-hop forwarding fee, in satoshis.
    fee_rng = random.Random(fee_seed)
    for _, _, attrs in graph.edges(data=True):
        attrs["fee"] = 1 + fee_rng.randint(0, 10)
    largest = max(nx.weakly_connected_components(graph), key=len)
    return graph, list(largest)


def path_capacity(graph: nx.DiGraph, path: list[str]) -> int:
    return min((graph[u][v]["balance"] for u, v in zip(path, path[1:])), default=0)


def candidate_paths(graph: nx.DiGraph, source: str, target: str, limit: int):
    try:
        gen = nx.shortest_simple_paths(graph, source, target, weight="fee")
        for _, path in zip(range(limit), gen):
            yield path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return


def route_payment(graph: nx.DiGraph, source: str, target: str, amount: int, method: str):
    if method == "dijkstra_proxy":
        try:
            path = nx.shortest_path(graph, source, target, weight="fee")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return False, 0, 0, 0
        if path_capacity(graph, path) < amount:
            return False, 0, 0, len(path) - 1
        for u, v in zip(path, path[1:]):
            graph[u][v]["balance"] -= amount
        fee = sum(graph[u][v]["fee"] for u, v in zip(path, path[1:]))
        return True, amount, fee, len(path) - 1

    # Auroch-like greedy multipath proxy: inspect up to three low-fee paths and
    # split over their current bottleneck balances. No auction/LP protocol.
    left, paths_used, total_fee, total_hops = amount, [], 0, 0
    reserved: dict[tuple[str, str], int] = {}
    for path in candidate_paths(graph, source, target, limit=3):
        available = min((graph[u][v]["balance"] - reserved.get((u, v), 0)
                         for u, v in zip(path, path[1:])), default=0)
        allocation = min(left, available)
        if allocation <= 0:
            continue
        paths_used.append((path, allocation))
        for u, v in zip(path, path[1:]):
            reserved[(u, v)] = reserved.get((u, v), 0) + allocation
        hops = len(path) - 1
        total_fee += allocation * sum(graph[u][v]["fee"] for u, v in zip(path, path[1:]))
        total_hops += allocation * hops
        left -= allocation
        if left == 0:
            break
    if left:
        return False, 0, 0, 0
    for path, allocation in paths_used:
        for u, v in zip(path, path[1:]):
            graph[u][v]["balance"] -= allocation
    mean_hops = round(total_hops / amount)
    return True, amount, total_fee / amount, mean_hops


def run_one(graph: nx.DiGraph, nodes: list[str], workload: list[tuple[str, str, int]], method: str):
    rows = []
    for tx_index, (source, target, amount) in enumerate(workload):
        started = time.perf_counter()
        success, delivered, fee_per_sat, hops = route_payment(graph, source, target, amount, method)
        elapsed = time.perf_counter() - started
        fee = delivered * fee_per_sat if success else 0
        rows.append({
            "transaction": tx_index, "source": source, "destination": target,
            "attempted_sats": amount, "success": int(success),
            "delivered_sats": delivered, "fee_sats": fee,
            "hops": hops, "routing_seconds": elapsed,
        })
    attempted = sum(r["attempted_sats"] for r in rows)
    delivered = sum(r["delivered_sats"] for r in rows)
    successful = [r for r in rows if r["success"]]
    total_fee = sum(r["fee_sats"] for r in rows)
    return rows, {
        "success_ratio": len(successful) / len(rows) if rows else 0,
        "success_volume": delivered / attempted if attempted else 0,
        "routing_cost": total_fee / delivered if delivered else 0,
        "mean_hops": float(np.mean([r["hops"] for r in successful])) if successful else 0,
        "mean_route_seconds": float(np.mean([r["routing_seconds"] for r in rows])) if rows else 0,
        "liquidity_utilization": delivered / max(attempted, 1),
        "attempted_sats": attempted,
        "delivered_sats": delivered,
        "total_fee_sats": total_fee,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("lngraph_2021_11_27__00_00.json"))
    parser.add_argument("--transactions", type=int, default=50, help="Pilot workload per run; default 50 (paper uses 5000/7000/9000).")
    parser.add_argument("--runs", type=int, default=3, help="Pilot repetitions; default 3 (paper uses 20).")
    parser.add_argument("--scales", type=int, nargs="+", default=[30, 50, 70])
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--output", type=Path, default=Path("results/quick_pilot"))
    args = parser.parse_args()
    if args.transactions < 1 or args.runs < 1 or any(s < 1 for s in args.scales):
        parser.error("transactions, runs, and capacity scales must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    raw_rows, per_tx_rows = [], []
    methods = [("Auroch-like multipath proxy", "multipath_proxy"), ("Fee-weighted Dijkstra proxy", "dijkstra_proxy")]
    start_all = time.perf_counter()

    for scale in args.scales:
        for repetition in range(args.runs):
            seed = args.seed + repetition
            graph, nodes = load_graph(args.input, scale, fee_seed=args.seed)
            workload_rng = random.Random(seed)
            workload = []
            for _ in range(args.transactions):
                source, target = workload_rng.sample(nodes, 2)
                # Synthetic log-uniform payment amounts; the paper's Bitcoin trace is unavailable.
                amount = int(round(10 ** workload_rng.uniform(3, 6)))
                workload.append((source, target, amount))
            for label, method in methods:
                method_graph = graph.copy()
                tx_rows, metrics = run_one(method_graph, nodes, workload, method)
                raw_rows.append({
                    "protocol_label": label, "method": method, "transactions": args.transactions,
                    "capacity_scale": scale, "repetition": repetition + 1, "seed": seed, **metrics,
                })
                for row in tx_rows:
                    per_tx_rows.append({
                        "protocol_label": label, "method": method, "transactions": args.transactions,
                        "capacity_scale": scale, "repetition": repetition + 1, "seed": seed, **row,
                    })
                print(f"scale={scale} run={repetition + 1}/{args.runs} {label}: "
                      f"success={metrics['success_ratio']:.3f} volume={metrics['success_volume']:.3f}")

    raw_path = args.output / "per_run.csv"
    tx_path = args.output / "per_transaction.csv"
    for path, rows in ((raw_path, raw_rows), (tx_path, per_tx_rows)):
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)

    metrics_to_plot = [
        ("success_ratio", "Success ratio", "Fraction"),
        ("success_volume", "Success volume", "Fraction"),
        ("routing_cost", "Routing cost", "Fee / delivered satoshi"),
        ("mean_route_seconds", "Mean route time", "Seconds per payment"),
        ("mean_hops", "Mean successful route length", "Hops"),
    ]
    averaged = []
    for label, method in methods:
        for scale in args.scales:
            subset = [r for r in raw_rows if r["method"] == method and r["capacity_scale"] == scale]
            summary = {"protocol_label": label, "method": method, "capacity_scale": scale,
                       "transactions": args.transactions, "runs": len(subset)}
            for metric, _, _ in metrics_to_plot:
                vals = np.asarray([r[metric] for r in subset], dtype=float)
                summary[metric] = float(vals.mean())
                summary[f"{metric}_std"] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            averaged.append(summary)
    with (args.output / "averaged.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(averaged[0])); writer.writeheader(); writer.writerows(averaged)

    plot_dir = args.output / "plots"
    plot_dir.mkdir(exist_ok=True)
    for metric, title, ylabel in metrics_to_plot:
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        for label, method in methods:
            subset = [r for r in averaged if r["method"] == method]
            xs = [r["capacity_scale"] for r in subset]
            ys = [r[metric] for r in subset]
            err = [r[f"{metric}_std"] for r in subset]
            ax.errorbar(xs, ys, yerr=err, marker="o", capsize=4, label=label)
        ax.set_xlabel("Channel capacity multiplier")
        ax.set_ylabel(ylabel)
        ax.set_title(f"Exploratory proxy pilot: {title}\n{args.transactions} payments/run, {args.runs} runs; not paper reproduction")
        ax.set_xticks(args.scales); ax.legend(); ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(plot_dir / f"{metric}.png", dpi=180)
        fig.savefig(plot_dir / f"{metric}.pdf")
        plt.close(fig)

    metadata = {
        "experiment": "exploratory_proxy_pilot",
        "input": str(args.input), "transactions_per_run": args.transactions,
        "repetitions": args.runs, "capacity_scales": args.scales,
        "base_seed": args.seed, "elapsed_seconds": time.perf_counter() - start_all,
        "liquidity": "50:50 initial balance; balances update after successful payments",
        "amounts": "synthetic log-uniform 1,000 to 1,000,000 sats; not the paper's Bitcoin trace",
        "protocols": "Auroch-like greedy three-path proxy and fee-weighted single-path Dijkstra proxy; not faithful Auroch/Spider/SpeedyMurmurs implementations",
        "policy_handling": "channel policies are ignored in this quick pilot",
        "metrics": "paper success ratio, success volume, routing cost plus exploratory route time and hop count",
        "paper_comparison_claim": False,
    }
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote raw data, averages, metadata, and plots to {args.output}")
    print(f"Elapsed seconds: {metadata['elapsed_seconds']:.1f}")


if __name__ == "__main__":
    main()
