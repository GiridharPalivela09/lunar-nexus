"""Tests for NEXUS POC 7: Spiking Neural Network (SNN) Temporal Reasoner."""

import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc7_snn_temporal import (
    LIFNeuronLayer,
    SNNTemporalReasoner,
    TemporalSNNProfile,
    generate_synthetic_observation_sequence,
)


def test_lif_neuron_layer_dynamics():
    """Verify Leaky Integrate-and-Fire membrane potential integration, spiking, and reset."""
    layer = LIFNeuronLayer(num_neurons=4, decay_beta=0.8, threshold=1.0, v_reset=0.0)

    # Sub-threshold input: should not fire
    sub_current = np.array([0.4, 0.4, 0.4, 0.4])
    spikes1 = layer.step(sub_current)
    assert not np.any(spikes1)
    assert np.allclose(layer.v_membrane, 0.4)

    # Second step with additional current: V = 0.8*0.4 + 0.8 = 1.12 >= 1.0 -> should fire
    supra_current = np.array([0.8, 0.8, 0.8, 0.8])
    spikes2 = layer.step(supra_current)
    assert np.all(spikes2)
    # Fired neurons must be reset to v_reset (0.0)
    assert np.allclose(layer.v_membrane, 0.0)


def test_event_spike_encoding():
    """Verify that sharp illumination transitions trigger event change spikes."""
    reasoner = SNNTemporalReasoner(num_neurons=8, time_steps=10)

    # Step function signal: 0.0 to 1.0
    series = np.array([0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    spike_train, transitions = reasoner.encode_to_event_spikes(series, change_threshold=0.2)

    assert spike_train.shape == (6, 8)
    assert transitions >= 1  # 0.0 -> 1.0 detected as sudden transition


def test_snn_site_temporal_reasoning_comparisons():
    """Verify SNN distinguishes stable plateau illumination from flickering shadow rims and dark floors."""
    reasoner = SNNTemporalReasoner(num_neurons=16, time_steps=24, seed=42)

    plateau_series = generate_synthetic_observation_sequence(site_type="plateau", num_steps=24)
    floor_series = generate_synthetic_observation_sequence(site_type="crater_floor", num_steps=24)
    flicker_series = generate_synthetic_observation_sequence(site_type="flicker_rim", num_steps=24)

    prof_plateau = reasoner.process_site_temporal_series("site_plateau", plateau_series)
    prof_floor = reasoner.process_site_temporal_series("site_floor", floor_series)
    prof_flicker = reasoner.process_site_temporal_series("site_flicker", flicker_series)

    assert isinstance(prof_plateau, TemporalSNNProfile)
    # Plateau has continuous solar input -> higher firing rate than dark floor
    assert prof_plateau.mean_firing_rate > prof_floor.mean_firing_rate
    # Flicker rim experiences multiple sharp transitions
    assert prof_flicker.sudden_shadow_transitions > prof_plateau.sudden_shadow_transitions
    # Plateau should exhibit high temporal stability
    assert prof_plateau.temporal_stability_index >= 0.5
    # Power consumption proxy must be non-negative
    assert prof_plateau.neuromorphic_power_proxy_mw > 0.0
