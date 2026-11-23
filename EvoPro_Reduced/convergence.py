from __future__ import annotations

from typing import List, Optional

import matplotlib.pyplot as plt
import numpy as np


class ConvergenceAnalyzer:
    """Generic convergence analysis for EvoPro-style GA runs."""

    def __init__(self, ga) -> None:
        self.ga = ga
        self.scores_per_iter = ga.scores_per_iter
        self.minimize = getattr(ga, "minimize", True)

    def get_convergence_metrics(self) -> dict:
        if not self.scores_per_iter:
            return {}

        best_scores: List[float] = []
        avg_scores: List[float] = []
        std_scores: List[float] = []
        min_scores: List[float] = []
        max_scores: List[float] = []

        for scores in self.scores_per_iter:
            if self.minimize:
                best_scores.append(min(scores))
            else:
                best_scores.append(max(scores))
            avg_scores.append(float(np.mean(scores)))
            std_scores.append(float(np.std(scores)))
            min_scores.append(float(np.min(scores)))
            max_scores.append(float(np.max(scores)))

        improvements: List[float] = []
        for i in range(1, len(best_scores)):
            if self.minimize:
                improvements.append(best_scores[i - 1] - best_scores[i])
            else:
                improvements.append(best_scores[i] - best_scores[i - 1])

        converged = False
        if len(improvements) >= 3:
            recent = improvements[-3:]
            converged = all(abs(imp) < 1e-3 for imp in recent)

        return {
            "num_iterations": len(self.scores_per_iter),
            "best_scores_per_iter": best_scores,
            "avg_scores_per_iter": avg_scores,
            "std_scores_per_iter": std_scores,
            "min_scores_per_iter": min_scores,
            "max_scores_per_iter": max_scores,
            "improvements": improvements,
            "final_best_score": best_scores[-1],
            "initial_best_score": best_scores[0],
            "total_improvement": best_scores[-1] - best_scores[0],
            "avg_improvement_per_iter": float(np.mean(improvements)) if improvements else 0.0,
            "converged": converged,
        }

    def calculate_diversity(self, iteration: int = -1) -> dict:
        if not self.scores_per_iter:
            return {}
        if iteration >= len(self.scores_per_iter) or iteration < -len(self.scores_per_iter):
            raise IndexError("Iteration out of bounds")

        scores = self.scores_per_iter[iteration]
        unique_scores = len(set(scores))
        score_diversity = unique_scores / len(scores)
        score_range = float(max(scores) - min(scores)) if scores else 0.0
        coef_variation = float(np.std(scores) / np.mean(scores)) if np.mean(scores) != 0 else 0.0

        seq_diversity: Optional[float] = None
        if hasattr(self.ga, "pool") and self.ga.pool:
            identifiers = [str(ind) for ind in self.ga.pool]
            seq_diversity = len(set(identifiers)) / len(identifiers)

        iteration_index = iteration if iteration >= 0 else len(self.scores_per_iter) + iteration

        return {
            "iteration": iteration_index,
            "score_diversity": score_diversity,
            "unique_scores": unique_scores,
            "total_individuals": len(scores),
            "sequence_diversity": seq_diversity,
            "score_range": score_range,
            "coefficient_of_variation": coef_variation,
        }

    def plot_convergence(self, save_path: Optional[str] = None, show: bool = True) -> None:
        metrics = self.get_convergence_metrics()
        if not metrics:
            print("No convergence metrics available")
            return

        iterations = range(metrics["num_iterations"])
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))

        ax1 = axes[0, 0]
        ax1.plot(iterations, metrics["best_scores_per_iter"], "b-o", label="Best Score", linewidth=2)
        ax1.plot(iterations, metrics["avg_scores_per_iter"], "g--", label="Average Score", linewidth=2)
        ax1.fill_between(
            iterations,
            metrics["min_scores_per_iter"],
            metrics["max_scores_per_iter"],
            alpha=0.2,
            color="gray",
            label="Range",
        )
        ax1.set_xlabel("Iteration", fontsize=12)
        ax1.set_ylabel("Score", fontsize=12)
        ax1.set_title("Best Score Evolution", fontsize=14, fontweight="bold")
        ax1.legend(fontsize=10)
        ax1.grid(True, alpha=0.3)

        ax2 = axes[0, 1]
        improvements = metrics["improvements"]
        if improvements:
            improvement_iterations = range(1, len(improvements) + 1)
            colors = ["green" if imp > 0 else "red" for imp in improvements]
            ax2.bar(improvement_iterations, improvements, color=colors, alpha=0.7)
            ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        ax2.set_xlabel("Iteration", fontsize=12)
        ax2.set_ylabel("Improvement", fontsize=12)
        ax2.set_title("Improvement per Iteration", fontsize=14, fontweight="bold")
        ax2.grid(True, alpha=0.3)

        ax3 = axes[1, 0]
        ax3.plot(iterations, metrics["std_scores_per_iter"], "r-o", linewidth=2)
        ax3.set_xlabel("Iteration", fontsize=12)
        ax3.set_ylabel("Standard Deviation", fontsize=12)
        ax3.set_title("Score Standard Deviation", fontsize=14, fontweight="bold")
        ax3.grid(True, alpha=0.3)

        ax4 = axes[1, 1]
        score_ranges = [max_s - min_s for max_s, min_s in zip(metrics["max_scores_per_iter"], metrics["min_scores_per_iter"])]
        ax4.plot(iterations, score_ranges, "m-o", linewidth=2)
        ax4.set_xlabel("Iteration", fontsize=12)
        ax4.set_ylabel("Range (max - min)", fontsize=12)
        ax4.set_title("Score Range per Iteration", fontsize=14, fontweight="bold")
        ax4.grid(True, alpha=0.3)

        info_text = (
            f"Iterations: {metrics['num_iterations']}\n"
            f"Initial score: {metrics['initial_best_score']:.4f}\n"
            f"Final score:   {metrics['final_best_score']:.4f}\n"
            f"Total change:  {metrics['total_improvement']:.4f}\n"
            f"Converged:     {'Yes' if metrics['converged'] else 'No'}"
        )
        fig.text(
            0.99,
            0.01,
            info_text,
            fontsize=10,
            family="monospace",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            verticalalignment="bottom",
            horizontalalignment="right",
        )

        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        fig.suptitle("Genetic Algorithm Convergence Analysis", fontsize=16, fontweight="bold")

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"Plot saved to: {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

    def plot_diversity_evolution(self, save_path: Optional[str] = None, show: bool = True) -> None:
        if not self.scores_per_iter:
            print("No scores recorded; cannot compute diversity")
            return

        diversities = []
        cv_values = []
        iterations = range(len(self.scores_per_iter))

        for idx in iterations:
            metrics = self.calculate_diversity(idx)
            diversities.append(metrics["score_diversity"])
            cv_values.append(metrics["coefficient_of_variation"])

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        ax1.plot(iterations, diversities, "b-o", linewidth=2)
        ax1.set_xlabel("Iteration", fontsize=12)
        ax1.set_ylabel("Diversity (unique scores / total)", fontsize=12)
        ax1.set_title("Score Diversity", fontsize=14, fontweight="bold")
        ax1.set_ylim([0, 1.05])
        ax1.grid(True, alpha=0.3)

        ax2.plot(iterations, cv_values, "r-o", linewidth=2)
        ax2.set_xlabel("Iteration", fontsize=12)
        ax2.set_ylabel("Coefficient of Variation (σ/μ)", fontsize=12)
        ax2.set_title("Coefficient of Variation", fontsize=14, fontweight="bold")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            print(f"Plot saved to: {save_path}")

        if show:
            plt.show()
        else:
            plt.close()

    def print_summary(self) -> None:
        metrics = self.get_convergence_metrics()
        if not metrics:
            print("No convergence data available")
            return

        print("\n" + "=" * 60)
        print("CONVERGENCE SUMMARY")
        print("=" * 60)
        print(f"Iterations:                 {metrics['num_iterations']}")
        print(f"Initial best score:         {metrics['initial_best_score']:.6f}")
        print(f"Final best score:           {metrics['final_best_score']:.6f}")
        print(f"Total improvement:          {metrics['total_improvement']:.6f}")
        print(f"Average improvement/iter:   {metrics['avg_improvement_per_iter']:.6f}")
        print(f"Converged:                  {'Yes' if metrics['converged'] else 'No'}")

        diversity = self.calculate_diversity(-1)
        print(f"\nFinal pool diversity:")
        print(f"  Score diversity:          {diversity['score_diversity']:.4f}")
        print(f"  Unique scores:            {diversity['unique_scores']}/{diversity['total_individuals']}")
        print(f"  Score range:              {diversity['score_range']:.6f}")
        print(f"  Coefficient of variation: {diversity['coefficient_of_variation']:.6f}")

        improvements = metrics['improvements']
        if improvements:
            positive = sum(1 for imp in improvements if imp > 0)
            print(f"  Iterations with improvement: {positive}/{len(improvements)}")
        print("=" * 60 + "\n")

