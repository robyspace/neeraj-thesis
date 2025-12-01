#!/usr/bin/env python3
"""
Multi-Objective PPO Agent for C-MORL (Proximal Policy Optimization)
Implements PPO with separate value networks for each objective
Supports preference-based scalarization
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
import numpy as np
from typing import Dict, Tuple, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MultiObjectiveValueNetwork(nn.Module):
    """
    Separate value networks for each objective
    Architecture: 3 parallel value heads sharing feature extraction
    """

    def __init__(self, state_dim: int, hidden_dim: int = 256):
        super().__init__()

        # Shared feature extraction
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )

        # Separate value heads for each objective
        self.v_energy = nn.Linear(hidden_dim, 1)
        self.v_carbon = nn.Linear(hidden_dim, 1)
        self.v_latency = nn.Linear(hidden_dim, 1)

    def forward(self, state):
        """Returns dict with three value estimates"""
        features = self.shared(state)
        return {
            'v_energy': self.v_energy(features).squeeze(-1),
            'v_carbon': self.v_carbon(features).squeeze(-1),
            'v_latency': self.v_latency(features).squeeze(-1)
        }


class PolicyNetwork(nn.Module):
    """Policy network for action selection"""

    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim)
        )

    def forward(self, state):
        """Returns action logits"""
        return self.network(state)

    def get_action_probs(self, state):
        """Returns action probabilities"""
        logits = self.forward(state)
        return F.softmax(logits, dim=-1)

    def get_action(self, state, deterministic=False):
        """Sample action from policy"""
        logits = self.forward(state)
        dist = Categorical(logits=logits)

        if deterministic:
            action = torch.argmax(logits, dim=-1)
        else:
            action = dist.sample()

        log_prob = dist.log_prob(action)
        return action, log_prob


class CMORLAgent:
    """
    Constrained Multi-Objective Reinforcement Learning Agent
    Implements PPO with preference-based scalarization
    """

    def __init__(self,
                 state_dim: int,
                 action_dim: int,
                 preference_vector: np.ndarray,
                 learning_rate: float = 3e-4,
                 gamma: float = 0.99,
                 gae_lambda: float = 0.95,
                 clip_epsilon: float = 0.2,
                 value_coef: float = 0.5,
                 entropy_coef: float = 0.01,
                 device: str = 'cpu'):
        """
        Initialize C-MORL agent

        Args:
            state_dim: State space dimensionality (137 with DC types)
            action_dim: Action space size (5)
            preference_vector: [w_energy, w_carbon, w_latency] weights
            learning_rate: Learning rate for optimizers
            gamma: Discount factor
            gae_lambda: GAE lambda parameter
            clip_epsilon: PPO clipping parameter
            value_coef: Value loss coefficient
            entropy_coef: Entropy bonus coefficient
            device: 'cpu' or 'cuda'
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.preference_vector = torch.FloatTensor(preference_vector).to(device)
        self.device = device

        # Hyperparameters
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef

        # Networks
        self.policy = PolicyNetwork(state_dim, action_dim).to(device)
        self.value_net = MultiObjectiveValueNetwork(state_dim).to(device)

        # Optimizers
        self.policy_optimizer = torch.optim.Adam(self.policy.parameters(), lr=learning_rate)
        self.value_optimizer = torch.optim.Adam(self.value_net.parameters(), lr=learning_rate)

        # Training statistics
        self.training_steps = 0

        logger.info(f"Initialized C-MORL agent with preference {preference_vector}")

    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float]:
        """
        Select action from policy

        Args:
            state: Environment state (127-dim)
            deterministic: If True, select best action

        Returns:
            action: Selected action (0-4)
            log_prob: Log probability of action
        """
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            action, log_prob = self.policy.get_action(state_tensor, deterministic)
            return action.item(), log_prob.item()

    def evaluate_actions(self, states, actions):
        """
        Evaluate actions for PPO update

        Returns:
            log_probs: Log probabilities of actions
            values: Scalarized value estimates
            entropy: Policy entropy
        """
        # Get action log probabilities
        logits = self.policy(states)
        dist = Categorical(logits=logits)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy().mean()

        # Get multi-objective values
        values_dict = self.value_net(states)

        # Scalarize values using preference vector
        values = (self.preference_vector[0] * values_dict['v_energy'] +
                 self.preference_vector[1] * values_dict['v_carbon'] +
                 self.preference_vector[2] * values_dict['v_latency'])

        return log_probs, values, entropy, values_dict

    def compute_gae(self, rewards_dict: Dict[str, List[float]],
                    values_dict: Dict[str, List[float]],
                    dones: List[bool]) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        """
        Compute Generalized Advantage Estimation for multi-objective rewards

        Args:
            rewards_dict: Dict with keys 'R_energy', 'R_carbon', 'R_latency'
            values_dict: Dict with value estimates for each objective
            dones: Episode termination flags

        Returns:
            advantages: Scalarized advantages
            returns_dict: Returns for each objective
        """
        # Compute returns and advantages for each objective
        returns_dict = {}
        advantages_dict = {}

        for obj_name in ['R_energy', 'R_carbon', 'R_latency']:
            rewards = torch.FloatTensor(rewards_dict[obj_name]).to(self.device)
            values = torch.FloatTensor(values_dict[obj_name]).to(self.device)
            dones_tensor = torch.FloatTensor(dones).to(self.device)

            # GAE computation
            advantages = torch.zeros_like(rewards)
            returns = torch.zeros_like(rewards)

            gae = 0
            next_value = 0  # Assuming episodes end at terminal state

            for t in reversed(range(len(rewards))):
                if t == len(rewards) - 1:
                    next_value = 0
                    next_non_terminal = 1.0 - dones_tensor[t]
                else:
                    next_value = values[t + 1]
                    next_non_terminal = 1.0 - dones_tensor[t]

                delta = rewards[t] + self.gamma * next_value * next_non_terminal - values[t]
                gae = delta + self.gamma * self.gae_lambda * next_non_terminal * gae
                advantages[t] = gae
                returns[t] = advantages[t] + values[t]

            returns_dict[obj_name] = returns
            advantages_dict[obj_name] = advantages

        # Scalarize advantages using preference vector
        scalarized_advantages = (
            self.preference_vector[0] * advantages_dict['R_energy'] +
            self.preference_vector[1] * advantages_dict['R_carbon'] +
            self.preference_vector[2] * advantages_dict['R_latency']
        )

        return scalarized_advantages, returns_dict

    def update(self, states, actions, old_log_probs, rewards_dict, dones,
               epochs: int = 10, batch_size: int = 64):
        """
        PPO update step

        Args:
            states: Batch of states
            actions: Batch of actions
            old_log_probs: Log probs from old policy
            rewards_dict: Dict of reward lists
            dones: Done flags
            epochs: Number of optimization epochs
            batch_size: Minibatch size
        """
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        old_log_probs = torch.FloatTensor(old_log_probs).to(self.device)

        # Get initial value estimates
        with torch.no_grad():
            values_dict_initial = self.value_net(states)
            values_dict_np = {
                'R_energy': values_dict_initial['v_energy'].cpu().numpy().tolist(),
                'R_carbon': values_dict_initial['v_carbon'].cpu().numpy().tolist(),
                'R_latency': values_dict_initial['v_latency'].cpu().numpy().tolist()
            }

        # Compute advantages and returns
        advantages, returns_dict = self.compute_gae(rewards_dict, values_dict_np, dones)

        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        # PPO update for multiple epochs
        dataset_size = len(states)
        indices = np.arange(dataset_size)

        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        num_updates = 0

        for epoch in range(epochs):
            np.random.shuffle(indices)

            for start in range(0, dataset_size, batch_size):
                end = start + batch_size
                batch_indices = indices[start:end]

                # Get batch
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages[batch_indices]

                # Evaluate actions
                log_probs, values, entropy, values_dict = self.evaluate_actions(
                    batch_states, batch_actions
                )

                # Policy loss (PPO clip objective)
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * batch_advantages
                policy_loss = -torch.min(surr1, surr2).mean()

                # Value loss (separate for each objective)
                value_loss = 0
                for obj_name in ['R_energy', 'R_carbon', 'R_latency']:
                    obj_key = 'v_energy' if obj_name == 'R_energy' else ('v_carbon' if obj_name == 'R_carbon' else 'v_latency')
                    batch_returns = returns_dict[obj_name][batch_indices]
                    value_loss += F.mse_loss(values_dict[obj_key], batch_returns)

                value_loss = value_loss / 3.0  # Average over objectives

                # Total loss
                loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy

                # Update
                self.policy_optimizer.zero_grad()
                self.value_optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.policy.parameters(), max_norm=0.5)
                torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), max_norm=0.5)
                self.policy_optimizer.step()
                self.value_optimizer.step()

                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy += entropy.item()
                num_updates += 1

        self.training_steps += 1

        return {
            'policy_loss': total_policy_loss / num_updates,
            'value_loss': total_value_loss / num_updates,
            'entropy': total_entropy / num_updates
        }

    def save(self, path: str):
        """Save agent checkpoint"""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'value_net_state_dict': self.value_net.state_dict(),
            'policy_optimizer_state_dict': self.policy_optimizer.state_dict(),
            'value_optimizer_state_dict': self.value_optimizer.state_dict(),
            'preference_vector': self.preference_vector.cpu().numpy(),
            'training_steps': self.training_steps
        }, path)
        logger.info(f"Saved agent to {path}")

    def load(self, path: str):
        """Load agent checkpoint"""
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.value_net.load_state_dict(checkpoint['value_net_state_dict'])
        self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer_state_dict'])
        self.value_optimizer.load_state_dict(checkpoint['value_optimizer_state_dict'])
        self.preference_vector = torch.FloatTensor(checkpoint['preference_vector']).to(self.device)
        self.training_steps = checkpoint['training_steps']
        logger.info(f"Loaded agent from {path}")


if __name__ == "__main__":
    # Test agent creation
    print("="*80)
    print("C-MORL AGENT TEST")
    print("="*80)

    agent = CMORLAgent(
        state_dim=137,
        action_dim=5,
        preference_vector=np.array([0.5, 0.3, 0.2])  # Energy, Carbon, Latency
    )

    # Test action selection
    test_state = np.random.randn(137)
    action, log_prob = agent.select_action(test_state)

    print(f"\n✓ Agent created with preference [0.5, 0.3, 0.2]")
    print(f"✓ Test action selection: action={action}, log_prob={log_prob:.3f}")

    # Test save/load
    agent.save("/tmp/test_agent.pt")
    agent.load("/tmp/test_agent.pt")
    print(f"✓ Save/load test passed")

    print("\n" + "="*80)
    print("✓ AGENT TEST COMPLETED")
    print("="*80)
