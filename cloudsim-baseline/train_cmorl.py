#!/usr/bin/env python3
"""
C-MORL Training Script
Implements two-stage training:
  Stage 1: Pareto initialization (M=6 policies, 1.5M timesteps each)
  Stage 2: Pareto extension (N=5 policies, K=60 constrained steps)
"""

import numpy as np
import torch
from pathlib import Path
import logging
import json
from datetime import datetime
from typing import Dict, List
import argparse

from cmorl_environment import CMORLEnvironment
from cmorl_agent import CMORLAgent
from pareto_utils import ParetoFront, sample_preference_vectors

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CMORLTrainer:
    """
    C-MORL Training Manager
    Coordinates two-stage training process
    """

    def __init__(self,
                 output_dir: str = 'cmorl_results',
                 simulation_hours: int = 24,
                 vms_per_hour: int = 10,
                 random_seed: int = 42):
        """
        Initialize trainer

        Args:
            output_dir: Directory for saving results
            simulation_hours: Episode length in hours
            vms_per_hour: VMs per hour
            random_seed: Random seed
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.simulation_hours = simulation_hours
        self.vms_per_hour = vms_per_hour
        self.random_seed = random_seed

        # Set seeds
        np.random.seed(random_seed)
        torch.manual_seed(random_seed)

        # Initialize Pareto front
        self.pareto_front = ParetoFront(num_objectives=3)

        # Training history
        self.training_history = []

        logger.info(f"Initialized C-MORL Trainer")
        logger.info(f"Output directory: {self.output_dir}")

    def collect_trajectory(self, env: CMORLEnvironment, agent: CMORLAgent,
                          max_steps: int = None) -> Dict:
        """
        Collect trajectory from environment

        Returns:
            trajectory: Dict with states, actions, rewards, etc.
        """
        states = []
        actions = []
        log_probs = []
        rewards_energy = []
        rewards_carbon = []
        rewards_latency = []
        dones = []

        state, info = env.reset(seed=self.random_seed)
        episode_return = {
            'R_energy': 0.0,
            'R_carbon': 0.0,
            'R_latency': 0.0
        }

        steps = 0
        done = False

        while not done:
            # Select action
            action, log_prob = agent.select_action(state, deterministic=False)

            # Take step
            next_state, reward, done, truncated, info = env.step(action)

            # Store transition
            states.append(state)
            actions.append(action)
            log_probs.append(log_prob)
            rewards_energy.append(reward['R_energy'])
            rewards_carbon.append(reward['R_carbon'])
            rewards_latency.append(reward['R_latency'])
            dones.append(done)

            # Update episode return
            episode_return['R_energy'] += reward['R_energy']
            episode_return['R_carbon'] += reward['R_carbon']
            episode_return['R_latency'] += reward['R_latency']

            state = next_state
            steps += 1

            if max_steps and steps >= max_steps:
                break

        # Get final episode metrics from CloudSim
        if done and info['total_placements'] > 0:
            episode_metrics = {
                'energy_kwh': info['episode_energy'],
                'carbon_gco2': info['episode_carbon'],
                'latency_ms': info['episode_latency'],
                'failures': info['episode_failures'],
                'total_placements': info['total_placements']
            }
        else:
            episode_metrics = {
                'energy_kwh': 0.0,
                'carbon_gco2': 0.0,
                'latency_ms': 0.0,
                'failures': 0,
                'total_placements': 0
            }

        return {
            'states': np.array(states),
            'actions': np.array(actions),
            'log_probs': np.array(log_probs),
            'rewards_dict': {
                'R_energy': rewards_energy,
                'R_carbon': rewards_carbon,
                'R_latency': rewards_latency
            },
            'dones': dones,
            'episode_return': episode_return,
            'episode_metrics': episode_metrics,
            'steps': steps
        }

    def train_policy(self, agent: CMORLAgent, env: CMORLEnvironment,
                    total_timesteps: int, eval_freq: int = 10000,
                    save_path: str = None) -> Dict:
        """
        Train a single policy

        Args:
            agent: C-MORL agent
            env: Environment
            total_timesteps: Total training timesteps
            eval_freq: Evaluation frequency
            save_path: Path to save agent

        Returns:
            training_info: Training statistics
        """
        logger.info(f"Training policy with preference {agent.preference_vector.cpu().numpy()}")
        logger.info(f"Target timesteps: {total_timesteps}")

        timesteps = 0
        episode = 0
        best_return = -np.inf

        while timesteps < total_timesteps:
            # Collect trajectory
            trajectory = self.collect_trajectory(env, agent)

            # Update agent
            update_info = agent.update(
                states=trajectory['states'],
                actions=trajectory['actions'],
                old_log_probs=trajectory['log_probs'],
                rewards_dict=trajectory['rewards_dict'],
                dones=trajectory['dones'],
                epochs=10,
                batch_size=64
            )

            timesteps += trajectory['steps']
            episode += 1

            # Logging
            if episode % 10 == 0:
                logger.info(f"Episode {episode}, Timesteps {timesteps}/{total_timesteps}")
                logger.info(f"  Return: E={trajectory['episode_return']['R_energy']:.3f}, "
                           f"C={trajectory['episode_return']['R_carbon']:.3f}, "
                           f"L={trajectory['episode_return']['R_latency']:.3f}")
                logger.info(f"  Metrics: Energy={trajectory['episode_metrics']['energy_kwh']:.2f} kWh, "
                           f"Carbon={trajectory['episode_metrics']['carbon_gco2']:.2f} gCO2")
                logger.info(f"  Loss: Policy={update_info['policy_loss']:.4f}, "
                           f"Value={update_info['value_loss']:.4f}")

            # Save best agent
            scalarized_return = (
                agent.preference_vector[0] * trajectory['episode_return']['R_energy'] +
                agent.preference_vector[1] * trajectory['episode_return']['R_carbon'] +
                agent.preference_vector[2] * trajectory['episode_return']['R_latency']
            ).item()

            if scalarized_return > best_return:
                best_return = scalarized_return
                if save_path:
                    agent.save(save_path)

        logger.info(f"Training complete: {timesteps} timesteps, {episode} episodes")

        # Final evaluation
        final_trajectory = self.collect_trajectory(env, agent)

        return {
            'total_timesteps': timesteps,
            'total_episodes': episode,
            'final_metrics': final_trajectory['episode_metrics'],
            'best_return': best_return
        }

    def stage1_pareto_initialization(self, n_policies: int = 6,
                                     timesteps_per_policy: int = 150000):
        """
        Stage 1: Pareto Initialization
        Train M policies with fixed preference vectors

        Args:
            n_policies: Number of policies to train (M=6 from paper)
            timesteps_per_policy: Timesteps per policy (1.5M from paper, using 150K for testing)
        """
        logger.info("="*80)
        logger.info("STAGE 1: PARETO INITIALIZATION")
        logger.info("="*80)
        logger.info(f"Training {n_policies} policies with {timesteps_per_policy} timesteps each")

        # Sample preference vectors
        preferences = sample_preference_vectors(n_policies, n_objectives=3)

        stage1_dir = self.output_dir / "stage1"
        stage1_dir.mkdir(exist_ok=True)

        stage1_results = []

        for i, preference in enumerate(preferences):
            logger.info(f"\n--- Training Policy {i+1}/{n_policies} ---")
            logger.info(f"Preference: {preference}")

            # Create environment
            env = CMORLEnvironment(
                simulation_hours=self.simulation_hours,
                vms_per_hour=self.vms_per_hour,
                random_seed=self.random_seed + i
            )

            # Create agent
            agent = CMORLAgent(
                state_dim=132,
                action_dim=5,
                preference_vector=preference,
                learning_rate=3e-4
            )

            # Train
            save_path = str(stage1_dir / f"policy_{i+1}.pt")
            train_info = self.train_policy(
                agent, env,
                total_timesteps=timesteps_per_policy,
                save_path=save_path
            )

            # Add to Pareto front
            objectives = np.array([
                train_info['final_metrics']['energy_kwh'],
                train_info['final_metrics']['carbon_gco2'],
                train_info['final_metrics']['latency_ms']
            ])

            self.pareto_front.add_solution(
                objectives,
                metadata={
                    'policy_id': i+1,
                    'preference': preference,
                    'save_path': save_path,
                    'stage': 1
                }
            )

            stage1_results.append({
                'policy_id': i+1,
                'preference': preference.tolist(),
                'objectives': objectives.tolist(),
                'train_info': train_info
            })

            env.close()

        # Save Stage 1 results
        self.pareto_front.print_summary()

        with open(stage1_dir / "results.json", 'w') as f:
            json.dump(stage1_results, f, indent=2)

        logger.info("✓ Stage 1 complete")
        return stage1_results

    def stage2_pareto_extension(self, n_select: int = 5, n_steps: int = 60,
                                gamma_constraint: float = 0.9):
        """
        Stage 2: Pareto Extension
        Select sparse solutions and perform constrained optimization

        Args:
            n_select: Number of policies to select (N=5 from paper)
            n_steps: Constrained optimization steps (K=60 from paper)
            gamma_constraint: Constraint relaxation (γ=0.9 from paper)
        """
        logger.info("="*80)
        logger.info("STAGE 2: PARETO EXTENSION")
        logger.info("="*80)
        logger.info(f"Selecting {n_select} sparse solutions for extension")

        # Select sparse solutions
        sparse_solutions = self.pareto_front.select_sparse_solutions(n_select)

        stage2_dir = self.output_dir / "stage2"
        stage2_dir.mkdir(exist_ok=True)

        stage2_results = []

        for sol_idx, (pareto_idx, crowding_distance) in enumerate(sparse_solutions):
            logger.info(f"\n--- Extending Solution {sol_idx+1}/{n_select} ---")
            logger.info(f"Crowding distance: {crowding_distance:.3f}")

            objectives, metadata = self.pareto_front.get_solution(pareto_idx)
            logger.info(f"Base objectives: {objectives}")

            # Load base policy
            base_agent = CMORLAgent(
                state_dim=132,
                action_dim=5,
                preference_vector=metadata['preference']
            )
            base_agent.load(metadata['save_path'])

            # Create environment
            env = CMORLEnvironment(
                simulation_hours=self.simulation_hours,
                vms_per_hour=self.vms_per_hour,
                random_seed=self.random_seed + 100 + sol_idx
            )

            # Perform constrained optimization
            # Maximize each objective while constraining others
            for target_obj_idx, target_obj_name in enumerate(['Energy', 'Carbon', 'Latency']):
                logger.info(f"  Optimizing {target_obj_name}...")

                # Create new preference emphasizing target objective
                new_preference = np.zeros(3)
                new_preference[target_obj_idx] = 0.7
                other_weight = 0.15
                for i in range(3):
                    if i != target_obj_idx:
                        new_preference[i] = other_weight

                # Create new agent with adjusted preference
                extended_agent = CMORLAgent(
                    state_dim=132,
                    action_dim=5,
                    preference_vector=new_preference
                )

                # Copy weights from base agent
                extended_agent.policy.load_state_dict(base_agent.policy.state_dict())
                extended_agent.value_net.load_state_dict(base_agent.value_net.state_dict())

                # Fine-tune with constrained steps
                save_path = str(stage2_dir / f"extended_{sol_idx+1}_{target_obj_name.lower()}.pt")
                train_info = self.train_policy(
                    extended_agent, env,
                    total_timesteps=n_steps * env.simulation_hours * env.vms_per_hour,
                    save_path=save_path
                )

                # Add to Pareto front
                extended_objectives = np.array([
                    train_info['final_metrics']['energy_kwh'],
                    train_info['final_metrics']['carbon_gco2'],
                    train_info['final_metrics']['latency_ms']
                ])

                self.pareto_front.add_solution(
                    extended_objectives,
                    metadata={
                        'policy_id': f"extended_{sol_idx+1}_{target_obj_name}",
                        'preference': new_preference,
                        'save_path': save_path,
                        'stage': 2,
                        'base_solution': pareto_idx
                    }
                )

                stage2_results.append({
                    'base_solution': pareto_idx,
                    'target_objective': target_obj_name,
                    'objectives': extended_objectives.tolist(),
                    'preference': new_preference.tolist()
                })

            env.close()

        # Save Stage 2 results
        self.pareto_front.print_summary()

        with open(stage2_dir / "results.json", 'w') as f:
            json.dump(stage2_results, f, indent=2)

        logger.info("✓ Stage 2 complete")
        return stage2_results

    def save_final_results(self):
        """Save final Pareto front and training summary"""
        results_file = self.output_dir / "final_results.json"

        results = {
            'pareto_front_size': self.pareto_front.get_size(),
            'hypervolume': self.pareto_front.compute_hypervolume(),
            'expected_utility': self.pareto_front.compute_expected_utility(),
            'solutions': []
        }

        for i in range(self.pareto_front.get_size()):
            obj, meta = self.pareto_front.get_solution(i)
            # Convert numpy arrays to lists for JSON serialization
            meta_serializable = {}
            for k, v in meta.items():
                if k == 'save_path':
                    continue
                if isinstance(v, np.ndarray):
                    meta_serializable[k] = v.tolist()
                else:
                    meta_serializable[k] = v

            results['solutions'].append({
                'objectives': obj.tolist(),
                'metadata': meta_serializable
            })

        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Saved final results to {results_file}")


def main():
    parser = argparse.ArgumentParser(description='Train C-MORL agent')
    parser.add_argument('--output-dir', default='cmorl_results', help='Output directory')
    parser.add_argument('--simulation-hours', type=int, default=2, help='Episode length (hours)')
    parser.add_argument('--vms-per-hour', type=int, default=5, help='VMs per hour')
    parser.add_argument('--n-policies', type=int, default=3, help='Number of Stage 1 policies')
    parser.add_argument('--timesteps', type=int, default=10000, help='Timesteps per policy')
    parser.add_argument('--n-extend', type=int, default=2, help='Number of Stage 2 extensions')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    logger.info("="*80)
    logger.info("C-MORL TRAINING")
    logger.info("="*80)
    logger.info(f"Configuration:")
    logger.info(f"  Output dir: {args.output_dir}")
    logger.info(f"  Episode: {args.simulation_hours} hours × {args.vms_per_hour} VMs/hour")
    logger.info(f"  Stage 1: {args.n_policies} policies × {args.timesteps} timesteps")
    logger.info(f"  Stage 2: {args.n_extend} extensions")
    logger.info(f"  Random seed: {args.seed}")

    # Create trainer
    trainer = CMORLTrainer(
        output_dir=args.output_dir,
        simulation_hours=args.simulation_hours,
        vms_per_hour=args.vms_per_hour,
        random_seed=args.seed
    )

    # Stage 1: Pareto Initialization
    stage1_results = trainer.stage1_pareto_initialization(
        n_policies=args.n_policies,
        timesteps_per_policy=args.timesteps
    )

    # Stage 2: Pareto Extension
    stage2_results = trainer.stage2_pareto_extension(
        n_select=min(args.n_extend, len(stage1_results)),
        n_steps=60
    )

    # Save final results
    trainer.save_final_results()

    logger.info("="*80)
    logger.info("✓ C-MORL TRAINING COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
