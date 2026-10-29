import json
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

REPO_OWNER = "arulmuruganmcse2024-tech"
REPO_NAME = "aether-loop"
PAGES_URL = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/"
DESCRIPTION = "Decoupled 6-DOF Recursive Newton-Euler Mechanics Observer, OpenShell Sandboxed SRE Agent, and Asynchronous VLA Batch Orchestrator."
TOPICS = [
    "robotics",
    "physical-ai",
    "lerobot",
    "nvidia-cosmos",
    "nvidia-nemotron",
    "nebius",
    "tavily",
    "control-theory",
    "fastapi",
    "threejs",
]


def get_git_token() -> str:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Could not retrieve GitHub token from git credential fill")


def deploy_gh_pages(root_dir: Path) -> None:
    dist_dir = root_dir / "frontend" / "dist"
    if not dist_dir.exists():
        raise RuntimeError("frontend/dist does not exist. Run npm run build first.")

    # Copy index.html to 404.html and add .nojekyll for clean GitHub Pages serving
    shutil.copyfile(dist_dir / "index.html", dist_dir / "404.html")
    (dist_dir / ".nojekyll").write_text("", encoding="utf-8")

    remote_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}.git"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for item in dist_dir.iterdir():
            dest = tmp_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        subprocess.run(["git", "init"], cwd=tmp_path, check=True)
        subprocess.run(["git", "checkout", "-b", "gh-pages"], cwd=tmp_path, check=True)
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "deploy: publish interactive 6-DOF mechanics & SRE workbench to GitHub Pages"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=tmp_path, check=True)
        subprocess.run(["git", "push", "--force", "origin", "gh-pages"], cwd=tmp_path, check=True)
    print(f"[PASS] Deployed frontend/dist to gh-pages branch ({PAGES_URL})")


def update_github_repo_metadata(token: str) -> None:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "aether-loop-deployer",
    }

    # 1. Update Description and Homepage URL
    repo_api = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
    req_patch = urllib.request.Request(
        repo_api,
        data=json.dumps({"description": DESCRIPTION, "homepage": PAGES_URL}).encode("utf-8"),
        headers=headers,
        method="PATCH",
    )
    with urllib.request.urlopen(req_patch) as resp:
        print(f"[PASS] Updated GitHub About Description & Homepage ({resp.status})")

    # 2. Update Repository Topics
    topics_api = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/topics"
    req_topics = urllib.request.Request(
        topics_api,
        data=json.dumps({"names": TOPICS}).encode("utf-8"),
        headers=headers,
        method="PUT",
    )
    with urllib.request.urlopen(req_topics) as resp:
        print(f"[PASS] Updated 10 GitHub Repository Topics ({resp.status})")

    # 3. Enable GitHub Pages on gh-pages branch (ignore 409 if already enabled)
    pages_api = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pages"
    req_pages = urllib.request.Request(
        pages_api,
        data=json.dumps({"source": {"branch": "gh-pages", "path": "/"}}).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req_pages) as resp:
            print(f"[PASS] Enabled GitHub Pages ({resp.status})")
    except urllib.error.HTTPError as e:
        if e.code in (409, 422):
            print("[PASS] GitHub Pages already enabled on gh-pages branch.")
        else:
            print(f"[WARN] GitHub Pages API returned {e.code}: {e.read().decode('utf-8', errors='ignore')}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    deploy_gh_pages(root)
    gh_token = get_git_token()
    update_github_repo_metadata(gh_token)
