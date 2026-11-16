# Experiment plan and paper comparison

## Reference experiment

The reference is Ababneh, Kolachala, and Vishwanathan, “Auroch: Auction-Based Multipath Routing for Payment Channel Networks,” ASIA CCS 2024. The authors compare Auroch with modified shortest-path/Dijkstra, Spider, and SpeedyMurmurs. Their workload has 5,000, 7,000, or 9,000 payments; capacities are multiplied by 30, 50, or 70; source and destination are random; amounts are sampled from a Bitcoin transaction-volume trace; base fee is 1 satoshi and rate fee is sampled from 0–10 satoshis; and results average 20 runs. The reference dataset is a Lightning snapshot from 2021-11-27.

Paper definitions:

- **Success ratio:** successful payments / attempted payments.
- **Success volume:** successful payment amount / attempted payment amount.
- **Routing cost:** fees for successful transactions / successfully routed payment volume. Lower is better.

The paper describes balance data as unavailable after transactions. Its Lightning topology file does not reveal a reproducible initial balance assignment. This repository's current simulation uses an explicit 50:50 channel split, which must be treated as a modeling assumption.

## Inputs found locally

The repository contains `../lngraph_2021_11_27__00_00.json` (~111 MB) at its root. It does not contain the compressed `.json.zst` named in the earlier README, a Bitcoin amount trace, or Ripple transaction records. The paper uses Ripple counts to choose workload sizes, not necessarily as sender/receiver identities for Lightning. Do not imply that synthetic amounts reproduce the paper's trace.

The available graph has previously been reported by this repository as 18,310 nodes and 80,743 channels; the paper reports 18,331 and 80,918. Preserve this discrepancy in captions and result metadata.

## Metric terminology

Routing does not have labeled ground truth, so classifier **accuracy** is not defined. Useful additional descriptive metrics include elapsed routing time per payment, successful-payment fee per satoshi delivered, mean route hop count, and liquidity utilization. These are operational measurements, not accuracy scores and not paper-defined metrics.

## Reproduction status

The existing `liquidity.py` executes one 100,000-satoshi payment. It does not implement the multi-transaction workload or all four paper protocols. Spider and SpeedyMurmurs need their own faithful implementations and parameterization before a direct four-way comparison can be claimed. ECDSA in the current implementation is also incomplete. A chart produced from synthetic amounts, approximate baselines, or a subgraph must identify those limitations in its title, legend, and metadata.

## Generated local topology analysis

`scripts/topology_report.py` was run against the available root snapshot. It produced six figure families (degree distribution, channel capacity histogram, channel capacity CDF, policy availability, network scale, and largest component sizes), each as PNG and PDF, plus `results/raw/topology_summary.json`. The graph has 18,310 nodes, 80,743 channels, 95 connected components, and a largest connected component of 18,110 nodes. This is an input-data audit and visual description, not a routing protocol comparison.

## Exploratory multi-payment pilot

`scripts/quick_eval.py` ran 50 payments × 3 repetitions × 3 capacity scales (30×/50×/70×), comparing a greedy three-path multipath proxy with a fee-weighted single-path Dijkstra proxy. It completed in about 29 seconds and generated per-run/per-payment CSVs, averages, metadata, and five metric figures under `results/quick_pilot/`. It uses synthetic log-uniform payment sizes, 50:50 starting liquidity, and ignores directional policies. The multipath proxy is not the Auroch auction protocol, and the Dijkstra proxy is not the paper's modified Dijkstra implementation; no Spider or SpeedyMurmurs code is included. Treat these plots as a pipeline pilot only.

## Planned workload size

The paper's grid is 3 transaction counts × 3 capacity multipliers × 20 repetitions = 180 runs, or 1,260,000 attempted payments. This is an estimate of workload size only; runtime depends on the evaluator and machine. Benchmark a small sample first, then estimate full runtime from measured timings.

## Parameter-grid execution status

The full grid has now been executed with a 128-pair seeded endpoint pool and synthetic log-uniform payment amounts. Four transparent proxy methods were run for all 720 method/configuration/repetition combinations. The consolidated output is in `../final_results/`. This closes the engineering task of running the complete parameter grid, while faithful paper reproduction remains pending because the data trace and original comparison-protocol implementations are unavailable.
