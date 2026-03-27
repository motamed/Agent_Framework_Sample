"""Pydantic schemas shared across the marketing workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketingStrategy(BaseModel):
    """Structured representation of the positioning work from the strategy agent."""

    model_config = ConfigDict(extra="ignore")

    topic: str = Field(default="", description="User supplied topic for the campaign.")
    user_intent: str = Field(default="", description="Analysis of user's original intent, goals, and what they want to achieve")
    output_language: str = Field(default="en", description="Language code for all outputs, detected from user input (e.g., 'en', 'zh', 'ja', 'ko', 'es', 'fr').")
    target_audience: str = Field(default="", description="Persona or ICP summary.")
    pain_points: List[str] = Field(default_factory=list, description="Ordered list of customer pains.")
    selling_points: List[str] = Field(default_factory=list, description="Differentiated value props.")
    content_framework: List[str] = Field(default_factory=list, description="Story beats or outline segments.")
    tone_of_voice: str = Field(default="", description="Tone guidance for downstream assets.")
    brand_pillars: List[str] = Field(default_factory=list, description="Anchor themes to repeat across channels.")
    keywords: List[str] = Field(default_factory=list, description="SEO or creative keywords to reuse.")


class EmailCampaign(BaseModel):
    """Email campaign content for nurture sequences."""

    model_config = ConfigDict(extra="ignore")

    subject_lines: List[str] = Field(default_factory=list, description="3-5 A/B testable subject line variations.")
    preview_text: str = Field(default="", description="Email preview/preheader text (50-100 chars).")
    email_type: str = Field(default="promotional", description="Type: welcome, promotional, nurture, announcement, etc.")
    headline: str = Field(default="", description="Main headline in email body.")
    body_html: str = Field(default="", description="Email body content in HTML format with inline styles.")
    body_plain: str = Field(default="", description="Plain text version of email body.")
    cta_button_text: str = Field(default="", description="Primary CTA button text.")
    cta_url_placeholder: str = Field(default="{{CTA_URL}}", description="Placeholder for CTA link.")
    ps_line: Optional[str] = Field(default=None, description="Optional P.S. line for additional urgency/hook.")
    segment_notes: Optional[str] = Field(default=None, description="Notes on which audience segment this email targets.")


class SocialPost(BaseModel):
    """Single social post variant."""

    model_config = ConfigDict(extra="ignore")

    platform: str = Field(default="", description="Channel, e.g. LinkedIn, Instagram, Xiaohongshu.")
    channel: Optional[str] = Field(default=None, description="Alternative field for platform/channel.")
    tone: str = Field(default="", description="Tone or mood for the copy.")
    hook: str = Field(default="", description="First line or hook that anchors the scroll stop.")
    body: str = Field(default="", description="Main body text.")
    cta: str = Field(default="", description="Call-to-action copy.")
    # Alternative fields from agent output
    copy_text: Optional[str] = Field(default=None, alias="copy", description="Alternative copy/content field.")
    content: Optional[str] = Field(default=None, description="Alternative content field.")
    post_text: Optional[str] = Field(default=None, description="Post text from agent.")
    call_to_action: Optional[str] = Field(default=None, description="Alternative CTA field.")
    image_suggestion: Optional[str] = Field(default=None, description="Suggested image description.")
    visual_prompt: Optional[str] = Field(default=None, description="Visual prompt for image generation.")
    hashtags: Optional[List[str]] = Field(default=None, description="Hashtags for the post.")
    
    @field_validator("hashtags", mode="before")
    @classmethod
    def normalize_hashtags(cls, v: Any) -> Optional[List[str]]:
        """Convert string hashtags to list format."""
        if v is None:
            return None
        if isinstance(v, str):
            # Split by space or comma, filter empty strings
            parts = v.replace(",", " ").split()
            return [p.strip() for p in parts if p.strip()]
        return v
    
    def model_post_init(self, __context: Any) -> None:
        # Normalize: if channel is set but platform is empty, use channel as platform
        if self.channel and not self.platform:
            object.__setattr__(self, "platform", self.channel)
        # Normalize body from alternative fields
        if not self.body:
            if self.post_text:
                object.__setattr__(self, "body", self.post_text)
            elif self.copy_text:
                object.__setattr__(self, "body", self.copy_text)
            elif self.content:
                object.__setattr__(self, "body", self.content)
        # Normalize cta from alternative field
        if not self.cta and self.call_to_action:
            object.__setattr__(self, "cta", self.call_to_action)


class CopywritingContent(BaseModel):
    """Payload emitted by the copywriting agent."""

    model_config = ConfigDict(extra="ignore")

    hero_message: str = Field(default="", description="One sentence elevator pitch.")
    social_posts: List[SocialPost] = Field(default_factory=list)
    email_campaign: Optional[EmailCampaign] = Field(default=None, description="Email campaign content for marketing automation.")
    blog_outline: List[str] = Field(default_factory=list, description="Ordered outline for the long-form asset.")
    blog_article: str = Field(default="", description="Full blog/long-form draft in markdown.")
    pain_point_analysis: List[str] = Field(default_factory=list, description="Problem/solution bullets.")
    cta_variations: List[str] = Field(default_factory=list, description="List of CTA options for experimentation.")


class ImagePrompt(BaseModel):
    """Prompt engineering payload for DALL-E/MJ style generators."""

    model_config = ConfigDict(extra="ignore")

    prompt_id: str = Field(default="", description="Stable identifier used for matching assets.")
    prompt: str = Field(default="", description="The actual text prompt to feed the image model.")
    scene_description: str = Field(default="", description="Plain language paraphrase for humans.")
    style: str = Field(default="cinematic", description="Visual direction (e.g., cinematic, minimal).")
    aspect_ratio: str = Field(default="1:1", description="Aspect ratio guidance.")


class GeneratedImage(BaseModel):
    """Metadata for actual rendered images (if any)."""

    model_config = ConfigDict(extra="ignore")

    prompt_id: str = Field(default="")
    url: str = Field(default="", description="URL or local file reference to the rendered image.")
    local_path: Optional[str] = Field(default=None, description="Local filesystem path.")
    revised_prompt: Optional[str] = Field(None, description="Model-adjusted prompt text.")
    prompt: Optional[str] = Field(default=None, description="Original prompt used.")


class ImageContent(BaseModel):
    """Aggregate of prompts and generated imagery."""

    model_config = ConfigDict(extra="ignore")

    prompts: List[ImagePrompt] = Field(default_factory=list)
    assets: List[GeneratedImage] = Field(default_factory=list)


class VideoScene(BaseModel):
    """Single scene in a three-act marketing video."""

    model_config = ConfigDict(extra="ignore")

    scene_number: int = Field(default=0)
    act: str = Field(default="", description="Problem / Solution / Transformation")
    visuals: str = Field(default="", description="Camera + action direction.")
    voiceover: str = Field(default="", description="Narration copy.")
    screen_text: str = Field(default="", description="On-screen supers or captions.")
    duration_seconds: int = Field(default=5, ge=1, description="Approximate duration for the shot.")
    # Alternative fields that agents might return
    description: Optional[str] = Field(default=None, description="Scene description.")
    narration: Optional[str] = Field(default=None, description="Alternative narration field.")
    caption: Optional[str] = Field(default=None, description="Alternative caption field.")
    audio: Optional[str] = Field(default=None, description="Audio description.")
    audio_narration: Optional[str] = Field(default=None, description="Audio narration text.")
    on_screen_text: Optional[str] = Field(default=None, description="On-screen text overlay.")
    camera_moves: Optional[str] = Field(default=None, description="Camera movement description.")
    camera_actions: Optional[str] = Field(default=None, description="Camera actions.")
    props: Optional[Any] = Field(default=None, description="Props used in scene - can be string or list.")
    speaker: Optional[str] = Field(default=None, description="Speaker in the scene.")
    dialogue: Optional[Any] = Field(default=None, description="Dialogue in the scene - can be string or list.")
    visual: Optional[str] = Field(default=None, description="Visual description (alternative).")
    actions: Optional[str] = Field(default=None, description="Actions in the scene.")
    camera_instructions: Optional[str] = Field(default=None, description="Camera instructions.")
    camera_direction: Optional[str] = Field(default=None, description="Camera direction.")
    actor_actions: Optional[str] = Field(default=None, description="Actor actions.")
    sfx: Optional[str] = Field(default=None, description="Sound effects.")
    transition: Optional[str] = Field(default=None, description="Transition to next scene.")
    shot_description: Optional[str] = Field(default=None, description="Shot description.")
    visual_instructions: Optional[str] = Field(default=None, description="Visual instructions.")
    sound_instructions: Optional[str] = Field(default=None, description="Sound instructions.")
    
    def model_post_init(self, __context: Any) -> None:
        # Normalize voiceover from alternative fields
        if not self.voiceover:
            if self.audio_narration:
                object.__setattr__(self, "voiceover", self.audio_narration)
            elif self.narration:
                object.__setattr__(self, "voiceover", self.narration)
            elif self.dialogue and isinstance(self.dialogue, str):
                # Use dialogue as voiceover if it's a simple string
                object.__setattr__(self, "voiceover", self.dialogue)
        # Normalize screen_text from alternative field
        if not self.screen_text and self.on_screen_text:
            object.__setattr__(self, "screen_text", self.on_screen_text)
        # Normalize visuals from alternative field
        if not self.visuals and self.visual:
            object.__setattr__(self, "visuals", self.visual)


class VideoScript(BaseModel):
    """Structured output for the video/script agent."""

    model_config = ConfigDict(extra="ignore")

    structure_notes: List[str] = Field(default_factory=list, description="High-level structure summary.")
    scenes: List[VideoScene] = Field(default_factory=list)
    total_duration_seconds: int = Field(default=60, description="Summed duration for quick planning.")
    cta: str = Field(default="", description="Closing CTA line.")
    srt_caption: str = Field(default="", description="Subtitle text block in SRT style.")


class CampaignPackage(BaseModel):
    """Final packaged output across all modalities."""

    model_config = ConfigDict(extra="ignore")

    campaign_id: str = Field(...)
    topic: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    strategy: MarketingStrategy
    copywriting: CopywritingContent
    images: ImageContent
    video: VideoScript
    package_path: Optional[str] = Field(default=None, description="Filesystem location for persisted assets.")

    def with_package_path(self, path: str) -> "CampaignPackage":
        """Return a copy with an updated package path."""

        return self.model_copy(update={"package_path": path})
