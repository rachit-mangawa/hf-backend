"""Synchronizes registered services from registry.py and requirements.in to frontend/registry.json.

Runs during the GitHub Actions Pages deployment workflow and can be run locally.
Ensures any newly added project in registry.py automatically shows up on the website.
"""

import ast
import json
import os
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PY = ROOT_DIR / "registry.py"
REQUIREMENTS_IN = ROOT_DIR / "requirements.in"
FRONTEND_REGISTRY_JSON = ROOT_DIR / "frontend" / "registry.json"

PALETTE = ["icon-emerald", "icon-blue", "icon-purple", "icon-amber", "icon-cyan"]

KNOWN_METADATA = {
    "/heartflow": {
        "name": "HeartFlow OS",
        "description": "Clinical cardiovascular risk scoring and interpretability engine. Evaluates vitals, computes local SHAP feature attributions, and compiles TinyML C header artifacts for embedded microcontrollers.",
        "tag": "ML SERVICE",
        "repoUrl": "https://github.com/rachit-mangawa/HEARTFLOW_OS",
        "liveUrl": "https://rachit-mangawa.github.io/HEARTFLOW_OS/",
        "specs": [
            {"label": "ROC-AUC", "value": "94.2%"},
            {"label": "Explainability", "value": "SHAP Tree"},
            {"label": "Edge Target", "value": "TinyML C99"}
        ],
        "icon": "icons/heartflow.svg",
        "iconClass": "icon-emerald"
    },
    "/semantic": {
        "name": "Semantic Analyzer",
        "description": "Multi-task NLP inference engine for developer and community feedback. Computes dense sentence embeddings, polarity scores, and multi-label toxicity classifications with pre-warmed weights.",
        "tag": "NLP SERVICE",
        "repoUrl": "https://github.com/rachit-mangawa/Semantic-Comment-Analyze",
        "liveUrl": "https://rachit-mangawa.github.io/Semantic-Comment-Analyze/",
        "specs": [
            {"label": "Embedding", "value": "MiniLM-L6-v2"},
            {"label": "Toxicity", "value": "Multi-label"},
            {"label": "Latency", "value": "~18ms CPU"}
        ],
        "icon": "icons/semantic.svg",
        "iconClass": "icon-blue"
    }
}


def parse_registry() -> dict[str, str]:
    if not REGISTRY_PY.exists():
        print(f"Warning: {REGISTRY_PY} not found.", file=sys.stderr)
        return {}

    with open(REGISTRY_PY, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(REGISTRY_PY))

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "PROJECT_REGISTRY":
                    if isinstance(node.value, ast.Dict):
                        registry = {}
                        for k, v in zip(node.value.keys, node.value.values):
                            if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                                registry[k.value] = v.value
                        return registry
    return {}


def parse_requirements_repos() -> dict[str, str]:
    """Extracts GitHub repository URLs mapped to keywords from requirements.in."""
    repos = {}
    if not REQUIREMENTS_IN.exists():
        return repos

    git_pattern = re.compile(r"git\+https://github\.com/([^/]+)/([^/.]+)(?:\.git)?")
    with open(REQUIREMENTS_IN, "r", encoding="utf-8") as f:
        for line in f:
            match = git_pattern.search(line.strip())
            if match:
                owner, repo = match.groups()
                full_url = f"https://github.com/{owner}/{repo}"
                clean_name = repo.lower().replace("_", "-")
                repos[clean_name] = full_url
                for part in clean_name.split("-"):
                    if len(part) >= 3:
                        repos[part] = full_url
    return repos


def format_title(prefix: str) -> str:
    clean = prefix.strip("/").replace("-", " ").replace("_", " ")
    return " ".join(word.capitalize() for word in clean.split())


def sync_registry() -> list[dict]:
    registry_map = parse_registry()
    req_repos = parse_requirements_repos()

    # Load existing registry.json if present to preserve custom edits
    existing_by_prefix = {}
    if FRONTEND_REGISTRY_JSON.exists():
        try:
            with open(FRONTEND_REGISTRY_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("projects", []):
                    existing_by_prefix[item.get("prefix")] = item
        except Exception as e:
            print(f"Notice: Could not parse existing registry.json: {e}", file=sys.stderr)

    projects = []
    color_idx = 0

    for prefix, target in registry_map.items():
        clean_prefix = prefix.strip("/")
        # Check known presets
        if prefix in KNOWN_METADATA:
            entry = dict(KNOWN_METADATA[prefix])
            entry["prefix"] = prefix
            entry["target"] = target
            projects.append(entry)
            continue

        # Check existing metadata
        if prefix in existing_by_prefix:
            entry = dict(existing_by_prefix[prefix])
            entry["prefix"] = prefix
            entry["target"] = target
            projects.append(entry)
            continue

        # Auto-generate metadata for newly added project
        repo_url = ""
        for key, url in req_repos.items():
            if key in clean_prefix.lower() or clean_prefix.lower() in key:
                repo_url = url
                break

        title = format_title(prefix)
        icon_class = PALETTE[color_idx % len(PALETTE)]
        color_idx += 1

        entry = {
            "prefix": prefix,
            "target": target,
            "name": title,
            "description": f"Pluggable Python microservice dynamically mounted at {prefix}.",
            "tag": "MICROSERVICE",
            "repoUrl": repo_url,
            "liveUrl": repo_url,
            "specs": [
                {"label": "Protocol", "value": "FastAPI"},
                {"label": "Target", "value": target.split(":")[-1]},
                {"label": "Status", "value": "Active"}
            ],
            "icon": "",
            "iconClass": icon_class
        }
        projects.append(entry)

    out_data = {
        "generated_at": None,
        "total_projects": len(projects),
        "projects": projects
    }

    FRONTEND_REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(FRONTEND_REGISTRY_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"Successfully generated {FRONTEND_REGISTRY_JSON} with {len(projects)} registered projects:")
    for p in projects:
        print(f"  - {p['prefix']} -> {p['name']} ({p.get('target', '')})")

    return projects


if __name__ == "__main__":
    sync_registry()
