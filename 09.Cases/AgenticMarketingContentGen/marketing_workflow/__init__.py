"""Agentic marketing workflow built on Microsoft Agent Framework."""

from .schemas import (
    CampaignPackage,
    CopywritingContent,
    ImageContent,
    ImagePrompt,
    MarketingStrategy,
    SocialPost,
    VideoScene,
    VideoScript,
)
from .workflow import AgenticMarketingWorkflow, MarketingWorkflowConfig

__all__ = [
    "AgenticMarketingWorkflow",
    "MarketingWorkflowConfig",
    "CampaignPackage",
    "CopywritingContent",
    "ImageContent",
    "ImagePrompt",
    "MarketingStrategy",
    "SocialPost",
    "VideoScene",
    "VideoScript",
]
