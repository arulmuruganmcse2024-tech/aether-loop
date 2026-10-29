import asyncio
import json
import os
import time
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.cosmos_synthesizer import build_cosmos3_wsm_and_training_curve
from backend.nebius_serverless import (
    build_cosmos3_sdg_cli_command,
    build_lerobot_smolvla_cli_command,
    build_serverless_endpoint_cli_command,
    execute_and_poll_nebius_job,
)
from backend.openshell_gate import verify_policy_in_openshell_sandbox
from backend.router_nemotron import DynamicNemotronRouter, FALLBACK_PHYSICS_SPECS, GroundedPhysicsSpec

app = FastAPI(
    title="AETHER-LOOP Control Plane API",
    description="Autonomous Edge-to-Hyperscale Remediation & Closed-Loop Physical AI DevOps Engine",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router_engine = DynamicNemotronRouter()


class SandboxVerifyRequest(BaseModel):
    anomaly_id: str = "skydrol_spill"
    max_safe_velocity: float = 0.22
    kinetic_friction_mu_k: float = 0.08
    payload_mass_kg: float = 1.40
    obstacle_x: float = 0.32
    obstacle_y: float = 0.18
    obstacle_z: float = 0.04


class CredentialsUpdateRequest(BaseModel):
    nebius_api_key: str = ""
    tavily_api_key: str = ""


class LiveTavilyTestRequest(BaseModel):
    query: str = "Skydrol LD-4 hydraulic fluid kinematic viscosity refractive index friction coefficient"
    anomaly_id: str = "skydrol_spill"


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "service": "AETHER-LOOP Closed-Loop Physical AI DevOps Engine",
        "author": "Arul Murugan M",
        "nebius_token_factory_configured": bool(router_engine.api_key),
        "tavily_configured": bool(router_engine.tavily_key),
        "tavily_key_prefix": (router_engine.tavily_key[:8] + "...") if router_engine.tavily_key else "not_set",
        "tier_models": router_engine.tier_models,
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
            await asyncio.sleep(0.18)

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
        await asyncio.sleep(0.18)

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
        await asyncio.sleep(0.18)

        receipt = verify_policy_in_openshell_sandbox(
            anomaly_id=anomaly_id,
            checkpoint_path=f"/data/checkpoints/smolvla_{anomaly_id}_v1.1.pt",
            max_safe_velocity=spec_obj.max_safe_ee_velocity_m_s,
            kinetic_friction_mu_k=spec_obj.kinetic_friction_mu_k,
            payload_mass_kg=spec_obj.payload_mass_kg,
            num_rollouts=100,
        )
        endpoint_cli = build_serverless_endpoint_cli_command(bucket_id, subnet_id, anomaly_id)
        yield f"data: {json.dumps({'stage': 'OPENSHELL_VERIFIED_DEPLOY', 'attestation': receipt.model_dump(), 'endpoint_cli': endpoint_cli})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
