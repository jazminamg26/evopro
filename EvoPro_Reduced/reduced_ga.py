from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from reduced_problem import ReducedEvoProProblem, ReducedEvoProConfig


@dataclass
class Individual:
    sequence: List[str]
    score: Optional[float] = None
    average_score: Optional[float] = None
    score_history: List[float] = None
    scored: bool = False

    def __post_init__(self) -> None:
        if self.score_history is None:
            self.score_history = []

    def __str__(self) -> str:
        return "".join(self.sequence)

    def set_score(self, score: float, num_repeat_scoring: int = 1) -> None:
        self.score_history.insert(0, score)
        self.score = score
        self.average_score = sum(self.score_history) / len(self.score_history)
        if len(self.score_history) >= num_repeat_scoring:
            self.scored = True

    def get_average_score(self) -> float:
        if self.average_score is not None:
            return self.average_score
        if self.score_history:
            return sum(self.score_history) / len(self.score_history)
        return float("inf")


class GeneticAlgorithmReduced:
    """EvoPro-style GA for the reduced sequence optimisation problem."""

    def __init__(
        self,
        problem: ReducedEvoProProblem,
        pool_size: int = 60,
        mutation_rate: float = 0.15,
        crossover_percent: float = 0.4,
        minimize: bool = True,
        num_repeat_scoring: int = 1,
        random_seed: Optional[int] = None,
        mode: str = "both",
    ) -> None:
        self.problem = problem
        self.pool_size = pool_size
        self.mutation_rate = mutation_rate
        self.crossover_percent = crossover_percent
        self.minimize = minimize
        self.num_repeat_scoring = num_repeat_scoring
        self.mode = mode.lower()
        if self.mode not in {"mutation", "crossover", "both"}:
            raise ValueError("mode must be one of {'mutation', 'crossover', 'both'}")
        if random_seed is not None:
            random.seed(random_seed)
            np.random.seed(random_seed)

        self.initial_sequence = problem.random_sequence()
        self.pool: List[Individual] = []
        self.sequence_registry: dict[str, Individual] = {}
        self.scores_per_iter: List[List[float]] = []
        self.iteration = 0

    # ------------------------------------------------------------------
    # Core GA helpers
    # ------------------------------------------------------------------
    def _initialize_pool(self) -> None:
        self.pool = [Individual(self.initial_sequence.copy())]
        self.sequence_registry[str(self.pool[0])] = self.pool[0]
        while len(self.pool) < self.pool_size:
            new_individual = self._mutate_random(self.pool[-1])
            key = str(new_individual)
            if key not in self.sequence_registry:
                self.pool.append(new_individual)
                self.sequence_registry[key] = new_individual

    def _mutate_random(self, individual: Individual, mutation_rate: Optional[float] = None) -> Individual:
        if mutation_rate is None:
            mutation_rate = self.mutation_rate
        seq = individual.sequence.copy()
        n = len(seq)
        num_mutations = max(1, int(mutation_rate * n))
        for _ in range(num_mutations):
            unsatisfied = self.problem.unsatisfied_motifs(seq)
            if unsatisfied and random.random() < 0.3:
                motif = random.choice(unsatisfied)
                self.problem.enforce_motif(seq, motif)
                continue

            hyd_idx = self.problem.random_hydrophobic_index()
            if hyd_idx is not None and random.random() < 0.3:
                self.problem.mutate_to_hydrophobic(seq, hyd_idx)
                continue

            if random.random() < 0.2:
                self.problem.adjust_charge(seq)
                continue

            move = random.choice(["substitution", "swap", "shuffle"])
            if move == "substitution":
                idx = random.randrange(n)
                self.problem.mutate_position(seq, idx)
            elif move == "swap":
                i, j = random.sample(range(n), 2)
                seq[i], seq[j] = seq[j], seq[i]
            else:
                start = random.randrange(max(1, n - 3))
                window = seq[start:start + 3]
                random.shuffle(window)
                seq[start:start + 3] = window
        return Individual(seq)

    def _crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """Single-point crossover."""
        n = len(parent1.sequence)
        point = random.randint(1, n - 1)
        child = parent1.sequence[:point] + parent2.sequence[point:]
        return Individual(child)

    def _evaluate_pool(self) -> None:
        for individual in self.pool:
            if not individual.scored:
                scores = self.problem.evaluate(individual.sequence)
                individual.set_score(scores["overall"], self.num_repeat_scoring)

    def _sort_pool(self) -> None:
        self.pool.sort(key=lambda x: x.get_average_score(), reverse=not self.minimize)

    def _purge_pool(self) -> None:
        purge_size = int(self.pool_size / 2)
        if len(self.pool) > purge_size:
            self._sort_pool()
            self.pool = self.pool[:purge_size]

    def _generate_offspring(self, parent: Individual) -> Individual:
        if self.mode == "mutation":
            return self._mutate_random(parent)

        if self.mode == "crossover":
            if len(self.pool) < 2:
                return self._mutate_random(parent)
            parent2_candidates = [p for p in self.pool if p is not parent]
            parent2 = random.choice(parent2_candidates)
            return self._crossover(parent, parent2)

        offspring = parent
        if len(self.pool) > 1 and random.random() < self.crossover_percent:
            parent2_candidates = [p for p in self.pool if p is not parent]
            parent2 = random.choice(parent2_candidates)
            offspring = self._crossover(parent, parent2)
        if random.random() < self.mutation_rate:
            offspring = self._mutate_random(offspring)
        return offspring

    def _refill_pool(self) -> None:
        attempts = 0
        while len(self.pool) < self.pool_size:
            parent = random.choice(self.pool)
            offspring = self._generate_offspring(parent)
            key = str(offspring)
            if key in self.sequence_registry:
                offspring = self.sequence_registry[key]
            else:
                self.sequence_registry[key] = offspring
            if key not in {str(p) for p in self.pool}:
                self.pool.append(offspring)

            attempts += 1
            if attempts > 200:
                random_parent = random.choice(self.pool)
                mutated = self._mutate_random(random_parent, mutation_rate=0.5)
                key = str(mutated)
                if key not in self.sequence_registry:
                    self.sequence_registry[key] = mutated
                if key not in {str(p) for p in self.pool}:
                    self.pool.append(mutated)
                    break

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(self, num_iterations: int, verbose: bool = True) -> Tuple[List[str], float]:
        self._initialize_pool()
        if verbose:
            print(f"Iteration 0: evaluating initial pool of {len(self.pool)} sequences...")
        self._evaluate_pool()
        self._sort_pool()
        best_individual = self.pool[0]
        if verbose:
            print(f"Initial best score: {best_individual.get_average_score():.3f}")
            print(f"Initial best sequence: {str(best_individual)}\n")

        for iteration in range(1, num_iterations + 1):
            self.iteration = iteration
            if verbose:
                print(f"{'='*70}")
                print(f"Iteration {iteration}/{num_iterations}")

            self._purge_pool()
            if verbose:
                print(f"Pool after purge: {len(self.pool)} sequences")

            self._refill_pool()
            if verbose:
                print(f"Pool after refill: {len(self.pool)} sequences")

            self._evaluate_pool()
            self._sort_pool()

            current_best = self.pool[0]
            if (self.minimize and current_best.get_average_score() < best_individual.get_average_score()) or \
               (not self.minimize and current_best.get_average_score() > best_individual.get_average_score()):
                best_individual = current_best

            scores = [ind.get_average_score() for ind in self.pool]
            self.scores_per_iter.append(scores)
            if verbose:
                print(f"Best score:   {best_individual.get_average_score():.3f}")
                print(f"Average pool: {np.mean(scores):.3f}")
                print(f"Pool std dev: {np.std(scores):.3f}")

        return best_individual.sequence, best_individual.get_average_score()

    def get_best_individual(self) -> Tuple[List[str], float]:
        self._sort_pool()
        best = self.pool[0]
        return best.sequence, best.get_average_score()

