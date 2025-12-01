#!/usr/bin/env python3
"""
C-MORL Training Script
Implements two-stage training:
  Stage 1: Pareto initialization (M=3 policies, 1000 timesteps each)
  Stage 2: Pareto extension (N=2 policies, K=60 constrained steps)
"""

import numpy as np
import torch
from pathlib import Path
import logging
import json
from datetime import datetime
from typing import Dict, List, Tuple
import argparse
import pandas as pd

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
                state_dim=137,
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
                state_dim=137,
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
                    state_dim=137,
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
                    'base_solution': int(pareto_idx),  # Convert from numpy int64
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

    def evaluate_solution(self, policy_path: str, preference: np.ndarray) -> Tuple[Dict, pd.DataFrame]:
        """
        Evaluate a single policy by running a full episode and collecting detailed results.
        Returns CloudSim results and placement decisions like ECMR does.

        Args:
            policy_path: Path to saved policy weights
            preference: Preference vector for the agent

        Returns:
            (cloudsim_results, placement_decisions_df)
        """
        logger.info(f"Evaluating policy: {policy_path}")

        # Create environment and agent
        env = CMORLEnvironment(
            simulation_hours=self.simulation_hours,
            vms_per_hour=self.vms_per_hour,
            random_seed=self.random_seed
        )

        agent = CMORLAgent(
            state_dim=env.observation_space.shape[0],
            action_dim=env.action_space.n,
            preference_vector=preference
        )

        # Load policy (weights_only=False for compatibility with numpy arrays)
        checkpoint = torch.load(policy_path, weights_only=False)
        agent.policy.load_state_dict(checkpoint['policy_state_dict'])

        # Run evaluation episode
        state, info = env.reset(seed=self.random_seed)
        done = False
        placement_decisions = []

        while not done:
            # Select action deterministically
            action, _ = agent.select_action(state, deterministic=True)
            next_state, reward, done, truncated, info = env.step(action)

            # Record placement decision
            if 'placement_decision' in info:
                placement_decisions.append(info['placement_decision'])

            state = next_state

        # Get final CloudSim results
        cloudsim_results = env.app.getResults()

        # Get datacenter states and convert to ECMR-compatible format
        from cmorl_environment import DATACENTERS as DC_CONFIG

        # Map DC names for display
        dc_names = {
            'DC_MADRID': 'Madrid DC',
            'DC_AMSTERDAM': 'Amsterdam DC',
            'DC_PARIS': 'Paris DC',
            'DC_MILAN': 'Milan DC',
            'DC_STOCKHOLM': 'Stockholm DC'
        }

        class DCStateWrapper:
            """Wrapper to make dict datacenter states compatible with print function"""
            def __init__(self, dc_id, state_dict):
                self.name = dc_names.get(dc_id, dc_id)
                self.carbon_intensity = state_dict['carbon_intensity']
                self.renewable_pct = state_dict['renewable_pct']
                self.dc_type = state_dict.get('dc_type', 'DG')
                self.hydro_mw = state_dict.get('hydro_mw', 0.0)
                self.solar_mw = state_dict.get('solar_mw', 0.0)
                self.wind_mw = state_dict.get('wind_mw', 0.0)
                self.pue = DC_CONFIG[dc_id]['pue']
                self.vms_placed = state_dict['vms_placed']

        datacenter_states = {}
        for dc_id in env.datacenter_ids:
            datacenter_states[dc_id] = {
                'stats': env.app.getDatacenterStats(dc_id),
                'state': DCStateWrapper(dc_id, env.datacenter_states[dc_id])
            }

        env.close()

        # Convert placement decisions to DataFrame
        placement_df = pd.DataFrame(placement_decisions) if placement_decisions else pd.DataFrame()

        return cloudsim_results, placement_df, datacenter_states

    def print_solution_results(self, solution_idx: int, preference: np.ndarray,
                               objectives: np.ndarray, cloudsim_results: Dict,
                               placement_df: pd.DataFrame, datacenter_states: Dict):
        """
        Print detailed results for a single Pareto solution in ECMR format.

        Args:
            solution_idx: Index of solution in Pareto front
            preference: Preference vector used
            objectives: [energy, carbon, latency] objectives
            cloudsim_results: CloudSim simulation results
            placement_df: DataFrame of placement decisions
            datacenter_states: Datacenter statistics and state
        """
        print("="*80)
        print(f"C-MORL SOLUTION #{solution_idx + 1} RESULTS")
        print(f"Preference: Energy={preference[0]:.2f}, Carbon={preference[1]:.2f}, Latency={preference[2]:.2f}")
        print("="*80)
        print()

        # === SECTION 1: Overall Statistics ===
        print(" OVERALL STATISTICS")
        print("-" * 80)
        print(f"  Total IT Energy: {cloudsim_results.get('totalITEnergyKWh', 0):.4f} kWh")
        print(f"  Total Facility Energy (PUE-adjusted): {cloudsim_results.get('totalEnergyKWh', 0):.4f} kWh")
        print(f"  Average PUE: {cloudsim_results.get('averagePUE', 0):.2f}")
        print(f"  Total VMs Requested: {cloudsim_results.get('totalVMs', 0)}")
        print(f"  Successful VMs: {cloudsim_results.get('successfulVMs', 0)}")
        print(f"  Failed VMs: {cloudsim_results.get('failedVMs', 0)}")
        success_rate = (cloudsim_results.get('successfulVMs', 0) /
                       max(cloudsim_results.get('totalVMs', 1), 1) * 100)
        print(f"  Success Rate: {success_rate:.1f}%")
        print()

        # === SECTION 2: Carbon Metrics ===
        print(" CARBON & RENEWABLE METRICS")
        print("-" * 80)

        total_carbon = 0
        weighted_carbon_avg = 0
        weighted_renewable_avg = 0
        total_vms = len(placement_df) if not placement_df.empty else 1

        dc_carbon_details = []
        for dc_id, dc_data in datacenter_states.items():
            stats = dc_data['stats']
            dc_state = dc_data['state']
            dc_energy = stats.get('totalEnergyKWh', 0)
            dc_carbon = dc_energy * (dc_state.carbon_intensity / 1000)  # gCO2/kWh to kgCO2
            total_carbon += dc_carbon

            # Weight by VMs placed
            weighted_carbon_avg += dc_state.carbon_intensity * (dc_state.vms_placed / total_vms)
            weighted_renewable_avg += dc_state.renewable_pct * (dc_state.vms_placed / total_vms)

            dc_carbon_details.append((dc_id, dc_state, dc_energy, dc_carbon, stats))

        print(f"  Total Carbon Emissions: {total_carbon:.4f} kg CO2")
        print(f"  Weighted Avg Carbon Intensity: {weighted_carbon_avg:.1f} gCO2/kWh")
        print(f"  Weighted Avg Renewable %: {weighted_renewable_avg:.1f}%")

        if not placement_df.empty and 'carbon_intensity' in placement_df.columns:
            avg_vm_carbon = placement_df['carbon_intensity'].mean()
            min_vm_carbon = placement_df['carbon_intensity'].min()
            max_vm_carbon = placement_df['carbon_intensity'].max()
            print(f"  VM Carbon Intensity: avg={avg_vm_carbon:.1f}, min={min_vm_carbon:.1f}, max={max_vm_carbon:.1f} gCO2/kWh")
        print()

        # === SECTION 2.5: Green Datacenter Utilization (M5) ===
        print("🌱 M5: GREEN DATACENTER UTILIZATION")
        print("-" * 80)

        if not placement_df.empty and 'dc_type' in placement_df.columns:
            green_dc_placements = sum(1 for _, row in placement_df.iterrows() if row['dc_type'] == 'DG')
            brown_dc_placements = sum(1 for _, row in placement_df.iterrows() if row['dc_type'] == 'DB')
            total_placements = len(placement_df)

            green_utilization_pct = (green_dc_placements / total_placements * 100) if total_placements > 0 else 0
            brown_utilization_pct = (brown_dc_placements / total_placements * 100) if total_placements > 0 else 0

            print(f"  Green Datacenter (DG) VMs: {green_dc_placements} ({green_utilization_pct:.2f}%)")
            print(f"  Brown Datacenter (DB) VMs: {brown_dc_placements} ({brown_utilization_pct:.2f}%)")
            print(f"  ➜ Green DC Utilization Score: {green_utilization_pct/100:.3f}/1.000")

            # Visual bar representation
            green_bar = '█' * int(green_utilization_pct / 2)
            brown_bar = '█' * int(brown_utilization_pct / 2)
            print(f"  Green: {green_bar}")
            print(f"  Brown: {brown_bar}")
        else:
            print("  [DC type data not available in placement decisions]")
        print()

        # === SECTION 3: Per-Datacenter Details ===
        print(" PER-DATACENTER STATISTICS")
        print("-" * 80)

        for dc_id, dc_state, dc_energy, dc_carbon, stats in dc_carbon_details:
            placement_pct = (dc_state.vms_placed / total_vms) * 100 if total_vms > 0 else 0

            print(f"  {dc_id} ({dc_state.name}):")
            print(f"    VMs: {dc_state.vms_placed} ({placement_pct:.1f}% of total)")
            print(f"    IT Energy: {stats.get('itEnergyKWh', 0):.4f} kWh | "
                  f"Total (PUE {dc_state.pue}): {dc_energy:.4f} kWh")
            print(f"    Carbon: {dc_state.carbon_intensity:.0f} gCO2/kWh | "
                  f"Emissions: {dc_carbon:.4f} kg CO2")
            print(f"    Renewable: {dc_state.renewable_pct:.1f}% "
                  f"(Hydro: {dc_state.hydro_mw:.1f} MW, Solar: {dc_state.solar_mw:.1f} MW, Wind: {dc_state.wind_mw:.1f} MW)")
            print(f"    Utilization: CPU {stats.get('cpuUtilization', 0):.1%}, "
                  f"RAM {stats.get('ramUtilization', 0):.1%}")
            print(f"    Server Mix: RH2285: {stats.get('huaweiRH2285Count', 0)}, "
                  f"RH2288: {stats.get('huaweiRH2288Count', 0)}, "
                  f"SR655: {stats.get('lenovoSR655Count', 0)}")
            print()

        # === SECTION 4: VM Distribution ===
        print(" VM TYPE DISTRIBUTION")
        print("-" * 80)
        if not placement_df.empty and 'vm_type' in placement_df.columns:
            type_counts = placement_df['vm_type'].value_counts()
            for vm_type in ['small', 'medium', 'large', 'xlarge']:
                count = type_counts.get(vm_type, 0)
                pct = (count / len(placement_df)) * 100
                bar = '█' * int(pct / 2)
                print(f"  {vm_type:8s}: {count:4d} ({pct:5.1f}%) {bar}")
        print()

        # === SECTION 5: Datacenter Selection ===
        print(" DATACENTER SELECTION DISTRIBUTION")
        print("-" * 80)
        if not placement_df.empty and 'datacenter' in placement_df.columns:
            dc_counts = placement_df['datacenter'].value_counts()
            for dc_id in datacenter_states.keys():
                count = dc_counts.get(dc_id, 0)
                pct = (count / len(placement_df)) * 100 if len(placement_df) > 0 else 0
                bar = '█' * int(pct / 2)
                print(f"  {dc_id:15s}: {count:4d} ({pct:5.1f}%) {bar}")
        print()

        # === SECTION 6: C-MORL Objectives ===
        print(" C-MORL OBJECTIVES (Learned Trade-offs)")
        print("-" * 80)
        print(f"  Energy: {objectives[0]:.4f} kWh")
        print(f"  Carbon: {objectives[1]:.4f} gCO2")
        print(f"  Latency: {objectives[2]:.4f} ms")
        print()

        print("="*80)
        print(f"✓ SOLUTION #{solution_idx + 1} EVALUATION COMPLETE")
        print("="*80)
        print()

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
            # Convert numpy arrays and types to JSON-serializable format
            meta_serializable = {}
            for k, v in meta.items():
                if k == 'save_path':
                    continue
                if isinstance(v, np.ndarray):
                    meta_serializable[k] = v.tolist()
                elif isinstance(v, (np.int32, np.int64)):
                    meta_serializable[k] = int(v)
                elif isinstance(v, (np.float32, np.float64)):
                    meta_serializable[k] = float(v)
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

    # Save final results (JSON format)
    trainer.save_final_results()

    # Evaluate and print detailed results for each Pareto solution
    logger.info("="*80)
    logger.info("EVALUATING PARETO FRONT SOLUTIONS")
    logger.info("="*80)

    pareto_size = trainer.pareto_front.get_size()
    logger.info(f"Evaluating {pareto_size} Pareto solutions with detailed CloudSim results...")
    print()

    for i in range(pareto_size):
        obj, meta = trainer.pareto_front.get_solution(i)
        policy_path = meta.get('save_path')
        preference = meta.get('preference')

        if policy_path and Path(policy_path).exists():
            # Evaluate this solution
            cloudsim_results, placement_df, datacenter_states = trainer.evaluate_solution(
                policy_path, preference
            )

            # Print results in ECMR format
            trainer.print_solution_results(
                solution_idx=i,
                preference=preference,
                objectives=obj,
                cloudsim_results=cloudsim_results,
                placement_df=placement_df,
                datacenter_states=datacenter_states
            )
        else:
            logger.warning(f"Policy file not found for solution {i+1}: {policy_path}")

    logger.info("="*80)
    logger.info("✓ C-MORL TRAINING & EVALUATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    main()
