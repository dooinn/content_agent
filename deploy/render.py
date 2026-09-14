"""Render deploy/service.template.yaml into a Cloud Run service spec.

Non-secret settings (models, voice id) are copied from backend/.env using an allowlist. Langfuse
keys are added as Secret Manager references only when they are set locally.

    uv run --project backend python deploy/render.py --tag r1 --out service.yaml
"""

import argparse
import json
from pathlib import Path
from string import Template

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = [
    "CLAUDE_MODEL",
    "IMAGE_MODEL",
    "IMAGE_QUALITY",
    "VIDEO_MODEL",
    "BGM_VOLUME",
    "ELEVENLABS_VOICE_ID",
    "ELEVENLABS_MODEL_ID",
    "LANGFUSE_HOST",
    "LANGFUSE_BASE_URL",
]
OPTIONAL_SECRETS = {
    "LANGFUSE_PUBLIC_KEY": "langfuse-public-key",
    "LANGFUSE_SECRET_KEY": "langfuse-secret-key",
}
INDENT = " " * 8


def env_value(name: str, value: str) -> str:
    return f"{INDENT}- name: {name}\n{INDENT}  value: {json.dumps(value)}\n"


def env_secret(name: str, secret: str) -> str:
    return (
        f"{INDENT}- name: {name}\n{INDENT}  valueFrom:\n{INDENT}    secretKeyRef:\n"
        f"{INDENT}      name: {secret}\n{INDENT}      key: latest\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="ai-video-dooinn")
    parser.add_argument("--region", default="europe-west9")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    local = {k: (v or "").strip() for k, v in dotenv_values(ROOT / "backend" / ".env").items()}
    extra = "".join(env_value(name, local[name]) for name in SETTINGS if local.get(name))
    extra += "".join(
        env_secret(name, secret) for name, secret in OPTIONAL_SECRETS.items() if local.get(name)
    )
    template = Template((ROOT / "deploy" / "service.template.yaml").read_text(encoding="utf-8"))
    spec = template.substitute(
        project=args.project, region=args.region, tag=args.tag, extra_env=extra
    )
    args.out.write_text(spec, encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
