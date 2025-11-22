#!/usr/bin/env python3
"""
Pareto Front Utilities for C-MORL
Implements:
- Non-dominated sorting
- Crowding distance calculation
- Hypervolume computation
- Pareto front management
"""

import numpy as np
from typing import List, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParetoFront:
    """
    Manages Pareto front for multi-objective optimization
    Tracks non-dominated solutions and computes quality metrics
    """

    def __init__(self, num_objectives: int = 3):
        """
        Initialize Pareto front

        Args:
            num_objectives: Number of objectives (3 for energy, carbon, latency)
        """
        self.num_objectives = num_objectives
        self.solutions = []  # List of (objectives, metadata) tuples
        self.reference_point = None  # For hypervolume calculation

    def add_solution(self, objectives: np.ndarray, metadata: Dict = None):
        """
        Add a solution to the Pareto front

        Args:
            objectives: Array of objective values [energy, carbon, latency]
            metadata: Additional info (policy path, preference vector, etc.)
        """
        objectives = np.array(objectives, dtype=np.float64)

        # Check if solution is dominated by existing solutions
        dominated = False
        to_remove = []

        for i, (existing_obj, existing_meta) in enumerate(self.solutions):
            if self._dominates(existing_obj, objectives):
                dominated = True
                break
            elif self._dominates(objectives, existing_obj):
                to_remove.append(i)

        # Remove dominated solutions
        for i in reversed(to_remove):
            self.solutions.pop(i)

        # Add new solution if not dominated
        if not dominated:
            if metadata is None:
                metadata = {}
            self.solutions.append((objectives, metadata))
            logger.debug(f"Added solution to Pareto front: {objectives}")

    def _dominates(self, obj1: np.ndarray, obj2: np.ndarray) -> bool:
        """
        Check if obj1 dominates obj2 (assuming minimization for all objectives)

        Args:
            obj1: First objective vector
            obj2: Second objective vector

        Returns:
            True if obj1 dominates obj2
        """
        # obj1 dominates obj2 if:
        # - obj1 is no worse than obj2 in all objectives
        # - obj1 is strictly better than obj2 in at least one objective

        better_in_all = np.all(obj1 <= obj2)
        strictly_better_in_one = np.any(obj1 < obj2)

        return better_in_all and strictly_better_in_one

    def get_objectives_array(self) -> np.ndarray:
        """Get array of all objective vectors in Pareto front"""
        if not self.solutions:
            return np.array([])
        return np.array([obj for obj, _ in self.solutions])

    def compute_crowding_distance(self) -> np.ndarray:
        """
        Compute crowding distance for each solution in Pareto front
        Used to identify sparse regions for Stage 2 selection

        Returns:
            Array of crowding distances
        """
        n_solutions = len(self.solutions)

        if n_solutions <= 2:
            # Boundary solutions have infinite crowding distance
            return np.full(n_solutions, np.inf)

        objectives = self.get_objectives_array()
        crowding_distances = np.zeros(n_solutions)

        # Compute crowding distance for each objective
        for obj_idx in range(self.num_objectives):
            # Sort solutions by this objective
            sorted_indices = np.argsort(objectives[:, obj_idx])

            # Boundary solutions get infinite distance
            crowding_distances[sorted_indices[0]] = np.inf
            crowding_distances[sorted_indices[-1]] = np.inf

            # Normalize objective range
            obj_range = objectives[sorted_indices[-1], obj_idx] - objectives[sorted_indices[0], obj_idx]

            if obj_range == 0:
                continue

            # Compute distance for interior solutions
            for i in range(1, n_solutions - 1):
                distance = (objectives[sorted_indices[i + 1], obj_idx] -
                          objectives[sorted_indices[i - 1], obj_idx]) / obj_range
                crowding_distances[sorted_indices[i]] += distance

        return crowding_distances

    def select_sparse_solutions(self, n_select: int) -> List[Tuple[int, float]]:
        """
        Select solutions from sparse regions of Pareto front
        Used in Stage 2: Pareto extension

        Args:
            n_select: Number of solutions to select (N=5 from paper)

        Returns:
            List of (index, crowding_distance) tuples
        """
        if len(self.solutions) <= n_select:
            return [(i, np.inf) for i in range(len(self.solutions))]

        crowding_distances = self.compute_crowding_distance()

        # Sort by crowding distance (descending)
        sorted_indices = np.argsort(-crowding_distances)

        # Select top N most sparse solutions
        selected = [(idx, crowding_distances[idx]) for idx in sorted_indices[:n_select]]

        logger.info(f"Selected {len(selected)} sparse solutions with crowding distances: "
                   f"{[f'{cd:.3f}' for _, cd in selected]}")

        return selected

    def compute_hypervolume(self, reference_point: np.ndarray = None) -> float:
        """
        Compute hypervolume indicator for Pareto front
        Measures the volume of objective space dominated by the front

        Args:
            reference_point: Reference point for hypervolume (default: worst point)

        Returns:
            Hypervolume value
        """
        if not self.solutions:
            return 0.0

        objectives = self.get_objectives_array()

        if reference_point is None:
            # Use worst point as reference (max of each objective + margin)
            reference_point = np.max(objectives, axis=0) * 1.1

        self.reference_point = reference_point

        # Simple hypervolume calculation (works for 2-3 objectives)
        # For production, consider using pygmo or similar library
        if self.num_objectives == 2:
            return self._compute_hypervolume_2d(objectives, reference_point)
        elif self.num_objectives == 3:
            return self._compute_hypervolume_3d(objectives, reference_point)
        else:
            logger.warning("Hypervolume computation only implemented for 2-3 objectives")
            return 0.0

    def _compute_hypervolume_2d(self, objectives: np.ndarray, ref_point: np.ndarray) -> float:
        """Compute 2D hypervolume"""
        # Sort by first objective
        sorted_indices = np.argsort(objectives[:, 0])
        sorted_objectives = objectives[sorted_indices]

        hypervolume = 0.0
        prev_x = 0.0

        for obj in sorted_objectives:
            if np.all(obj < ref_point):
                width = obj[0] - prev_x
                height = ref_point[1] - obj[1]
                hypervolume += width * height
                prev_x = obj[0]

        return hypervolume

    def _compute_hypervolume_3d(self, objectives: np.ndarray, ref_point: np.ndarray) -> float:
        """Compute 3D hypervolume (simplified approximation)"""
        # Approximate using sum of individual boxes
        # More accurate algorithms exist but are complex

        hypervolume = 0.0

        for obj in objectives:
            if np.all(obj < ref_point):
                # Volume of box from obj to reference point
                box_volume = np.prod(ref_point - obj)
                hypervolume += box_volume

        # This is an upper bound approximation (doesn't account for overlaps)
        # For production, use pygmo.hypervolume or similar
        return hypervolume * 0.5  # Rough correction for overlaps

    def compute_expected_utility(self, n_samples: int = 100) -> float:
        """
        Compute expected utility across uniformly sampled preferences
        Measures average performance across different preference vectors

        Args:
            n_samples: Number of preference samples

        Returns:
            Expected utility value
        """
        if not self.solutions:
            return 0.0

        objectives = self.get_objectives_array()
        utilities = []

        # Sample preference vectors uniformly from simplex
        for _ in range(n_samples):
            # Sample from Dirichlet distribution (uniform over simplex)
            preference = np.random.dirichlet(np.ones(self.num_objectives))

            # Find best solution for this preference
            scalarized_values = np.dot(objectives, preference)
            best_value = np.min(scalarized_values)  # Minimization
            utilities.append(-best_value)  # Convert to utility (higher is better)

        return np.mean(utilities)

    def get_size(self) -> int:
        """Get number of solutions in Pareto front"""
        return len(self.solutions)

    def get_solution(self, index: int) -> Tuple[np.ndarray, Dict]:
        """Get solution at index"""
        return self.solutions[index]

    def print_summary(self):
        """Print Pareto front summary"""
        print(f"\n{'='*80}")
        print(f"PARETO FRONT SUMMARY")
        print(f"{'='*80}")
        print(f"Number of solutions: {len(self.solutions)}")

        if self.solutions:
            objectives = self.get_objectives_array()
            print(f"\nObjective ranges:")
            print(f"  Energy:  [{objectives[:, 0].min():.3f}, {objectives[:, 0].max():.3f}]")
            print(f"  Carbon:  [{objectives[:, 1].min():.3f}, {objectives[:, 1].max():.3f}]")
            print(f"  Latency: [{objectives[:, 2].min():.3f}, {objectives[:, 2].max():.3f}]")

            crowding = self.compute_crowding_distance()
            finite_crowding = crowding[~np.isinf(crowding)]
            if len(finite_crowding) > 0:
                print(f"\nCrowding distance range: [{finite_crowding.min():.3f}, "
                      f"{finite_crowding.max():.3f}]")
            else:
                print(f"\nCrowding distance: All solutions have infinite distance (boundary solutions)")

            hv = self.compute_hypervolume()
            print(f"Hypervolume: {hv:.3f}")

            eu = self.compute_expected_utility()
            print(f"Expected utility: {eu:.3f}")

        print(f"{'='*80}\n")


