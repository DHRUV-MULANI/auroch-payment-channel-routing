# Research checklist status

Updated 2026-11-16. “Done” means the item is present and has actually been run or generated in this repository. A single-payment run does not count as a multi-transaction experiment.

| Requirement | Status | Evidence / next action |
|---|---|---|
| Lightning Network topology analysis | Done | Snapshot audit in `results/raw/topology_summary.json`; source snapshot has 18,310 nodes and 80,743 channels. |
| Graph distribution visualizations | Done | Six topology figure families in PNG and PDF under `results/plots/topology/`. |
| Single-payment Auroch simulation | Done | 100,000-sat smoke run; route split 50,000 / 50,000 / 0; liquidity audit passed. See `results/raw/single_payment_result.json`. |
| Multiple-transaction pilot | Done (exploratory only) | `results/quick_pilot/`: 50 payments/run, 3 repetitions. |
| 5,000 / 7,000 / 9,000 payment workloads | Done for proxy model | Full grid output under `final_results/`; synthetic amounts and a seeded 128-pair pool. |
| Channel capacity ×30 / ×50 / ×70 | Done for proxy model | All three scales executed under `final_results/`. |
| 20 repetitions per configuration | Done for proxy model | 720 per-run method/configuration records across four methods. |
| Success ratio comparison plots | Done for proxy model | `final_results/plots/comparison/success_ratio.png` and PDF. |
| Success volume comparison plots | Done for proxy model | `final_results/plots/comparison/success_volume.png` and PDF. |
| Routing cost comparison plots | Done for proxy model | `final_results/plots/comparison/routing_cost.png` and PDF. |
| Supplementary route time / hop / path plots | Done for proxy model | See `final_results/plots/comparison/`. |
| Faithful Dijkstra / Spider / SpeedyMurmurs comparison | Pending | The executed methods are labeled approximations; original implementations and Bitcoin payment-volume trace are absent. |
| Dynamic liquidity-dependent `tau_fee` | Later | Start only after baseline measurements and plots are completed. |

## Why the full comparison is not marked complete

The paper's baseline grid contains 180 configurations and 1,260,000 attempted payments. The quick pilot is intentionally not that experiment: it uses 50 payments per run, 3 repetitions, synthetic log-uniform amounts, ignores policies, and compares simplified proxies. Add the trace and faithful protocol baselines before reporting the paper's 20-run comparison.

“Accuracy” is not a defined metric for routing outcomes because there is no prediction label. Keep the paper's success ratio, success volume, and routing cost as the primary metrics. Runtime per transaction, hop count, and liquidity utilization can be reported as supplementary operational metrics.
