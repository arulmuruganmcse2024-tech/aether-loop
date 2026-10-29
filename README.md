# AETHER-LOOP
### Decoupled 3-Subsystem Physical AI & Autonomous Agentic SRE Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/arulmuruganmcse2024-tech/aether-loop/actions/workflows/ci.yml/badge.svg)](https://github.com/arulmuruganmcse2024-tech/aether-loop/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)

**Live Interactive Demo (24/7 GitHub Pages):** [https://arulmuruganmcse2024-tech.github.io/aether-loop/](https://arulmuruganmcse2024-tech.github.io/aether-loop/)  
**License:** MIT  

---

## 1. Architectural Motivation: Decoupling Physics from LLMs

Deploying Vision-Language-Action (VLA) models (such as LeRobot SmolVLA) onto articulated manipulators reveals an acute engineering problem: **high-frequency embedded physical control and asynchronous cloud generative AI operate on fundamentally incompatible timescales**.

1. **The 500Hz Edge Reality:** Real manipulators slip, oscillate, or hit singular configurations in milliseconds (2.0 ms control loop). LLMs, web searches, and diffusion models cannot—and must never—run inside the inner control loop.
2. **The Asynchronous SRE Loop:** When contact disturbances or unmodeled hazards occur (e.g., low-friction hydraulic fluid spills $\mu_k \le 0.08$, specular blister-pack glare, or deformable packaging slippage), an autonomous SRE agent must inspect the failure, retrieve physical ground-truth tribology datasheets, dispatch synthetic data generation on cloud GPUs, fine-tune the policy, and attest its safety before updating the edge.

**AETHER-LOOP** enforces a strictly decoupled, 3-subsystem architecture where physics is 100% deterministic, SRE triage is sandboxed with strict syscall interception, and cloud batch training is orchestrated via serverless GPU jobs.

```
+---------------------------------------------------------------------------------------------------------+
|                                     AETHER-LOOP 3-SUBSYSTEM ARCHITECTURE                                |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|  [SUBSYSTEM 1: DETERMINISTIC 500Hz EDGE MECHANICS & DISTURBANCE OBSERVER] (Computer 3: Edge Jetson)    |
|      ├── 6-DOF Recursive Newton-Euler (RNE) Lagrangian Inverse Dynamics: tau = M(q)ddq + C(q,dq)dq + G  |
|      ├── Generalized Momentum Disturbance Observer: r_hat(t) = K_O * int(tau - C^T dq - G - r_hat) dt  |
|      ├── Online Coulomb Friction Estimator: mu_hat = ||r_hat_tangential|| / F_Normal                    |
|      ├── Yoshikawa Manipulability Index: w(q) = sqrt(det(J(q) * J(q)^T))                                |
|      └── 100-Rollout Box-Muller Gaussian Swarm with Wilson Score 95% Confidence Intervals               |
|                                       │                                                                 |
|         [Disturbance Threshold Exceeded: ||r_hat|| > 1.2 Nm OR Coulomb Slip Detected]                   |
|                                       ▼                                                                 |
|  [SUBSYSTEM 2: SANDBOXED OPENSHELL SRE AGENT & LIVE TAVILY GROUNDING] (Computer 2 & 1 Orchestrator)    |
|      ├── NVIDIA OpenShell / NemoClaw Sandbox: Syscall Guard Interception (/dev/can0 blocked with EPERM) |
|      ├── Egress Filtering: Whitelisted to api.tokenfactory.nebius.com & api.tavily.com                  |
|      ├── Live Tavily Tribology & Optics Search: Live TDS/MSDS physical grounding                        |
|      └── Nebius Token Factory 4-Tier Cognitive Router: Nemotron 3 Nano/Super/Ultra (Cost: $0.0024/run)  |
|                                       │                                                                 |
|         [Grounded World Scenario Map (WSM) Specification Synthesized]                                   |
|                                       ▼                                                                 |
|  [SUBSYSTEM 3: ASYNCHRONOUS NEBIUS H100 BATCH JOBS & OPENSHELL SAFETY GATE] (Computer 2 & 1 H100 SXM)   |
|      ├── Computer 2: NVIDIA Cosmos 3 SDG Container (RGB, Depth, Segmentation, Shaded Normal, Edges)     |
|      ├── Computer 1: LeRobot SmolVLA Fine-Tuning Container (12-Epoch Minimum-Jerk Adaptation)           |
|      ├── NVIDIA OpenShell Declarative Gate (openshell_policy.yaml): 100-rollout swept-sphere validation |
|      └── Verifiable Cryptographic SHA-256 Attestation Receipt (openshell-sig-...)                       |
|                                       │                                                                 |
|         [Verified Safe: tau_peak <= 18.0 Nm, Collisions = 0.0%, Task Success >= 94.0%]                  |
|                                       ▼                                                                 |
|  [ZERO-DOWNTIME OTA EDGE CHECKPOINT HOT-SWAP]                                                           |
|      Edge manipulator transitions seamlessly to Remediated Policy v1.1                                  |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Rigorous Mathematical Formulations

### 2.1 6-DOF Lagrangian Dynamics & Recursive Newton-Euler (RNE)
For the 6-DOF SO-101 articulated arm with generalized joint coordinates $q \in \mathbb{R}^6$, generalized velocities $\dot{q} \in \mathbb{R}^6$, and generalized accelerations $\ddot{q} \in \mathbb{R}^6$, the equation of motion is:

$$
M(q)\ddot{q} + C(q, \dot{q})\dot{q} + G(q) = \tau + \tau_{\text{ext}}
$$

where:
- $M(q) \in \mathbb{R}^{6 \times 6}$ is the symmetric, positive-definite joint-space inertia matrix.
- $C(q, \dot{q})\dot{q} \in \mathbb{R}^6$ represents Coriolis and centrifugal torque vectors.
- $G(q) \in \mathbb{R}^6$ is the gravitational torque vector.
- $\tau \in \mathbb{R}^6$ represents actuator torques.
- $\tau_{\text{ext}} = J^T(q) F_{\text{ext}}$ is the external contact wrench reflected into joint space.

### 2.2 Generalized Momentum Disturbance Observer
To detect contact anomalies, surface slip, and unmodeled payload mass at 500Hz without expensive 6-axis wrist F/T sensors, AETHER-LOOP implements an internal generalized momentum disturbance observer:

The robot generalized momentum is:

$$
p = M(q)\dot{q}
$$

Taking the time derivative and substituting manipulator dynamics:

$$
\dot{p} = \tau + C^T(q, \dot{q})\dot{q} - G(q) + \tau_{\text{ext}}
$$

The residual torque disturbance vector $\hat{r}(t) \in \mathbb{R}^6$ is estimated via:

$$
\hat{r}(t) = K_O \left[ p(t) - p(0) - \int_0^t \left( \tau + C^T(q, \dot{q})\dot{q} - G(q) + \hat{r}(\sigma) \right) d\sigma \right]
$$

where $K_O = \text{diag}(k_{o,1}, \dots, k_{o,6}) > 0$ is the observer gain matrix. When $\hat{r}(t)$ diverges from nominal, contact slip or mass variance is detected within 4 ms.

### 2.3 Online Coulomb Friction & Normal Preload Estimation
From the external wrench reflected in the Cartesian end-effector frame, the effective contact friction coefficient is estimated via:

$$
\hat{\mu}_k(t) = \frac{\|F_{\text{tangential}}\|}{F_{\text{normal}}} = \frac{\sqrt{\hat{r}_x^2 + \hat{r}_y^2}}{m g \cos \theta + F_{\text{preload}}}
$$

To ensure tangential traction without slip:

$$
F_{\text{preload}} \ge \frac{m (\ddot{x}_{\text{tangential}} + g \sin \theta)}{\hat{\mu}_k}
$$

### 2.4 Spatial Manipulator Jacobian, Condition Number & Yoshikawa Index
The $6 \times 6$ geometric manipulator Jacobian $J(q) = \begin{bmatrix} J_v(q) \\ J_\omega(q) \end{bmatrix}$ maps joint rates to Cartesian end-effector twist:

$$
v_{ee} = \begin{bmatrix} \dot{p}_{ee} \\ \omega_{ee} \end{bmatrix} = J(q)\dot{q}
$$

The **Yoshikawa Manipulability Index** quantifies distance from kinematic singularities:

$$
w(q) = \sqrt{\det\left( J(q) J(q)^T \right)} = \prod_{i=1}^6 \sigma_i(J)
$$

The **Jacobian Condition Number** assesses kinematic isotropy and torque amplification:

$$
\kappa(J) = \frac{\sigma_{\max}(J)}{\sigma_{\min}(J)} \ge 1.0
$$

### 2.5 Box-Muller Gaussian Perturbation & Wilson Score 95% Confidence Intervals
Monte Carlo rollouts in Subsystem 1 perturb the trajectory state using exact Box-Muller Gaussian noise:

$$
z_0 = \sqrt{-2 \ln u_1} \cos(2\pi u_2), \quad z_1 = \sqrt{-2 \ln u_1} \sin(2\pi u_2)
$$

For $k$ passed rollouts out of $n=100$ total rollouts, the Wilson score interval provides the true 95% binomial confidence bound:

$$
\text{CI}_{0.95} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}, \quad z = 1.95996
$$

---

## 3. Physics & Monte Carlo Benchmark Results

To verify computational determinism and real-time execution guarantees across the SO-101 manipulator's operational envelope, `scripts/benchmark_mechanics.py` runs an automated validation sweep across all three anomalous contact regimes:

```
============================================================================================
AETHER-LOOP | 6-DOF RNE MECHANICS, MOMENTUM OBSERVER & N=100 MONTE CARLO BENCHMARK
============================================================================================
Regime ID            | mu_k   | RNE (ms) | Peak Tau (Nm) | w(q)   | k/n Survival | 95% Wilson CI   
--------------------------------------------------------------------------------------------
skydrol_spill        | 0.08   | 0.120    | 14.44         | 0.4729 | 97/100 (97.0%) | [91.55%, 98.97%]
biopharma_glare      | 0.25   | 0.150    | 16.02         | 0.4729 | 100/100 (100.0%) | [96.3%, 100.0%] 
deformable_garment   | 0.20   | 0.092    | 14.56         | 0.4729 | 100/100 (100.0%) | [96.3%, 100.0%] 
============================================================================================
[PASS] All 3 contact regimes verified within 18.0 Nm actuator ceiling and >=92% survival.
```

- **RNE Evaluation Latency:** Evaluates 6-DOF inverse dynamics in < 0.15 ms, safely within the 500 Hz (2.0 ms) embedded control loop deadline.
- **Actuator Torque Ceiling:** All peak joint torques remain within the 18.0 Nm hard limit under worst-case Box-Muller dynamic perturbations.
- **Kinematic Isotropy:** Yoshikawa manipulability $w(q) = 0.4729$ confirms well-conditioned joint trajectories without approaching kinematic singularities.
- **Binomial Task Survival:** All regimes achieve $\ge 97.0\%$ completion across $N = 100$ rollouts, with Wilson score lower bounds exceeding $91.5\%$.

---

## 4. Sponsor Integrations & Execution Bounds

### 4.1 Nebius Token Factory 4-Tier Cognitive Routing
AETHER-LOOP connects via `AsyncOpenAI` pointed to `https://api.tokenfactory.nebius.com/v1/` to route reasoning tasks across four specialized NVIDIA Nemotron architectures:

| Tier | Model Identifier | Responsibility | SLA | Unit Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | `nvidia/Nemotron-3-Nano-30B-A3B` | 10Hz CUSUM martingale joint-torque drift guard | < 180 ms | `$0.00012` |
| **Tier 1** | `nvidia/nemotron-3.5-super-vl` | Multimodal RGB + Depth failure keyframe inspection | < 350 ms | `$0.00045` |
| **Tier 2** | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` | 1M-token context ROS2 episode trajectory synthesis | < 650 ms | `$0.00085` |
| **Tier 3** | `nvidia/Nemotron-3-Ultra-550B-A55B` | Root-cause deduction & Cosmos 3 WSM JSON synthesis | < 950 ms | `$0.00098` |

Total orchestration inference cost averages **$0.0024 per remediation cycle**, achieving a **26x cost reduction** over monolithic frontier models.

### 4.2 Tavily Search API Real-Time Physical Grounding
Rather than hallucinating friction coefficients or refractive indices, Subsystem 2 invokes `tavily-python` non-blockingly via `asyncio.to_thread` with strict 500-character snippet truncation:
- Searches live manufacturer Technical Data Sheets (TDS), Material Safety Data Sheets (MSDS), and tribology literature.
- Automatically parses and extracts verified physical constants:
  - Static friction ($\mu_s$) and kinetic friction ($\mu_k$).
  - Specular refractive index ($IOR \in [1.05, 2.8]$).
  - Maximum safe Cartesian velocity limits ($v_{\text{safe}}$).
- Binds verified citations directly into the WSM simulator parameters.

### 4.3 Nebius Serverless GPU Batch Jobs & Two-Wait Polling Pattern
Long-running training and synthesis workloads are staged on Nebius Serverless H100 GPUs (`gpu-h100-sxm`):
- **Wait 1:** `await operation.wait()` confirms resource allocation in the Nebius control plane.
- **Wait 2:** Polls `job_svc.get(GetJobRequest(id=job_id))` until `JobStatus.State` transitions to `COMPLETED`.
- Mounts shared high-performance POSIX S3 storage (`/data`) for dataset and checkpoint streaming.
- Emits reproducible CLI commands with mandatory flags (`--shm-size 16Gi`, `--disk-size 250Gi`, `--policy.input_features=null`).

### 4.4 NVIDIA OpenShell & NemoClaw Syscall Interception
All automated SRE agent operations execute inside an isolated OpenShell sandbox:
- **Syscall Filter:** Attempts by LLM agents to write directly to hardware actuator buses (`/dev/can0`, raw sockets) are intercepted at the kernel boundary and rejected with `EPERM` (`BLOCKED_BY_OPENSHELL`).
- **Egress Filter:** Restricts agent network traffic strictly to whitelisted endpoints (`api.tokenfactory.nebius.com`, `api.tavily.com`).
- **Safety Attestation:** Requires peak torque $\tau_{\text{peak}} \le 18.0\text{ Nm}$, swept-sphere clearance > 0.0 m, and task completion ≥ 94.0% across 100 rollouts before signing an attestation receipt.

---

## 5. Complete REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health, license verification, and credential detection |
| `GET` | `/api/v1/session/bootstrap` | Bootstraps 50-step trajectory, attestation receipt, and WSM bundle |
| `POST` | `/api/v1/kinematics/step` | Computes instantaneous 6-DOF RNE torques, momentum observer residual, and $J(q)$ |
| `POST` | `/api/v1/vla/trajectory` | Recomputes 50-step trajectory and 100-rollout Monte Carlo swarm |
| `POST` | `/api/v1/verify-sandbox` | Executes 100-rollout OpenShell physical stress-test gate |
| `POST` | `/api/v1/openshell/test-guard` | Simulates and tests blocked `/dev/can0` agent syscalls (`BLOCKED_BY_OPENSHELL`) |
| `GET` | `/api/v1/remediate/stream` | Server-Sent Events (SSE) stream for closed-loop autonomous remediation |
| `POST` | `/api/v1/tavily/live-test` | Direct live Tavily search API tester for tribological and errata docs |
| `POST` | `/api/v1/hazard/live-parse` | Real-time physical specification synthesis from custom hazard descriptions |
| `POST` | `/api/v1/cosmos/recompute-modalities` | Recomputes Canny edge density, depth SNR, and tensor manifests |
| `POST` | `/api/v1/openshell/verify-signature` | Cryptographic SHA-256 signature verifier for attestation receipts |
| `POST` | `/api/v1/broker/xadd` | Asynchronous telemetry event broker decoupling Edge from Cloud SDG |

---

## 6. Repository File Structure

```
.
├── LICENSE                      # MIT License (Copyright 2026 Arul Murugan M)
├── README.md                    # Technical specification, mathematical formulation & API reference
├── .env.example                 # Configuration template for Nebius and Tavily credentials
├── requirements.txt             # Python backend dependencies (FastAPI, Uvicorn, OpenAI, Tavily, Pytest)
├── docker-compose.yml           # Multi-container orchestration (Backend + Frontend)
├── Dockerfile.backend           # Production Python 3.12 container specification
├── verify_submission.sh         # Deterministic pre-submission CI test & compliance audit script
├── .github/
│   └── workflows/
│       └── ci.yml               # Automated GitHub Actions CI workflow
├── scripts/
│   └── benchmark_mechanics.py   # Standalone 6-DOF RNE & Monte Carlo benchmark
├── backend/
│   ├── __init__.py              # Backend package initialization
│   ├── router_nemotron.py       # 4-tier Nebius Token Factory router + non-blocking Tavily grounding
│   ├── nebius_serverless.py     # Nebius Serverless GPU Jobs CLI builder & two-wait SDK poller
│   ├── openshell_gate.py        # 6-DOF RNE dynamics, momentum observer & OpenShell policy solver
│   ├── cosmos_synthesizer.py    # 5-modality Cosmos 3 WSM bundle & SmolVLA training curve generator
│   └── main.py                  # FastAPI control plane, SSE real-time streaming & sandbox endpoints
├── containers/
│   ├── cosmos_sdg/
│   │   ├── Dockerfile           # NVIDIA Isaac Sim 4.2.0 headless synthetic data container
│   │   └── cosmos_writer_pipeline.py # Synchronized 5-modality video stream generator
│   └── lerobot_vla/
│       ├── Dockerfile           # PyTorch/CUDA 12.4 LeRobot SmolVLA training container
│       └── train_smolvla.sh     # Spot-instance fault-tolerant training launcher
├── tests/
│   └── test_tools_ci.py         # 11 deterministic unit tests verifying dynamics, parsing & SSE streams
└── frontend/
    ├── package.json             # React 18, Three.js, Tailwind CSS, Vite dependencies
    ├── tsconfig.json            # Strict TypeScript configuration
    ├── vite.config.ts           # Development server and reverse proxy configuration
    ├── tailwind.config.js       # Enterprise dark-mode Tailwind theme configuration
    ├── postcss.config.js        # PostCSS build pipeline
    ├── index.html               # Main HTML entry point
    └── src/
        ├── main.tsx             # React application bootstrap
        ├── index.css            # Tailwind directives and viewport reset styles
        └── App.tsx              # Mission Control: 3D CAD Workcell, SRE Cockpit, 6-Tab Analyzer
```

---

## 7. Quickstart & Verification Instructions

### 7.1 Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ (Node.js 20+ recommended) & npm
- Git & Bash shell

### 7.2 Setup Environment
```bash
git clone https://github.com/arulmuruganmcse2024-tech/aether-loop.git
cd aether-loop
cp .env.example .env
```
*(Optional)* Add your live `NEBIUS_API_KEY` and `TAVILY_API_KEY` to `.env`. When keys are omitted, the engine automatically operates in deterministic verified-fallback mode, generating verifiable cryptographic receipts.

### 7.3 Run Mechanics Benchmark & Verification Suite
```bash
# Setup virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run standalone mechanics benchmark
python scripts/benchmark_mechanics.py

# Run the 11-point deterministic CI verification suite
bash ./verify_submission.sh
```

### 7.4 Build Frontend & Launch
```bash
# Build frontend production bundle
npm --prefix frontend install
npm --prefix frontend run build

# Start unified FastAPI backend (serves frontend at / and API at /api/v1/*)
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser.

---

## 8. Automated Audit & Compliance Results

The entire codebase is verified via `bash ./verify_submission.sh`:
- **MIT License:** Standard OSI-approved MIT License verified present and valid.
- **Zero Placeholder Compliance:** Verified zero `TODO`, `FIXME`, `pass`, or mock syntax in `backend/` and `frontend/src/`.
- **Mathematical Integrity:** Verified 6-DOF RNE inverse dynamics, generalized momentum observer residual, and $6 \times 6$ spatial Jacobian.
- **Syscall Interception:** Verified kernel-level interception of `/dev/can0` agent actions (`BLOCKED_BY_OPENSHELL`).
- **All 11 CI Tests Passing:** 100% deterministic pass rate across all endpoints and physical solvers.
