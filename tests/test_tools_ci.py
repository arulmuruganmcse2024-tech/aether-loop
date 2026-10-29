import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from backend.router_nemotron import DynamicNemotronRouter, extract_first_json_object
from backend.nebius_serverless import (
    build_cosmos3_sdg_cli_command,
    build_lerobot_smolvla_cli_command,
    execute_and_poll_nebius_job,
)
from backend.openshell_gate import verify_policy_in_openshell_sandbox

client = TestClient(app)


def test_extract_first_json_object_handles_think_tags_and_multiple_braces():
    raw_llm_output = (
        "<think>\nLet's calculate the friction of {Skydrol} on epoxy.\n</think>\n"
        "Here is the grounded physics configuration:\n"
        "```json\n"
        "{\n"
        '  "static_friction_mu_s": 0.12,\n'
        '  "kinetic_friction_mu_k": 0.08,\n'
        '  "optical_specular_ior": 1.478,\n'
        "}\n"
        "```\n"
        "Note: apply this to {Computer 2} in the pipeline."
    )
    parsed = extract_first_json_object(raw_llm_output)
    assert parsed["static_friction_mu_s"] == 0.12
    assert parsed["kinetic_friction_mu_k"] == 0.08
    assert parsed["optical_specular_ior"] == 1.478


def test_nebius_serverless_cli_commands_contain_mandatory_flags():
    cosmos_cmd = build_cosmos3_sdg_cli_command("bucket-123", "subnet-456", "skydrol_spill")
    assert "--shm-size 16Gi" in cosmos_cmd
    assert "--disk-size 250Gi" in cosmos_cmd
    assert "bucket-123:/data:rw" in cosmos_cmd

    smolvla_cmd = build_lerobot_smolvla_cli_command("bucket-123", "subnet-456", "skydrol_spill")
    assert "--policy.input_features=null" in smolvla_cmd
    assert "--policy.output_features=null" in smolvla_cmd
    assert "--preemptible" in smolvla_cmd
    assert "--follows-spot-price" in smolvla_cmd


def test_openshell_newton_euler_physics_verifier_computes_real_dynamics():
    receipt = verify_policy_in_openshell_sandbox(
        anomaly_id="skydrol_spill",
        checkpoint_path="/data/checkpoints/smolvla_v1.1.pt",
        max_safe_velocity=0.22,
        kinetic_friction_mu_k=0.08,
        payload_mass_kg=1.40,
        num_rollouts=100,
    )
    assert receipt.evaluated_rollouts == 100
    assert 0.0 < receipt.max_observed_torque_nm <= 18.0
    assert receipt.collision_rate_pct == 0.0
    assert receipt.task_completion_rate_pct >= 94.0
    assert receipt.attestation_status == "VERIFIED_SAFE_FOR_EDGE_DEPLOYMENT"
    assert len(receipt.per_joint_peak_torque_nm) == 6
    assert len(receipt.rollout_swarm) == 100
    assert len(receipt.spatial_jacobian_6x6) == 6
    assert receipt.wilson_95_ci_lower_pct >= 91.0
    assert "baseline_v1_0" in receipt.synthesized_code_diff


def test_4_tier_router_and_two_wait_poller_end_to_end():
    async def _run():
        router = DynamicNemotronRouter()
        events = []
        async for ev in router.orchestrate_4_tier_remediation("skydrol_spill"):
            events.append(ev)
        assert len(events) == 5
        assert events[-1]["stage"] == "TIER_3_ULTRA_WSM_SPEC"

        job_res = await execute_and_poll_nebius_job(
            job_name="test-cosmos-job",
            stage="COMPUTER_2_COSMOS_SDG",
            image="cr.eu-north1.nebius.cloud/aether-loop/cosmos3-sdg:v1.1",
            container_command="python3",
            args="-m cosmos_writer_pipeline",
            cli_command="nebius ai job create ...",
            expected_artifacts=["/data/sdg/rgb.mp4", "/data/sdg/edges.mp4"],
        )
        assert job_res.wait_1_resource_created is True
        assert "COMPLETED" in job_res.wait_2_container_state

    asyncio.run(_run())


def test_fastapi_endpoints_and_sse_stream():
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["author"] == "Arul Murugan M"

    sandbox = client.post(
        "/api/v1/verify-sandbox",
        json={
            "anomaly_id": "biopharma_glare",
            "max_safe_velocity": 0.30,
            "kinetic_friction_mu_k": 0.25,
            "payload_mass_kg": 0.85,
        },
    )
    assert sandbox.status_code == 200
    assert sandbox.json()["attestation_status"] == "VERIFIED_SAFE_FOR_EDGE_DEPLOYMENT"


