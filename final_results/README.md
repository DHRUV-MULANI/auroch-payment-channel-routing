# Final experiment results

This folder is the delivery bundle for the full parameter-grid run. Check `raw/metadata.json` first: it records data, assumptions, algorithm definitions, run counts, and whether the result is paper-faithful.

- `raw/per_run.csv`: one record per method, workload size, capacity scale, and repetition.
- `raw/averaged.csv`: averages and standard deviations over repetitions.
- `raw/workload_manifest.csv`: seeded sources, destinations, and payment amounts.
- `raw/metadata.json`: full configuration and limitations.
- `plots/comparison/`: figures for the paper metrics plus routing time, hops, and path count.
- `plots/topology/`: topology input figures.
- `docs/`: interpretation and status.
- `scripts/`: copy of the experiment runner used for this output.
- `data/`: input provenance note; the large source topology remains at the repository root.

The initial parameter-grid implementation uses explicit proxies and synthetic amounts because the Bitcoin amount trace and faithful baselines are absent. It completes the requested grid mechanically, but its algorithm comparison is not a faithful reproduction of the paper.
