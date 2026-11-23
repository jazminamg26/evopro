# EvoPro Genetic Algorithm – Reduced Problem Benchmark

This experiment applies the EvoPro-style genetic algorithm to a simplified
sequence-design problem that mimics key aspects of the real EvoPro scoring
function **without invoking AlphaFold predictions**. The goal is to benchmark
GA operators (mutation-only, crossover-only, combined) on a controllable toy
problem before running the full pipeline.

## Contents

```
EvoPro_Reduced/
├── data/
│   └── default_config.json           # scoring weights & target motifs
├── reduced_problem.py                # sequence problem & scoring components
├── reduced_ga.py                     # EvoPro-style GA adapted to sequences
├── convergence.py                    # convergence analysis utilities (shared)
├── run_reduced_ga.py                 # CLI demo for running the GA
└── notebooks/
    └── Reduced_GA_Analysis.ipynb     # interactive exploration/comparison
```

## Quick Start

```bash
cd EvoPro_Reduced
python run_reduced_ga.py --iterations 200 --pool-size 80 --mode both
```

The script will:
1. Load the default problem configuration (`data/default_config.json`).
2. Initialise the GA with a random sequence satisfying the alphabet constraints.
3. Run for the requested number of iterations and print progress.
4. Output the best sequence, its component scores and the overall score.
5. Generate convergence/diversity plots (`reduced_convergence.png`,
   `reduced_diversity.png`).

## Reduced Scoring Function

The toy scoring replicates EvoPro ideas:
- **Disorder proxy**: penalises high content of disorder-promoting residues (K, P).
- **Hydrophobic core**: rewards hydrophobic amino acids in specified positions.
- **Charge balance**: penalises deviations from neutral charge.
- **Motif satisfaction**: rewards presence of target motifs (e.g. "RGD").
- Component weights are configurable in the JSON file, and the GA always
  *minimises* the weighted sum, just like EvoPro.

## GA Modes for Comparison

The GA supports three modes to benchmark operators:
- `mode="mutation"`: only random point mutations (swap amino acids).
- `mode="crossover"`: only single-point crossover between parents.
- `mode="both"`: EvoPro-style mixture (crossover probability + mutation rate).

Each run stores convergence metrics under `results/` so that notebooks or
scripts can perform statistical comparisons (e.g. Mann–Whitney, Wilcoxon).

## Notebook

`notebooks/Reduced_GA_Analysis.ipynb` demonstrates:
- Running multiple repeats per mode with different seeds.
- Collecting results into CSV / pickle files.
- Performing statistical tests between modes.
- Visualising convergence curves and component contributions.

## Extending

- Adjust the alphabet or scoring weights in `data/default_config.json`.
- Add new scoring components inside `reduced_problem.py`.
- Implement additional mutation/crossover operators in `reduced_ga.py`.
- Use the same convergence utilities to evaluate other GA experiments.

This reduced benchmark is intended as a fast sandbox for GA ideas before
plugging them into the full EvoPro + AlphaFold pipeline.

