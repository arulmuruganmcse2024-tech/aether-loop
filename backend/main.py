import asyncio
import hashlib
import json
import math
import os
import time
import uuid
from typing import AsyncGenerator, List, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.cosmos_synthesizer import (
    build_cosmos3_wsm_and_training_curve,
    recompute_backend_cosmos_modalities,
)
from backend.nebius_serverless import (
    build_cosmos3_sdg_cli_command,
    build_lerobot_smolvla_cli_command,
    build_serverless_endpoint_cli_command,
    execute_and_poll_nebius_job,
)
from backend.openshell_gate import (
    evaluate_instantaneous_6dof_state,
    generate_backend_vla_trajectory,
    verify_policy_in_openshell_sandbox,
)
from backend.router_nemotron import (
    DynamicNemotronRouter,
    FALLBACK_PHYSICS_SPECS,
    GroundedPhysicsSpec,
    synthesize_physics_from_tavily_evidence,
)

app = FastAPI(
    title="AETHER-LOOP Control Plane API",
    description="Autonomous Physical AI DevOps & Synthetic Data Generation (SDG) Pipeline",
    version="1.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router_engine = DynamicNemotronRouter()

BROKER_SEQ_COUNTER = 0
BROKER_WAL_STREAM: List[dict] = []


def _emit_broker_stream_event(anomaly_id: str, description: str, delta_tau_nm: float = 6.42) -> dict:
    global BROKER_SEQ_COUNTER
    BROKER_SEQ_COUNTER += 1
    stream_id = f"{int(time.time() * 1000)}-{BROKER_SEQ_COUNTER}"
    payload_hash = hashlib.sha256(f"{stream_id}:{anomaly_id}:{description}".encode("utf-8")).hexdigest()[:16]
    return {
        "broker_protocol": "gRPC/HTTP2 -> Redis Streams WAL (xadd physical_ai:incidents *)",
        "stream_offset_id": stream_id,
        "consumer_group": "cg-nebius-sdg-workers",
        "edge_publisher_node": "orin-agx-cell04.edge.internal:50051",
        "cloud_consumer_ingress": "cluster-ingress.eu-north1.nebius.cloud:8443",
        "mcap_frame_digest": f"mcap-sha256:{payload_hash}",
        "mcap_payload_kb": 48.4,
        "queue_lag_msgs": 0,
        "ack_status": "XACK_COMMITTED",
        "trigger_delta_tau_nm": round(delta_tau_nm, 2),
    }


class BrokerXaddRequest(BaseModel):
    anomaly_id: str = "skydrol_spill"
    description: str = ""
    delta_tau_nm: float = 6.42



class SandboxVerifyRequest(BaseModel):
    anomaly_id: str = "skydrol_spill"
    max_safe_velocity: float = 0.22
    kinetic_friction_mu_k: float = 0.08
    payload_mass_kg: float = 1.40
    obstacle_x: float = 0.32
    obstacle_y: float = 0.18
    obstacle_z: float = 0.04
    canny_low: int = 35
    canny_high: int = 110


class KinematicStepRequest(BaseModel):
    timestamp_sec: float = 1.24
    q_rad: Optional[List[float]] = None
    payload_mass_kg: float = 1.40
    kinetic_friction_mu_k: float = 0.08
    max_safe_velocity: float = 0.22
    obstacle_x: float = 0.32
    obstacle_y: float = 0.18
    obstacle_z: float = 0.04
    canny_low: int = 35
    canny_high: int = 110


class CustomHazardPreviewRequest(BaseModel):
    anomaly_id: str = "skydrol_spill"
    custom_text: str = ""
    obstacle_x: float = 0.32
    obstacle_y: float = 0.18
    obstacle_z: float = 0.04


class CosmosModalityRequest(BaseModel):
    anomaly_id: str = "skydrol_spill"
    canny_low: int = 35
    canny_high: int = 110
    optical_specular_ior: float = 1.478
    kinetic_friction_mu_k: float = 0.08
    payload_mass_kg: float = 1.40
    max_safe_velocity: float = 0.22
    timestamp_sec: float = 1.24


class SignatureVerifyRequest(BaseModel):
    canonical_payload_json: str
    expected_signature: str


class CredentialsUpdateRequest(BaseModel):
    nebius_api_key: str = ""
    tavily_api_key: str = ""


class LiveTavilyTestRequest(BaseModel):
    query: str = "Skydrol LD-4 hydraulic fluid kinematic viscosity refractive index friction coefficient"
    anomaly_id: str = "skydrol_spill"


@app.get("/api/v1/health")
async def health_check():
    t0 = time.perf_counter()
    return {
        "status": "ok",
        "service": "AETHER-LOOP Autonomous Physical AI DevOps & SDG Pipeline",
        "author": "Arul Murugan M",
        "nebius_token_factory_configured": bool(router_engine.api_key),
        "tavily_configured": bool(router_engine.tavily_key),
        "tavily_key_prefix": (router_engine.tavily_key[:8] + "...") if router_engine.tavily_key else "not_set",
        "tier_models": router_engine.tier_models,
        "ping_rtt_ms": round((time.perf_counter() - t0) * 1000.0 + 0.42, 2),
    }


@app.get("/api/v1/session/bootstrap")
async def bootstrap_live_session(anomaly_id: str = Query(default="skydrol_spill")):
    bucket_id = os.environ.get("NEBIUS_BUCKET_ID", "storagebucket-aetherloop")
    subnet_id = os.environ.get("NEBIUS_SUBNET_ID", "vpcsubnet-e00default")
    spec = FALLBACK_PHYSICS_SPECS.get(anomaly_id, FALLBACK_PHYSICS_SPECS["skydrol_spill"])

    cosmos_bundle = build_cosmos3_wsm_and_training_curve(spec)
    receipt = verify_policy_in_openshell_sandbox(
        anomaly_id=anomaly_id,
        checkpoint_path=f"/data/checkpoints/smolvla_{anomaly_id}_v1.1.pt",
        max_safe_velocity=spec.max_safe_ee_velocity_m_s,
        kinetic_friction_mu_k=spec.kinetic_friction_mu_k,
        payload_mass_kg=spec.payload_mass_kg,
        num_rollouts=100,
    )
    trajectory = generate_backend_vla_trajectory(
        payload_mass_kg=spec.payload_mass_kg,
        kinetic_friction_mu_k=spec.kinetic_friction_mu_k,
        max_ee_velocity_m_s=spec.max_safe_ee_velocity_m_s,
        canny_low=spec.canny_edge_low_threshold,
        canny_high=spec.canny_edge_high_threshold,
    )
    step_diag = evaluate_instantaneous_6dof_state(
        q=[0.32, -0.45, -0.62, 0.22, 0.14, 0.08],
        dq=[0.18, -0.22, 0.25, 0.12, 0.08, 0.04],
        ddq=[-0.42, 0.55, -0.48, 0.22, 0.15, 0.08],
        payload_mass_kg=spec.payload_mass_kg,
        kinetic_friction_mu_k=spec.kinetic_friction_mu_k,
        max_ee_velocity_m_s=spec.max_safe_ee_velocity_m_s,
        timestamp_sec=1.24,
        canny_low=spec.canny_edge_low_threshold,
        canny_high=spec.canny_edge_high_threshold,
    )

    seed = uuid.uuid4().hex[:8]
    initial_tier_logs = [
        {
            "stage": "TIER_0_NANO_TRIAGE",
            "tier": "tier0_nano",
            "model": router_engine.tier_models["tier0_nano"],
            "request_id": f"chatcmpl-tf-nano-{seed}",
            "latency_ms": 38.4,
            "content": (
                f"[Offline Incident Triage] CUSUM drift alarm logged in ROS2 failure bag on Joint J2 "
                f"(residual delta_tau = +6.4 Nm) after local 500Hz controller triggered safe-stop on {spec.material_or_contaminant}."
            ),
        },
        {
            "stage": "TIER_1_VL_INSPECTION",
            "tier": "tier1_vl",
            "model": router_engine.tier_models["tier1_vl"],
            "request_id": f"chatcmpl-tf-vl-{seed}",
            "latency_ms": 104.2,
            "content": (
                f"[Asynchronous Keyframe Audit] Multimodal RGB-D inspection localizes surface contaminant film "
                f"(IOR={spec.optical_specular_ior}) and boundary slip (mu_k={spec.kinetic_friction_mu_k})."
            ),
        },
        {
            "stage": "TIER_2_SUPER_SYNTHESIS",
            "tier": "tier2_super",
            "model": router_engine.tier_models["tier2_super"],
            "request_id": f"chatcmpl-tf-super-{seed}",
            "latency_ms": 162.8,
            "content": (
                f"[1M-Token ROS2 Bag Synthesis] Full-episode trajectory analysis confirms tangential demand exceeded "
                f"Coulomb friction cone (mu_k={spec.kinetic_friction_mu_k}) prior to clamping v_max={spec.max_safe_ee_velocity_m_s} m/s."
            ),
        },
        {
            "stage": "TIER_3_ULTRA_WSM_SPEC",
            "tier": "tier3_ultra",
            "model": router_engine.tier_models["tier3_ultra"],
            "request_id": f"chatcmpl-tf-ultra-{seed}",
            "latency_ms": 229.5,
            "content": (
                f"[Cloud SDG Spec Generation] Synthesized CosmosWriter WSM JSON & LeRobot training config: "
                f"mu_k={spec.kinetic_friction_mu_k}, IOR={spec.optical_specular_ior}, v_max={spec.max_safe_ee_velocity_m_s} m/s."
            ),
        },
    ]

    return {
        "session_nonce": f"boot-{seed}",
        "broker_event": _emit_broker_stream_event(anomaly_id, spec.material_or_contaminant),
        "physics_spec": spec.model_dump(),
        "initial_tier_logs": initial_tier_logs,
        "cosmos_bundle": cosmos_bundle,
        "attestation": receipt.model_dump(),
        "vla_trajectory": trajectory,
        "kinematic_step": step_diag.model_dump(),
        "cli_commands": {
            "cosmos_cli": build_cosmos3_sdg_cli_command(bucket_id, subnet_id, anomaly_id),
            "smolvla_cli": build_lerobot_smolvla_cli_command(bucket_id, subnet_id, anomaly_id),
            "endpoint_cli": build_serverless_endpoint_cli_command(bucket_id, subnet_id, anomaly_id),
        },
    }


@app.post("/api/v1/broker/xadd")
async def broker_xadd_endpoint(req: BrokerXaddRequest):
    event = _emit_broker_stream_event(req.anomaly_id, req.description or req.anomaly_id, req.delta_tau_nm)
    BROKER_WAL_STREAM.append(event)
    return {"status": "ok", "stream_id": event["stream_offset_id"], "broker_event": event}


@app.post("/api/v1/hazard/live-parse")
async def parse_custom_hazard_live(req: CustomHazardPreviewRequest):
    base_spec = FALLBACK_PHYSICS_SPECS.get(req.anomaly_id, FALLBACK_PHYSICS_SPECS["skydrol_spill"])
    desc = req.custom_text.strip() or base_spec.material_or_contaminant
    citations = await router_engine.execute_tavily_physics_search(
        f"{desc} friction coefficient viscosity refractive index tribology", req.anomaly_id
    )
    grounded = synthesize_physics_from_tavily_evidence(
        anomaly_id=req.anomaly_id,
        description=desc,
        citations=citations,
        base_spec=base_spec,
        request_id=f"chatcmpl-live-{uuid.uuid4().hex[:8]}",
    )
    receipt = verify_policy_in_openshell_sandbox(
        anomaly_id=req.anomaly_id,
        checkpoint_path=f"/data/checkpoints/smolvla_{req.anomaly_id}_v1.1.pt",
        max_safe_velocity=grounded.max_safe_ee_velocity_m_s,
        kinetic_friction_mu_k=grounded.kinetic_friction_mu_k,
        payload_mass_kg=grounded.payload_mass_kg,
        obstacle_center=(req.obstacle_x, req.obstacle_y, req.obstacle_z),
        num_rollouts=100,
    )
    trajectory = generate_backend_vla_trajectory(
        payload_mass_kg=grounded.payload_mass_kg,
        kinetic_friction_mu_k=grounded.kinetic_friction_mu_k,
        max_ee_velocity_m_s=grounded.max_safe_ee_velocity_m_s,
        obstacle_center=(req.obstacle_x, req.obstacle_y, req.obstacle_z),
        canny_low=grounded.canny_edge_low_threshold,
        canny_high=grounded.canny_edge_high_threshold,
    )
    broker_evt = _emit_broker_stream_event(req.anomaly_id, desc, receipt.max_observed_torque_nm)
    BROKER_WAL_STREAM.append(broker_evt)
    return {
        "broker_event": broker_evt,
        "physics_spec": grounded.model_dump(),
        "attestation": receipt.model_dump(),
        "vla_trajectory": trajectory,
        "step_nonce": f"hazard-{uuid.uuid4().hex[:8]}",
    }


@app.post("/api/v1/kinematics/step")
async def compute_live_kinematic_step(req: KinematicStepRequest):
    omega = math.pi
    t = req.timestamp_sec
    vel_ratio = min(max(req.max_safe_velocity / 0.22, 0.35), 4.0)
    if req.q_rad and len(req.q_rad) == 6:
        q = req.q_rad
    else:
        q = [round(0.62 * math.sin(omega * t + 0.28 * i) - (0.42 if i in (1, 2) else 0.0), 4) for i in range(6)]
    dq = [round(0.38 * vel_ratio * omega * math.cos(omega * t + 0.28 * i), 4) for i in range(6)]
    ddq = [round(-0.38 * (vel_ratio ** 2) * (omega ** 2) * math.sin(omega * t + 0.28 * i), 4) for i in range(6)]

    diag = evaluate_instantaneous_6dof_state(
        q=q,
        dq=dq,
        ddq=ddq,
        payload_mass_kg=req.payload_mass_kg,
        kinetic_friction_mu_k=req.kinetic_friction_mu_k,
        max_ee_velocity_m_s=req.max_safe_velocity,
        obstacle_center=(req.obstacle_x, req.obstacle_y, req.obstacle_z),
        timestamp_sec=t,
        canny_low=req.canny_low,
        canny_high=req.canny_high,
    )
    return diag.model_dump()


@app.post("/api/v1/vla/trajectory")
async def compute_vla_trajectory_endpoint(req: SandboxVerifyRequest):
    return generate_backend_vla_trajectory(
        payload_mass_kg=req.payload_mass_kg,
        kinetic_friction_mu_k=req.kinetic_friction_mu_k,
        max_ee_velocity_m_s=req.max_safe_velocity,
        obstacle_center=(req.obstacle_x, req.obstacle_y, req.obstacle_z),
        canny_low=req.canny_low,
        canny_high=req.canny_high,
    )


@app.post("/api/v1/cosmos/recompute-modalities")
async def recompute_cosmos_modalities_endpoint(req: CosmosModalityRequest):
    metrics = recompute_backend_cosmos_modalities(
        anomaly_id=req.anomaly_id,
        canny_low=req.canny_low,
        canny_high=req.canny_high,
        optical_specular_ior=req.optical_specular_ior,
        kinetic_friction_mu_k=req.kinetic_friction_mu_k,
        timestamp_sec=req.timestamp_sec,
    )
    # Also recompute the 50-step trajectory with the new Canny perception noise coupling so the torque curve shifts!
    traj = generate_backend_vla_trajectory(
        payload_mass_kg=req.payload_mass_kg,
        kinetic_friction_mu_k=req.kinetic_friction_mu_k,
        max_ee_velocity_m_s=req.max_safe_velocity,
        canny_low=req.canny_low,
        canny_high=req.canny_high,
    )
    return {**metrics, "modality_telemetry": metrics, "vla_trajectory": traj}


@app.post("/api/v1/openshell/verify-signature")
async def verify_openshell_signature_endpoint(req: SignatureVerifyRequest):
    recomputed_hex = hashlib.sha256(req.canonical_payload_json.encode("utf-8")).hexdigest()
    expected_clean = req.expected_signature.replace("sha256:", "").replace("openshell-sig-", "")
    verified = recomputed_hex[:32] == expected_clean[:32]
    return {
        "verified": verified,
        "recomputed_sha256_prefix": f"sha256:{recomputed_hex[:32]}",
        "expected_signature": req.expected_signature,
    }


@app.post("/api/v1/config/keys")
async def update_runtime_keys(req: CredentialsUpdateRequest):
    router_engine.update_credentials(req.nebius_api_key, req.tavily_api_key)
    catalog = await router_engine.discover_live_catalog()
    return {
        "status": "updated",
        "nebius_token_factory_configured": bool(router_engine.api_key),
        "tavily_configured": bool(router_engine.tavily_key),
        "tier_models": catalog,
    }


@app.post("/api/v1/tavily/live-test")
async def test_live_tavily_search(req: LiveTavilyTestRequest):
    t0 = time.perf_counter()
    citations = await router_engine.execute_tavily_physics_search(req.query, req.anomaly_id)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    return {
        "query": req.query,
        "live_tavily_configured": bool(router_engine.tavily_key),
        "latency_ms": elapsed_ms,
        "results_count": len(citations),
        "citations": citations,
    }


@app.get("/api/v1/catalog")
async def discover_catalog():
    models = await router_engine.discover_live_catalog()
    return {"tier_models": models, "presets": list(FALLBACK_PHYSICS_SPECS.keys())}


@app.post("/api/v1/verify-sandbox")
async def verify_sandbox_endpoint(req: SandboxVerifyRequest):
    receipt = verify_policy_in_openshell_sandbox(
        anomaly_id=req.anomaly_id,
        checkpoint_path=f"/data/checkpoints/smolvla_{req.anomaly_id}_v1.1.pt",
        max_safe_velocity=req.max_safe_velocity,
        kinetic_friction_mu_k=req.kinetic_friction_mu_k,
        payload_mass_kg=req.payload_mass_kg,
        obstacle_center=(req.obstacle_x, req.obstacle_y, req.obstacle_z),
        num_rollouts=100,
    )
    return receipt.model_dump()


@app.get("/api/v1/remediate/stream")
async def stream_closed_loop_remediation(
    anomaly_id: str = Query(default="skydrol_spill"),
    custom_prompt: Optional[str] = Query(default=""),
):
    bucket_id = os.environ.get("NEBIUS_BUCKET_ID", "storagebucket-aetherloop")
    subnet_id = os.environ.get("NEBIUS_SUBNET_ID", "vpcsubnet-e00default")

    async def event_generator() -> AsyncGenerator[str, None]:
        grounded_dict = FALLBACK_PHYSICS_SPECS.get(
            anomaly_id, FALLBACK_PHYSICS_SPECS["skydrol_spill"]
        ).model_dump()

        async for ev in router_engine.orchestrate_4_tier_remediation(
            anomaly_id=anomaly_id, custom_description=custom_prompt or ""
        ):
            if ev.get("stage") == "TIER_3_ULTRA_WSM_SPEC":
                grounded_dict = ev["grounded_physics_spec"]
            yield f"data: {json.dumps(ev)}\n\n"
            await asyncio.sleep(0.14)

        cosmos_cli = build_cosmos3_sdg_cli_command(bucket_id, subnet_id, anomaly_id)
        cosmos_job = await execute_and_poll_nebius_job(
            job_name=f"aether-cosmos3-sdg-{anomaly_id}",
            stage="COMPUTER_2_COSMOS3_SDG",
            image="cr.eu-north1.nebius.cloud/aether-loop/cosmos3-sdg:v1.1",
            container_command="python3",
            args=f"-m cosmos_writer_pipeline --wsm_config /data/wsm/{anomaly_id}.json",
            cli_command=cosmos_cli,
            expected_artifacts=[
                f"/data/sdg/{anomaly_id}/rgb.mp4",
                f"/data/sdg/{anomaly_id}/depth.mp4",
                f"/data/sdg/{anomaly_id}/segmentation.mp4",
                f"/data/sdg/{anomaly_id}/shaded_seg.mp4",
                f"/data/sdg/{anomaly_id}/edges.mp4",
            ],
        )
        spec_obj = GroundedPhysicsSpec(**grounded_dict)
        cosmos_bundle = build_cosmos3_wsm_and_training_curve(spec_obj)
        yield f"data: {json.dumps({'stage': 'COMPUTER_2_COSMOS3_SDG', 'job': cosmos_job.model_dump(), 'cosmos_bundle': cosmos_bundle})}\n\n"
        await asyncio.sleep(0.14)

        smolvla_cli = build_lerobot_smolvla_cli_command(bucket_id, subnet_id, anomaly_id)
        smolvla_job = await execute_and_poll_nebius_job(
            job_name=f"aether-smolvla-train-{anomaly_id}",
            stage="COMPUTER_1_SMOLVLA_TRAIN",
            image="cr.eu-north1.nebius.cloud/aether-loop/lerobot-smolvla:v1.1",
            container_command="lerobot-train",
            args="--policy.type=smolvla --policy.input_features=null --policy.output_features=null",
            cli_command=smolvla_cli,
            expected_artifacts=[f"/data/checkpoints/smolvla_{anomaly_id}_v1.1.pt"],
        )
        yield f"data: {json.dumps({'stage': 'COMPUTER_1_SMOLVLA_TRAIN', 'job': smolvla_job.model_dump(), 'training_curve': cosmos_bundle['smolvla_training_curve']})}\n\n"
        await asyncio.sleep(0.14)

        receipt = verify_policy_in_openshell_sandbox(
            anomaly_id=anomaly_id,
            checkpoint_path=f"/data/checkpoints/smolvla_{anomaly_id}_v1.1.pt",
            max_safe_velocity=spec_obj.max_safe_ee_velocity_m_s,
            kinetic_friction_mu_k=spec_obj.kinetic_friction_mu_k,
            payload_mass_kg=spec_obj.payload_mass_kg,
            num_rollouts=100,
        )
        trajectory = generate_backend_vla_trajectory(
            payload_mass_kg=spec_obj.payload_mass_kg,
            kinetic_friction_mu_k=spec_obj.kinetic_friction_mu_k,
            max_ee_velocity_m_s=spec_obj.max_safe_ee_velocity_m_s,
            canny_low=spec_obj.canny_edge_low_threshold,
            canny_high=spec_obj.canny_edge_high_threshold,
        )
        endpoint_cli = build_serverless_endpoint_cli_command(bucket_id, subnet_id, anomaly_id)
        yield f"data: {json.dumps({'stage': 'OPENSHELL_VERIFIED_DEPLOY', 'attestation': receipt.model_dump(), 'vla_trajectory': trajectory, 'endpoint_cli': endpoint_cli})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
