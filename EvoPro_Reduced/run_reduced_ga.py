from __future__ import annotations

import argparse
from pathlib import Path

from reduced_problem import ReducedEvoProConfig, ReducedEvoProProblem
from reduced_ga import GeneticAlgorithmReduced
from convergence import ConvergenceAnalyzer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EvoPro-style GA on reduced sequence problem",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=Path("data/default_config.json"),
                        help="Path to JSON configuration file")
    parser.add_argument("--iterations", "-i", type=int, default=200,
                        help="Number of GA iterations")
    parser.add_argument("--pool-size", "-p", type=int, default=60,
                        help="Pool size (population)")
    parser.add_argument("--mutation-rate", "-m", type=float, default=0.15,
                        help="Mutation rate (fraction of positions)")
    parser.add_argument("--crossover", "-c", type=float, default=0.4,
                        help="Probability of crossover during refill")
    parser.add_argument("--mode", choices=["mutation", "crossover", "both"], default="both",
                        help="Operator mode to evaluate")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed")
    parser.add_argument("--no-plots", action="store_true",
                        help="Disable plot generation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = ReducedEvoProConfig.from_json(args.config)
    problem = ReducedEvoProProblem(config)

    print("=" * 70)
    print("Reduced EvoPro Genetic Algorithm")
    print("=" * 70)
    print(f"Sequence length: {config.sequence_length}, alphabet: {config.alphabet}\n")

    ga = GeneticAlgorithmReduced(
        problem=problem,
        pool_size=args.pool_size,
        mutation_rate=args.mutation_rate,
        crossover_percent=args.crossover,
        minimize=True,
        random_seed=args.seed,
        mode=args.mode,
    )

    best_seq, best_score = ga.run(num_iterations=args.iterations, verbose=True)
    best_str = problem.sequence_to_str(best_seq)

    print("\n" + "=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print(f"Best sequence: {best_str}")
    print(f"Best overall score: {best_score:.3f}")

    comp = problem.evaluate(best_seq)
    for k, v in comp.items():
        if k != "overall":
            print(f"  {k}: {v:.3f} (weight={problem.weights.get(k, 0.0)})")

    analyzer = ConvergenceAnalyzer(ga)
    analyzer.print_summary()

    if not args.no_plots:
        analyzer.plot_convergence(save_path="reduced_convergence.png", show=False)
        analyzer.plot_diversity_evolution(save_path="reduced_diversity.png", show=False)
        print("Plots saved: reduced_convergence.png, reduced_diversity.png")


if __name__ == "__main__":
    main()

