"""NEXUS POC 7: Spiking Neural Network (SNN) Temporal Reasoner.

Event-driven neuromorphic reasoning over multi-temporal lunar observations:
- Event-based spike encoding (change detection & thresholded illumination fluxes)
- Leaky Integrate-and-Fire (LIF) neuromorphic neuron dynamics
- Spatio-temporal state embeddings across multi-observation time series
- Power-efficient edge inference proxy for lunar lander / rover compute
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TemporalSNNProfile:
    """Quantitative neuromorphic spatio-temporal state for a localized lunar site."""
    site_id: str
    total_spikes_emitted: int
    mean_firing_rate: float
    temporal_stability_index: float
    sudden_shadow_transitions: int
    neuromorphic_power_proxy_mw: float
    state_classification: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "total_spikes": self.total_spikes_emitted,
            "firing_rate": round(self.mean_firing_rate, 3),
            "temporal_stability": round(self.temporal_stability_index, 2),
            "shadow_transition_events": self.sudden_shadow_transitions,
            "neuromorphic_power_mw": round(self.neuromorphic_power_proxy_mw, 3),
            "classification": self.state_classification,
        }


class LIFNeuronLayer:
    """Vectorized Leaky Integrate-and-Fire (LIF) spiking neuron layer."""

    def __init__(
        self,
        num_neurons: int,
        decay_beta: float = 0.85,
        threshold: float = 1.0,
        v_reset: float = 0.0,
    ):
        self.num_neurons = num_neurons
        self.beta = float(decay_beta)
        self.threshold = float(threshold)
        self.v_reset = float(v_reset)
        self.v_membrane = np.full(num_neurons, v_reset, dtype=np.float64)

    def reset(self) -> None:
        """Resets membrane potential to initial baseline."""
        self.v_membrane.fill(self.v_reset)

    def step(self, input_current: np.ndarray) -> np.ndarray:
        """Executes one discrete simulation time-step.

        Args:
            input_current: 1D array of synaptic input currents (num_neurons,).

        Returns:
            spikes: Boolean array where True indicates action potential fired.
        """
        # Integrate & leak: V(t) = beta * V(t-1) + I(t)
        self.v_membrane = self.beta * self.v_membrane + input_current

        # Fire threshold condition
        spikes = self.v_membrane >= self.threshold

        # Reset membrane potential for firing neurons
        self.v_membrane[spikes] = self.v_reset
        return spikes


class SNNTemporalReasoner:
    """Processes time-series observations into spatio-temporal spike representations."""

    def __init__(self, num_neurons: int = 16, time_steps: int = 24, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.num_neurons = num_neurons
        self.time_steps = time_steps
        self.lif_layer = LIFNeuronLayer(num_neurons=num_neurons, decay_beta=0.82, threshold=1.0)
        # Synaptic weights projecting scalar observation to neuron inputs
        self.weights = self.rng.uniform(0.6, 1.4, size=num_neurons)

    def encode_to_event_spikes(
        self,
        time_series: np.ndarray,
        change_threshold: float = 0.10,
    ) -> Tuple[np.ndarray, int]:
        """Encodes temporal illumination signals into event-based spike trains.

        Emits spikes when significant illumination changes occur (e.g. shadow edge transit).
        """
        t_len = len(time_series)
        spike_train = np.zeros((t_len, self.num_neurons), dtype=np.float64)

        # Baseline change detection
        deltas = np.diff(time_series, prepend=time_series[0])
        transitions = int(np.sum(np.abs(deltas) >= change_threshold))

        for t in range(t_len):
            intensity = time_series[t]
            delta = abs(deltas[t])

            # Current driven by intensity and rate of change
            curr = (intensity * 0.7 + delta * 1.5) * self.weights
            spike_train[t] = curr

        return spike_train, transitions

    def process_site_temporal_series(
        self,
        site_id: str,
        temporal_illumination: np.ndarray,
    ) -> TemporalSNNProfile:
        """Runs the LIF network on a site's multi-observation illumination sequence."""
        self.lif_layer.reset()
        t_len = len(temporal_illumination)

        input_currents, transition_events = self.encode_to_event_spikes(temporal_illumination)

        spikes_history = []
        for t in range(t_len):
            fired = self.lif_layer.step(input_currents[t])
            spikes_history.append(fired)

        spikes_arr = np.array(spikes_history)  # shape (T, num_neurons)
        total_spikes = int(np.sum(spikes_arr))
        mean_firing_rate = float(total_spikes / (t_len * self.num_neurons))

        # Temporal stability: Low variation in firing rate = highly predictable illumination
        rates_per_step = np.mean(spikes_arr, axis=1)
        stability = float(np.clip(1.0 - np.std(rates_per_step), 0.0, 1.0))

        # Power calculation proxy (neuromorphic chips consume ~10-20 pJ per spike)
        # Power in mW = (total_spikes * 15 pJ) / (T * 1 ms)
        power_proxy_mw = float(total_spikes * 0.015)

        if stability >= 0.70 and mean_firing_rate > 0.35:
            verdict = "STABLE_CONTINUOUS_ILLUMINATION"
        elif transition_events > 4:
            verdict = "HIGH_FREQUENCY_SHADOW_FLICKER"
        elif mean_firing_rate < 0.1:
            verdict = "PERSISTENT_DARKNESS_STATE"
        else:
            verdict = "MODERATE_DIURNAL_CYCLING"

        return TemporalSNNProfile(
            site_id=site_id,
            total_spikes_emitted=total_spikes,
            mean_firing_rate=mean_firing_rate,
            temporal_stability_index=stability,
            sudden_shadow_transitions=transition_events,
            neuromorphic_power_proxy_mw=power_proxy_mw,
            state_classification=verdict,
        )


# -----------------------------------------------------------------------------
# Synthetic Multi-Observation Time Series Generator
# -----------------------------------------------------------------------------
def generate_synthetic_observation_sequence(
    site_type: str = "plateau",
    num_steps: int = 24,
    seed: int = 42,
) -> np.ndarray:
    """Generates synthetic time series across 24 observation epochs:

    - 'plateau': Continuous high sunlight with minor penumbral dips
    - 'crater_floor': Extended deep shadow with brief low-angle flare
    - 'flicker_rim': Rapid sharp shadow-light transitions due to moving crater rim obstructions
    """
    rng = np.random.default_rng(seed)
    time = np.linspace(0, 2 * np.pi, num_steps)

    if site_type == "plateau":
        # High sunlight baseline (0.7 - 0.95)
        curve = 0.8 + 0.15 * np.sin(time)
    elif site_type == "crater_floor":
        # Darkness most of the time
        curve = np.clip(0.15 * np.sin(time) - 0.05, 0.0, 0.2)
    elif site_type == "flicker_rim":
        # Step transitions
        curve = np.where(np.sin(time * 3) > 0, 0.85, 0.05)
    else:
        curve = 0.5 + 0.3 * np.sin(time)

    # Add minor noise
    noise = rng.normal(0.0, 0.02, size=num_steps)
    return np.clip(curve + noise, 0.0, 1.0)
