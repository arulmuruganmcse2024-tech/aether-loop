import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.openshell_gate import (
    evaluate_instantaneous_6dof_state,
    verify_policy_in_openshell_sandbox,
)
from backend.router_nemotron import FALLBACK_PHYSICS_SPECS


def run_benchmark() -> None:
    print("=" * 92)
    print("AETHER-LOOP | 6-DOF RNE MECHANICS, MOMENTUM OBSERVER & N=100 MONTE CARLO BENCHMARK")
    print("=" * 92)
    header = f"{'Regime ID':<20} | {'mu_k':<6} | {'RNE (ms)':<8} | {'Peak Tau (Nm)':<13} | {'w(q)':<6} | {'k/n Survival':<12} | {'95% Wilson CI':<16}"
    print(header)
    print("-" * 92)

    q_test = [0.32, -0.45, -0.62, 0.22, 0.14, 0.08]
    dq_test = [0.18, -0.22, 0.25, 0.12, 0.08, 0.04]
    ddq_test = [-0.42, 0.55, -0.48, 0.22, 0.15, 0.08]

    for key, spec in FALLBACK_PHYSICS_SPECS.items():
        t0 = time.perf_counter()
        step_diag = evaluate_instantaneous_6dof_state(
            q=q_test,
            dq=dq_test,
            ddq=ddq_test,
            payload_mass_kg=spec.payload_mass_kg,
            kinetic_friction_mu_k=spec.kinetic_friction_mu_k,
            max_ee_velocity_m_s=spec.max_safe_ee_velocity_m_s,
            timestamp_sec=1.24,
        )
        rne_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        receipt = verify_policy_in_openshell_sandbox(
            anomaly_id=key,
            checkpoint_path=f"/data/checkpoints/smolvla_{key}_v1.1.pt",
            max_safe_velocity=spec.max_safe_ee_velocity_m_s,
            kinetic_friction_mu_k=spec.kinetic_friction_mu_k,
            payload_mass_kg=spec.payload_mass_kg,
            num_rollouts=100,
        )
        ci_str = f"[{receipt.wilson_95_ci_lower_pct}%, {receipt.wilson_95_ci_upper_pct}%]"
        surv_str = f"{receipt.passed_rollouts_k}/100 ({receipt.task_completion_rate_pct}%)"
        print(
            f"{key:<20} | {spec.kinetic_friction_mu_k:<6.2f} | {rne_ms:<8.3f} | "
            f"{receipt.max_observed_torque_nm:<13.2f} | {step_diag.yoshikawa_manipulability_index:<6.4f} | "
            f"{surv_str:<12} | {ci_str:<16}"
        )
        assert receipt.max_observed_torque_nm <= 18.0, f"Torque limit exceeded on {key}"
        assert receipt.passed_rollouts_k >= 92, f"Survival below threshold on {key}"

    print("=" * 92)
    print("[PASS] All 3 contact regimes verified within 18.0 Nm actuator ceiling and >=92% survival.")


if __name__ == "__main__":
    run_benchmark()