def sample_preference_vectors(n_vectors: int, n_objectives: int = 3) -> np.ndarray:
    """
    Sample preference vectors uniformly from simplex
    Used in Stage 1: Pareto initialization

    Args:
        n_vectors: Number of vectors to sample (M=6 from paper)
        n_objectives: Number of objectives

    Returns:
        Array of preference vectors (n_vectors × n_objectives)
    """
    # Sample from Dirichlet distribution with uniform prior
    preferences = np.random.dirichlet(np.ones(n_objectives), size=n_vectors)

    logger.info(f"Sampled {n_vectors} preference vectors:")
    for i, pref in enumerate(preferences):
        logger.info(f"  Preference {i+1}: {pref}")

    return preferences


if __name__ == "__main__":
    # Test Pareto front utilities
    print("="*80)
    print("PARETO UTILITIES TEST")
    print("="*80)

    # Create Pareto front
    pf = ParetoFront(num_objectives=3)

    # Add some test solutions
    print("\nAdding test solutions...")
    test_solutions = [
        np.array([1.0, 2.0, 3.0]),  # Solution 1
        np.array([2.0, 1.0, 3.0]),  # Solution 2
        np.array([3.0, 3.0, 1.0]),  # Solution 3 (dominated)
        np.array([0.5, 2.5, 2.5]),  # Solution 4
        np.array([1.5, 1.5, 2.0]),  # Solution 5
    ]

    for i, sol in enumerate(test_solutions):
        pf.add_solution(sol, metadata={'id': i+1})
        print(f"  Added solution {i+1}: {sol}")

    # Print summary
    pf.print_summary()

    # Test crowding distance
    print("\nCrowding distances:")
    crowding = pf.compute_crowding_distance()
    for i, cd in enumerate(crowding):
        print(f"  Solution {i+1}: {cd:.3f}")

    # Test sparse selection
    print("\nSelecting 2 sparse solutions:")
    sparse = pf.select_sparse_solutions(n_select=2)
    for idx, cd in sparse:
        obj, meta = pf.get_solution(idx)
        print(f"  Solution {meta['id']}: objectives={obj}, crowding={cd:.3f}")

    # Test preference sampling
    print("\nSampling 6 preference vectors:")
    preferences = sample_preference_vectors(n_vectors=6)

    print("\n" + "="*80)
    print("✓ PARETO UTILITIES TEST COMPLETED")
    print("="*80)
