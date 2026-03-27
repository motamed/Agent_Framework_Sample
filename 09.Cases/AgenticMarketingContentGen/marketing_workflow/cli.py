"""Simple CLI to trigger the marketing workflow."""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

from agent_framework.openai import OpenAIChatClient

try:  # Optional import; azure support is nice to have but not required.
    from agent_framework.azure import AzureOpenAIChatClient
except Exception:  # pragma: no cover - azure client not installed
    AzureOpenAIChatClient = None  # type: ignore

from .workflow import AgenticMarketingWorkflow, MarketingWorkflowConfig


def _build_chat_client(args: argparse.Namespace) -> Any:
    if args.provider == "azure":
        if AzureOpenAIChatClient is None:
            raise RuntimeError("agent_framework.azure is not available; install azure extras to use this provider")
        return AzureOpenAIChatClient(
            endpoint=args.azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            deployment_name=args.azure_deployment or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            api_key=args.azure_api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=args.azure_api_version or os.getenv("AZURE_OPENAI_API_VERSION"),
        )

    return OpenAIChatClient(
        model_id=args.model_id or os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini"),
        api_key=args.api_key or os.getenv("OPENAI_API_KEY"),
        base_url=args.base_url or os.getenv("OPENAI_BASE_URL"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Agentic Marketing Content Workflow")
    parser.add_argument("topic", help="Campaign topic or brief")
    parser.add_argument("--provider", choices=["openai", "azure"], default="azure")
    parser.add_argument("--model-id", dest="model_id", help="OpenAI model ID")
    parser.add_argument("--api-key", dest="api_key", help="OpenAI API key")
    parser.add_argument("--base-url", dest="base_url", help="Custom OpenAI endpoint")
    parser.add_argument("--azure-endpoint", dest="azure_endpoint")
    parser.add_argument("--azure-deployment", dest="azure_deployment")
    parser.add_argument("--azure-api-key", dest="azure_api_key")
    parser.add_argument("--azure-api-version", dest="azure_api_version")
    parser.add_argument("--output-dir", dest="output_dir", default="artifacts/campaigns")
    parser.add_argument("--no-persist", dest="persist", action="store_false", help="Skip writing files to disk")
    parser.add_argument("--enable-image-gen", dest="enable_image_gen", action="store_true", 
                        help="Enable AI image generation using Azure FLUX model")
    parser.add_argument("--enable-video-gen", dest="enable_video_gen", action="store_true",
                        help="Enable AI video generation using Azure Sora-2 model")
    parser.add_argument("--deep-research", dest="deep_research", action="store_true",
                        help="Enable deep research mode with multi-agent planning and execution")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug output showing agent execution details")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = _build_chat_client(args)
    workflow = AgenticMarketingWorkflow(
        client,
        config=MarketingWorkflowConfig(
            persist_output=args.persist, 
            output_dir=args.output_dir,
            enable_image_generation=args.enable_image_gen,
            enable_video_generation=args.enable_video_gen,
            enable_deep_research=args.deep_research,
            debug=args.debug,
        ),
    )

    result = asyncio.run(workflow.run(args.topic))
    print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
