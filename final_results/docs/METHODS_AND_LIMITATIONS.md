# Methods and limitations

## Executed grid

The run executes transaction counts 5,000, 7,000, and 9,000; channel capacity multipliers ×30, ×50, and ×70; and 20 repetitions for every setting. Four routing methods are run on each workload. This produces 36 protocol-setting averages, 720 per-run records, and 1,260,000 attempted transactions per method (5,040,000 protocol decisions in total).

## Input and reproducibility

- Topology: local Lightning snapshot dated 2021-11-27; parsed counts are 18,310 nodes and 80,743 channels. The largest component has 18,110 nodes.
- Liquidity: each directional channel balance starts at half of aggregate channel capacity; successful payments update balances.
- Workload: payment values are generated from a seeded log-uniform distribution between 1,000 and 1,000,000 sat because the Bitcoin volume trace is unavailable. The workload manifest records every generated source, destination, and amount.
- Source/destination: each transaction draws from a fixed seeded pool of 128 ordered pairs in the largest component. The pool is reused with replacement for run-time tractability.
- Routing-time metric covers the cached route selection and capacity-allocation loop only; it excludes the one-time graph and route-cache construction.
- Fees: one satoshi base fee per hop plus a seeded integer rate in [0,10] multiplied by payment amount, following the paper equation's structure. The exact interpretation and units of the paper's rate parameter should be verified before making numerical claims.
- Parallel channels are aggregated by directed endpoint pair. Channel policy constraints are ignored in this benchmark.

## Methods implemented for this run

These are deliberately transparent approximations, not source-faithful implementations:

1. **Auroch-inspired multipath:** greedily allocates across up to three cached low-weight simple routes. It does not implement RREQ/RREP auctions, bid rules, Equation 6 allocation, or Equation 7 LP.
2. **Modified Dijkstra:** uses one cached fee-weighted shortest route and fails when its current bottleneck cannot carry the payment.
3. **Spider-inspired:** greedily splits over up to four cached edge-disjoint routes. This approximates probing and multipath but is not the Spider algorithm.
4. **SpeedyMurmurs-inspired:** uses one route through one of three fixed high-degree landmark trees. It does not implement the original embedding, routing tables, or protocol behavior.

## Metrics

- Success ratio = successful payment count / attempted payment count.
- Success volume = successful satoshi volume / attempted satoshi volume.
- Routing cost = total fee on successful transactions / successful satoshi volume.
- Supplementary outputs: mean hops, mean paths per successful payment, and measured routing-loop time per payment.

Routing has no labeled prediction target, so classifier accuracy is undefined. The supplementary metrics are operational measurements, not accuracy scores.

## Interpretation boundary

The full **parameter grid and repetition count** were executed, but these are assumption-based proxy results. They are useful for exercising the experiment pipeline and inspecting trends under this model. Do not cite their numeric values as the Auroch paper's results or claim exact reproduction. A faithful comparison still requires the missing Bitcoin trace, per-channel directional policy/liquidity treatment, and protocol implementations validated against the paper.
