#!/usr/bin/env python3
"""NEXUS POC 7 Demo: Spiking Neural Network (SNN) Temporal Reasoner.

Demonstrates:
1. Event-driven encoding of multi-observation illumination sequences into spike trains
2. Leaky Integrate-and-Fire (LIF) neuromorphic neuron dynamics
3. Evaluating temporal stability, shadow flickering, and persistent darkness states
4. Calculating neuromorphic edge compute power savings (~90%+ reduction vs continuous ANN)
5. Exporting temporal state vectors for habitat life-support planning
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc7_snn_temporal import (
    SNNTemporalReasoner,
    generate_synthetic_observation_sequence,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 7: SPIKING NEURAL NETWORK (SNN) TEMPORAL REASONER")
    print("=" * 72)

    reasoner = SNNTemporalReasoner(num_neurons=16, time_steps=24, seed=42)

    # 1. Synthesize multi-observation time series (24 epochs across lunar synodic cycle)
    print("\n[*] Generating Multi-Observation Temporal Sequences across 24 Epochs...")
    series_plateau = generate_synthetic_observation_sequence(site_type="plateau", num_steps=24)
    series_floor = generate_synthetic_observation_sequence(site_type="crater_floor", num_steps=24)
    series_flicker = generate_synthetic_observation_sequence(site_type="flicker_rim", num_steps=24)

    # 2. Process through LIF Spiking Network
    print("\n[*] Executing Leaky Integrate-and-Fire (LIF) Neuromorphic Temporal Dynamics...")
    prof_plateau = reasoner.process_site_temporal_series("site_01_north_plateau", series_plateau)
    prof_floor = reasoner.process_site_temporal_series("site_02_basin_floor", series_floor)
    prof_flicker = reasoner.process_site_temporal_series("site_03_rim_wall", series_flicker)

    profiles = [prof_plateau, prof_floor, prof_flicker]

    for p in profiles:
        print(f"\n    [{p.site_id.upper()}]")
        print(f"      • Total Spikes Emitted:     {p.total_spikes_emitted} spikes")
        print(f"      • Mean Firing Rate:         {p.mean_firing_rate:.3f} spikes/neuron/step")
        print(f"      • Temporal Stability Index: {p.temporal_stability_index:.2f} / 1.00")
        print(f"      • Sudden Shadow Events:     {p.sudden_shadow_transitions}")
        print(f"      • Neuromorphic Power Proxy: {p.neuromorphic_power_proxy_mw:.3f} mW (vs ~250 mW for Dense GPU)")
        print(f"      • Temporal State Verdict:   {p.state_classification}")

    # 3. Export Artifacts
    out_dir = Path("outputs/nexus_snn")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "snn_temporal_reasoning_report.json"

    data_out = {
        "model_architecture": "Leaky Integrate-and-Fire (LIF) Spiking Neural Network",
        "neuron_count": reasoner.num_neurons,
        "temporal_steps": 24,
        "site_evaluations": [p.to_dict() for p in profiles],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=2)

    print(f"\n[✓] SNN Temporal Reasoning Report: {report_path}")
    print("=" * 72)
    print(" NEXUS POC 7 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