def test_runtime_credentials_and_tavily_test_endpoints():
    keys_res = client.post(
        "/api/v1/config/keys",
        json={"nebius_api_key": "test-neb-key", "tavily_api_key": "tvly-test"},
    )
    assert keys_res.status_code == 200
    assert keys_res.json()["status"] == "updated"

    tav_res = client.post(
        "/api/v1/tavily/live-test",
        json={"query": "Skydrol friction coefficient", "anomaly_id": "skydrol_spill"},
    )
    assert tav_res.status_code == 200
    assert len(tav_res.json()["citations"]) > 0

    client.post("/api/v1/config/keys", json={"nebius_api_key": "", "tavily_api_key": ""})


def test_custom_hazard_tavily_snippet_physics_synthesis():
    from backend.router_nemotron import synthesize_physics_from_tavily_evidence, FALLBACK_PHYSICS_SPECS

    base = FALLBACK_PHYSICS_SPECS["skydrol_spill"]
    spec = synthesize_physics_from_tavily_evidence(
        anomaly_id="skydrol_spill",
        description="PTFE Teflon grease on 2.4kg steel valve",
        citations=[{"title": "PTFE Tribology", "url": "https://example.com", "snippet": "kinetic friction coefficient 0.05 and refractive index 1.38"}],
        base_spec=base,
        request_id="test-req-123",
    )
    assert spec.kinetic_friction_mu_k == 0.05
    assert spec.optical_specular_ior == 1.38
    assert spec.payload_mass_kg == 2.4


def test_bootstrap_kinematic_step_cosmos_modalities_and_signature_verifier():
    boot = client.get("/api/v1/session/bootstrap?anomaly_id=skydrol_spill")
    assert boot.status_code == 200
    b_data = boot.json()
    assert "session_nonce" in b_data
    assert len(b_data["vla_trajectory"]["policy_v1_1_steps"]) == 50
    assert "openshell_policy_yaml" in b_data["attestation"]
    assert "sha256_manifest_digest" in b_data["attestation"]
    assert "yoshikawa_manipulability" in b_data["attestation"]
    assert len(b_data["attestation"]["openshell_agent_audit_log"]) >= 4

    step = client.post(
        "/api/v1/kinematics/step",
        json={"timestamp_sec": 1.42, "payload_mass_kg": 1.4, "kinetic_friction_mu_k": 0.08, "max_safe_velocity": 0.22},
    )
    assert step.status_code == 200
    assert len(step.json()["joint_torques_nm"]) == 6
    assert "momentum_observer_residual_nm" in step.json()
    assert "estimated_contact_mu_hat" in step.json()
    assert "yoshikawa_manipulability_index" in step.json()

    mods = client.post(
        "/api/v1/cosmos/recompute-modalities",
        json={"anomaly_id": "skydrol_spill", "canny_low": 40, "canny_high": 125, "optical_specular_ior": 1.478, "kinetic_friction_mu_k": 0.08},
    )
    assert mods.status_code == 200
    assert mods.json()["edge_pixel_density_pct"] > 0.0

    sig_check = client.post(
        "/api/v1/openshell/verify-signature",
        json={
            "canonical_payload_json": b_data["attestation"]["canonical_payload_json"],
            "expected_signature": b_data["attestation"]["sha256_manifest_digest"],
        },
    )
    assert sig_check.status_code == 200
    assert sig_check.json()["verified"] is True


def test_live_reactive_hazard_parse_endpoint():
    res = client.post(
        "/api/v1/hazard/live-parse",
        json={"anomaly_id": "skydrol_spill", "custom_text": "Cryogenic ice frost layer on 2.8kg glass vial"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["physics_spec"]["kinetic_friction_mu_k"] == 0.03
    assert data["physics_spec"]["payload_mass_kg"] == 2.8
    assert "step_nonce" in data


def test_composite_cryogenic_petrolatum_mixture_and_gaussian_variance():
    res = client.post(
        "/api/v1/hazard/live-parse",
        json={
            "anomaly_id": "skydrol_spill",
            "custom_text": "Melted petroleum jelly mixed with liquid nitrogen on a 2.1kg titanium valve",
        },
    )
    assert res.status_code == 200
    data = res.json()
    spec = data["physics_spec"]
    att = data["attestation"]
    assert spec["surface_temperature_kelvin"] < 100.0
    assert 0.02 <= spec["kinetic_friction_mu_k"] <= 0.15
    assert att["torque_std_dev_nm"] > 0.0
    assert "passed_rollouts_k" in att
    assert "broker_event" in data
    assert data["broker_event"]["ack_status"] == "XACK_COMMITTED"




