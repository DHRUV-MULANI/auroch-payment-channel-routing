# Results summary

The full grid completed in 175.2 seconds on the current machine, including route-cache construction. It ran 720 simulations: four methods × three transaction counts × three capacity multipliers × 20 repetitions. Each method saw 1,260,000 attempted payments.

Selected exploratory proxy result: for 5,000 payments and ×30 capacity, the Auroch-inspired multipath proxy averaged success ratio 0.582 (sample SD 0.0092), success volume 0.387 (SD 0.0124), and routing cost 6.50 fee units per successfully delivered satoshi (SD 0.142). The Dijkstra proxy averaged 0.548 (SD 0.0087), 0.343 (SD 0.0103), and 6.66 (SD 0.141), respectively.

These values describe the synthetic-workload and simplified-method model in `METHODS_AND_LIMITATIONS.md`; they are not comparable as direct reproduction numbers. The figures cover all counts and capacity scales with error bars (sample standard deviation).
