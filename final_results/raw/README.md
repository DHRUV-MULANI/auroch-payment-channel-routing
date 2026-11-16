# Final raw results

`per_run.csv` preserves all method/configuration/repetition metrics. `averaged.csv` contains means and sample standard deviations across repetitions. `workload_manifest.csv` records the generated request traces. `metadata.json` is authoritative for assumptions and caveats.

`topology_summary.json` records the input graph audit and `single_payment_result.json` records the prior one-payment run. `per_run_checkpoint.csv` is the last complete checkpoint and duplicates the completed `per_run.csv` for recovery provenance.
