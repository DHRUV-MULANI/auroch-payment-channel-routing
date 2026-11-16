# Scripts

Executable analysis and evaluation entry points live here. Scripts should accept explicit input/output paths, record their settings, and avoid modifying source datasets. See each script's `--help` output before running it.

- `topology_report.py`: descriptive figures and summary statistics for the local Lightning topology.
- `plot_single_payment.py`: route-allocation chart for the recorded one-payment smoke run.
- `quick_eval.py`: explicitly exploratory multi-payment pipeline pilot; all outputs carry caveats in `metadata.json`.
