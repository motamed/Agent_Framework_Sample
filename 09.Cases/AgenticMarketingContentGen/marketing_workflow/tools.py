"""Tooling objects that agents and executors can call."""

from __future__ import annotations

import asyncio
import base64
import inspect
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Optional, List

from agent_framework import ai_function

from .schemas import CampaignPackage
from .utils import dump_json, ensure_directory, slugify, timestamp_id


class TavilySearchTools:
    """Web search tool using Tavily API for market research and content gathering."""

    def __init__(self, *, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("Tvly_API_KEY")
        self._client: Any = None
        self._search_tool = self._create_search_tool()

    def _get_client(self) -> Any:
        """Lazily initialize the Tavily client."""
        if self._client is None:
            if not self._api_key:
                raise RuntimeError(
                    "Tavily API key not configured. "
                    "Set Tvly_API_KEY in .env"
                )
            from tavily import TavilyClient
            self._client = TavilyClient(api_key=self._api_key)
        return self._client

    @property
    def search(self) -> Any:
        """Return the bound tool function for use with ChatAgent."""
        return self._search_tool

    def _create_search_tool(self) -> Any:
        """Create a bound ai_function tool for web search."""

        @ai_function(description="Search the web for current information, market trends, competitor analysis, or any topic research. Use this to gather real-time data and insights for marketing strategy and content creation.")
        def web_search(
            query: Annotated[str, "The search query. Be specific and include relevant keywords for better results."],
            search_depth: Annotated[str, "Search depth: 'basic' for quick results, 'advanced' for comprehensive research"] = "basic",
            max_results: Annotated[int, "Maximum number of results to return (1-10)"] = 5,
        ) -> dict[str, Any]:
            """Search the web using Tavily and return relevant results."""
            return self._do_search(query, search_depth, max_results)

        return web_search

    def _do_search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
    ) -> dict[str, Any]:
        """Internal method to perform web search."""
        try:
            client = self._get_client()
            
            # Clamp max_results to valid range
            max_results = max(1, min(10, max_results))
            
            response = client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
            )
            
            # Format results for agent consumption
            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0),
                })
            
            return {
                "query": query,
                "results": results,
                "answer": response.get("answer", ""),
            }
        except Exception as e:
            # Return error info instead of raising exception
            # This allows the agent to handle the error gracefully
            error_msg = str(e)
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "..."
            
            return {
                "query": query,
                "error": f"Web search failed: {error_msg}",
                "results": [],
                "answer": "",
            }


class SoraVideoGenerationTools:
    """Tool for generating videos using Azure OpenAI Sora-2 model.
    
    Note: Sora-2 API has concurrency limits (max 2 concurrent tasks).
    This tool uses a lock to ensure videos are generated sequentially.
    """

    # Class-level lock to ensure sequential video generation
    # This prevents concurrent API calls that would hit rate limits
    import threading
    _generation_lock = threading.Lock()

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        default_size: str = "1280x720",
        max_seconds: int = 10,
    ) -> None:
        self._endpoint = endpoint or os.getenv("AZURE_VIDEO_ENDPOINT")
        self._api_key = api_key or os.getenv("AZURE_VIDEO_API_KEY") or os.getenv("AZURE_IMAGE_API_KEY")
        self._deployment_name = deployment_name or os.getenv("AZURE_VIDEO_DEPLOYMENT_NAME", "sora-2")
        self._output_dir: Optional[Path] = Path(output_dir) if output_dir else None
        self._default_size = default_size
        self._max_seconds = max_seconds
        self._generated_videos: list[dict[str, Any]] = []
        
        # Create bound tool function
        self._generate_video_tool = self._create_generate_video_tool()

    @property
    def generated_videos(self) -> list[dict[str, Any]]:
        """Return list of generated videos with their paths and prompts."""
        return self._generated_videos.copy()
    
    @property
    def generate_video(self) -> Any:
        """Return the bound tool function for use with ChatAgent."""
        return self._generate_video_tool
    
    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for generated videos."""
        self._output_dir = Path(output_dir)
        ensure_directory(self._output_dir)

    def _create_generate_video_tool(self) -> Any:
        """Create a bound ai_function tool."""
        
        @ai_function(description="Generate a marketing video clip using AI Sora-2 model. Returns the file path of the generated video. The prompt MUST be in English. Each video clip should be max 10 seconds.")
        def generate_video(
            prompt: Annotated[str, "Detailed video generation prompt in English. Must describe the scene, action, camera movement, and atmosphere."],
            scene_id: Annotated[str, "Unique identifier for this scene, e.g. scene-01"] = "scene-01",
            seconds: Annotated[int, "Video duration in seconds (1-10)"] = 5,
            size: Annotated[str, "Video resolution: '1280x720' for landscape 720p, '720x1280' for portrait"] = "1280x720",
        ) -> dict[str, Any]:
            """Generate a video using Azure Sora-2 model and save to disk."""
            return self._do_generate_video(prompt, scene_id, seconds, size)
        
        return generate_video
    
    def _do_generate_video(
        self,
        prompt: str,
        scene_id: str = "scene-01",
        seconds: int = 5,
        size: str = "1280x720",
    ) -> dict[str, Any]:
        """Internal method to generate video.
        
        Uses a lock to ensure sequential generation due to API concurrency limits.
        """
        import requests
        import time
        
        if self._output_dir is None:
            raise RuntimeError(
                "Video output directory not set. Call set_output_dir() first."
            )
        
        if not self._endpoint or not self._api_key:
            raise RuntimeError(
                "Azure video generation credentials not configured. "
                "Set AZURE_VIDEO_ENDPOINT and AZURE_VIDEO_API_KEY in .env"
            )
        
        # Ensure output directory exists
        ensure_directory(self._output_dir)
        
        # Clamp seconds to valid values (Sora-2 only supports 4, 8, or 12 seconds)
        valid_seconds = [4, 8, 12]
        seconds = min(valid_seconds, key=lambda x: abs(x - seconds))
        
        # Acquire lock to ensure sequential generation (API concurrency limit)
        with SoraVideoGenerationTools._generation_lock:
            # Build request payload
            payload = {
                "prompt": prompt,
                "size": size or self._default_size,
                "seconds": str(seconds),
                "model": self._deployment_name,
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            }
            
            # Make API request to create video generation job
            response = requests.post(
                self._endpoint,
                json=payload,
                headers=headers,
                timeout=60,
            )
            
            if response.status_code != 200:
                # Return error info but don't crash
                return {
                    "scene_id": scene_id,
                    "error": f"API error: {response.status_code} - {response.text[:200]}",
                    "local_path": None,
                }
            
            result_data = response.json()
            video_id = result_data.get("id")
            
            if not video_id:
                return {
                    "scene_id": scene_id,
                    "error": "No video ID returned from API",
                    "local_path": None,
                }
            
            # Poll for video completion (Sora-2 uses async generation)
            status_url = f"{self._endpoint}/{video_id}"
            max_wait_time = 300  # 5 minutes max wait
            poll_interval = 5  # Check every 5 seconds
            elapsed = 0
            
            while elapsed < max_wait_time:
                status_response = requests.get(status_url, headers=headers, timeout=30)
                if status_response.status_code != 200:
                    return {
                        "scene_id": scene_id,
                        "error": f"Status check failed: {status_response.status_code}",
                        "video_id": video_id,
                        "local_path": None,
                    }
                
                status_data = status_response.json()
                status = status_data.get("status", "unknown")
                
                if status == "completed":
                    break
                elif status == "failed":
                    return {
                        "scene_id": scene_id,
                        "error": f"Video generation failed: {status_data.get('error', 'Unknown error')}",
                        "video_id": video_id,
                        "local_path": None,
                    }
                
                # Still processing, wait and retry
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            if elapsed >= max_wait_time:
                return {
                    "scene_id": scene_id,
                    "error": "Video generation timed out",
                    "video_id": video_id,
                    "local_path": None,
                }
            
            # Video is ready, get the content URL
            content_url = f"{self._endpoint}/{video_id}/content"
            content_response = requests.get(content_url, headers=headers, timeout=120, allow_redirects=True)
            
            filename = f"{timestamp_id()}_{slugify(scene_id)}.mp4"
            filepath = self._output_dir / filename
            
            video_url: Optional[str] = None
            local_path: Optional[str] = None
            
            if content_response.status_code == 200:
                content_type = content_response.headers.get("Content-Type", "")
                
                if "video" in content_type or content_response.content[:4] == b'\x00\x00\x00':
                    # Direct video content
                    filepath.write_bytes(content_response.content)
                    local_path = str(filepath)
                    video_url = local_path
                else:
                    # Might be a redirect URL or JSON response
                    try:
                        content_data = content_response.json()
                        if "url" in content_data:
                            video_url = content_data["url"]
                            # Download from URL
                            video_download = requests.get(video_url, timeout=120)
                            if video_download.status_code == 200:
                                filepath.write_bytes(video_download.content)
                                local_path = str(filepath)
                    except:
                        # If not JSON, check if it's the URL in text
                        video_url = content_response.text.strip()
                        if video_url and video_url.startswith("http"):
                            try:
                                video_download = requests.get(video_url, timeout=120)
                                if video_download.status_code == 200:
                                    filepath.write_bytes(video_download.content)
                                    local_path = str(filepath)
                            except:
                                pass
            
            result = {
                "scene_id": scene_id,
                "prompt": prompt,
                "video_id": video_id,
                "url": video_url,
                "local_path": local_path,
                "duration_seconds": seconds,
                "size": size,
            }
            self._generated_videos.append(result)
            
            return result


class FluxImageGenerationTools:
    """Tool for generating images using Azure OpenAI FLUX model."""

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        default_size: str = "1024x1024",
    ) -> None:
        self._endpoint = endpoint or os.getenv("AZURE_IMAGE_ENDPOINT")
        self._api_key = api_key or os.getenv("AZURE_IMAGE_API_KEY")
        self._deployment_name = deployment_name or os.getenv("AZURE_IMAGE_DEPLOYMENT_NAME", "FLUX.1-Kontext-pro")
        self._output_dir: Optional[Path] = Path(output_dir) if output_dir else None
        self._default_size = default_size
        self._client: Any = None
        self._generated_images: list[dict[str, str]] = []
        
        # Create bound tool function
        self._generate_image_tool = self._create_generate_image_tool()

    def _get_client(self) -> Any:
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            if not self._endpoint or not self._api_key:
                raise ValueError(
                    "Azure image generation credentials not configured. "
                    "Set AZURE_IMAGE_ENDPOINT and AZURE_IMAGE_API_KEY in .env"
                )
            from openai import OpenAI
            self._client = OpenAI(base_url=self._endpoint, api_key=self._api_key)
        return self._client

    @property
    def generated_images(self) -> list[dict[str, str]]:
        """Return list of generated images with their paths and prompts."""
        return self._generated_images.copy()
    
    @property
    def generate_image(self) -> Any:
        """Return the bound tool function for use with ChatAgent."""
        return self._generate_image_tool
    
    def set_output_dir(self, output_dir: str) -> None:
        """Set the output directory for generated images."""
        self._output_dir = Path(output_dir)
        ensure_directory(self._output_dir)

    def _create_generate_image_tool(self) -> Any:
        """Create a bound ai_function tool."""
        
        @ai_function(description="Generate a marketing image using AI. Returns the file path and URL of the generated image. The prompt MUST be in English.")
        def generate_image(
            prompt: Annotated[str, "Detailed image generation prompt in English. Must be descriptive and include lighting, composition, and atmosphere details."],
            prompt_id: Annotated[str, "Unique identifier for this image, e.g. prompt-01"] = "prompt-01",
            size: Annotated[str, "Image size, e.g., 1024x1024, 1792x1024"] = "1024x1024",
        ) -> dict[str, Any]:
            """Generate an image using Azure FLUX model and save to disk."""
            return self._do_generate_image(prompt, prompt_id, size)
        
        return generate_image
    
    def _do_generate_image(
        self,
        prompt: str,
        prompt_id: str = "prompt-01",
        size: str = "1024x1024",
    ) -> dict[str, Any]:
        """Internal method to generate image."""
        if self._output_dir is None:
            return {
                "prompt_id": prompt_id,
                "error": "Image output directory not set. Call set_output_dir() first.",
                "url": None,
                "local_path": None,
            }
        
        # Ensure output directory exists
        ensure_directory(self._output_dir)
        
        try:
            client = self._get_client()
            
            # Generate image
            response = client.images.generate(
                model=self._deployment_name,
                prompt=prompt,
                n=1,
                size=size or self._default_size,
            )
            
            # Decode and save image
            image_data = response.data[0]
            filename = f"{timestamp_id()}_{slugify(prompt_id)}.png"
            filepath = self._output_dir / filename
            
            url: Optional[str] = None
            local_path: Optional[str] = None
            
            if hasattr(image_data, "b64_json") and image_data.b64_json:
                image_bytes = base64.b64decode(image_data.b64_json)
                filepath.write_bytes(image_bytes)
                url = str(filepath)
                local_path = str(filepath)
            elif hasattr(image_data, "url") and image_data.url:
                url = image_data.url
                # Try to download and save locally
                try:
                    import requests
                    img_response = requests.get(url, timeout=60)
                    if img_response.status_code == 200:
                        filepath.write_bytes(img_response.content)
                        local_path = str(filepath)
                except Exception:
                    pass  # URL exists but couldn't download locally
            
            revised_prompt = getattr(image_data, "revised_prompt", None) or prompt
            
            result = {
                "prompt_id": prompt_id,
                "url": url or str(filepath),
                "revised_prompt": revised_prompt,
                "local_path": local_path,
                "prompt": prompt,
            }
            self._generated_images.append(result)
            
            return result
            
        except Exception as e:
            # Always return a valid response even on error
            # This prevents the "tool_calls without response" error
            error_msg = str(e)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            
            return {
                "prompt_id": prompt_id,
                "error": f"Image generation failed: {error_msg}",
                "url": None,
                "local_path": None,
                "prompt": prompt,
            }


class ImageGenerationTools:
    """Optional tool that lets the image agent trigger DALL-E/Midjourney compatible renders."""

    def __init__(
        self,
        image_client: Any = None,
        *,
        default_style: str = "vivid",
        default_size: str = "1024x1024",
    ) -> None:
        self._image_client = image_client
        self._default_style = default_style
        self._default_size = default_size

    @ai_function(description="Generate or request a marketing-friendly image.")
    async def generate_image(
        self,
        prompt: Annotated[str, "Image generation prompt"],
        *,
        style: Annotated[str, "Visual style, e.g., vivid, natural"] = None,
        size: Annotated[str, "Image size, e.g., 1024x1024"] = None,
    ) -> dict[str, Optional[str]]:
        """Invoke the configured image client or return a mock payload for dry-runs."""

        if self._image_client is None:
            slug = slugify(prompt)[:16]
            return {"url": f"mock://image/{slug}", "revised_prompt": prompt}

        request_kwargs = {
            "prompt": prompt,
            "style": style or self._default_style,
            "size": size or self._default_size,
            "n": 1,
        }

        client = self._image_client
        if hasattr(client, "images"):
            result = client.images.generate(**request_kwargs)
        else:
            result = client.generate(**request_kwargs)

        response = await maybe_await(result)
        data = response.data[0]
        return {"url": getattr(data, "url", None), "revised_prompt": getattr(data, "revised_prompt", prompt)}


@dataclass(slots=True)
class PackagingTools:
    """Filesystem helper used by the packaging executor."""

    base_output_dir: Path = Path("artifacts/campaigns")

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        ensure_directory(self.base_output_dir)

    def persist_package(self, package: CampaignPackage, campaign_dir: Optional[str] = None) -> str:
        """Create a folder with markdown/json assets for the campaign.
        
        Args:
            package: The campaign package to persist.
            campaign_dir: Optional pre-existing campaign directory path. If provided,
                         the package will be saved to this directory (images may already exist there).
        """

        if campaign_dir:
            base_dir = Path(campaign_dir)
        else:
            folder_name = f"{timestamp_id()}_{slugify(package.campaign_id)}"
            base_dir = self.base_output_dir / folder_name
        
        ensure_directory(base_dir)
        copy_dir = ensure_directory(base_dir / "copywriting")
        img_dir = ensure_directory(base_dir / "images")
        video_dir = ensure_directory(base_dir / "video")
        strategy_dir = ensure_directory(base_dir / "strategy")

        # Strategy assets
        dump_json(package.strategy.model_dump(), strategy_dir / "strategy.json")
        strategy_md = self._format_strategy_markdown(package.strategy)
        (strategy_dir / "strategy.md").write_text(strategy_md, encoding="utf-8")

        # Copywriting assets
        (copy_dir / "hero_message.md").write_text(package.copywriting.hero_message, encoding="utf-8")
        (copy_dir / "blog.md").write_text(package.copywriting.blog_article, encoding="utf-8")
        dump_json([post.model_dump(exclude_none=True) for post in package.copywriting.social_posts], copy_dir / "social_posts.json")
        dump_json(package.copywriting.blog_outline, copy_dir / "blog_outline.json")
        dump_json(package.copywriting.pain_point_analysis, copy_dir / "pain_point_analysis.json")
        dump_json(package.copywriting.cta_variations, copy_dir / "cta_variations.json")
        
        # Email campaign assets
        if package.copywriting.email_campaign:
            email_dir = ensure_directory(copy_dir / "email")
            email = package.copywriting.email_campaign
            
            # Save complete JSON data
            dump_json(email.model_dump(exclude_none=True), email_dir / "email_campaign.json")
            
            # Save HTML email (ready for email clients)
            html_email = self._format_email_html(email)
            (email_dir / "email_campaign.html").write_text(html_email, encoding="utf-8")
            
            # Save plain text version
            (email_dir / "email_campaign.txt").write_text(email.body_plain or "", encoding="utf-8")
            
            # Save subject lines for A/B testing
            if email.subject_lines:
                (email_dir / "subject_lines.txt").write_text("\n".join(email.subject_lines), encoding="utf-8")

        # Image assets
        dump_json([prompt.model_dump(exclude_none=True) for prompt in package.images.prompts], img_dir / "prompts.json")
        dump_json([asset.model_dump(exclude_none=True) for asset in package.images.assets], img_dir / "assets.json")

        # Video assets
        dump_json([scene.model_dump(exclude_none=True) for scene in package.video.scenes], video_dir / "scenes.json")
        dump_json(package.video.model_dump(exclude_none=True), video_dir / "video_script.json")
        (video_dir / "script.md").write_text(package.video.srt_caption, encoding="utf-8")
        (video_dir / "cta.md").write_text(package.video.cta, encoding="utf-8")
        if package.video.structure_notes:
            (video_dir / "structure_notes.md").write_text("\n".join(f"- {note}" for note in package.video.structure_notes), encoding="utf-8")

        # Manifest
        dump_json(package.model_dump(exclude_none=True), base_dir / "manifest.json")
        return str(base_dir)
    
    def _format_strategy_markdown(self, strategy) -> str:
        """Format strategy as readable markdown."""
        lines = [
            f"# Marketing Strategy: {strategy.topic}",
            "",
            "## Target Audience",
            strategy.target_audience,
            "",
            "## Pain Points",
        ]
        for point in strategy.pain_points:
            lines.append(f"- {point}")
        lines.extend(["", "## Selling Points"])
        for point in strategy.selling_points:
            lines.append(f"- {point}")
        lines.extend(["", "## Content Framework"])
        for item in strategy.content_framework:
            lines.append(f"1. {item}")
        lines.extend(["", "## Tone of Voice", strategy.tone_of_voice, "", "## Brand Pillars"])
        for pillar in strategy.brand_pillars:
            lines.append(f"- {pillar}")
        lines.extend(["", "## Keywords"])
        lines.append(", ".join(strategy.keywords))
        return "\n".join(lines)
    
    def _format_email_html(self, email) -> str:
        """Format email campaign as a complete HTML email document.
        
        Creates an email-client compatible HTML file with:
        - Proper DOCTYPE and meta tags for email rendering
        - Inline CSS (email clients strip external styles)
        - Responsive table-based layout
        - Preview text hidden but accessible to email clients
        """
        subject = email.subject_lines[0] if email.subject_lines else "Marketing Email"
        preview = email.preview_text or ""
        
        return f'''<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>{subject}</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        /* Reset styles */
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }}
        /* Mobile styles */
        @media screen and (max-width: 600px) {{
            .email-container {{ width: 100% !important; margin: auto !important; }}
            .stack-column, .stack-column-center {{ display: block !important; width: 100% !important; max-width: 100% !important; direction: ltr !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f4f4;">
    <!-- Preview text (hidden but shown in email client preview) -->
    <div style="display: none; font-size: 1px; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; mso-hide: all;">
        {preview}
    </div>
    
    <!-- Email wrapper -->
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f4f4f4;">
        <tr>
            <td style="padding: 20px 0;">
                <!-- Email container -->
                <table class="email-container" role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: #ffffff;">
                    <!-- Email body -->
                    <tr>
                        <td style="padding: 30px 40px;">
                            {email.body_html or ""}
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 40px; background-color: #f8f8f8; border-top: 1px solid #e0e0e0;">
                            <p style="margin: 0; font-family: Arial, sans-serif; font-size: 12px; color: #888888; text-align: center;">
                                You received this email because you subscribed to our newsletter.<br>
                                <a href="{{{{UNSUBSCRIBE_URL}}}}" style="color: #888888;">Unsubscribe</a> | <a href="{{{{PREFERENCES_URL}}}}" style="color: #888888;">Update preferences</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>'''


async def maybe_await(value: Any) -> Any:
    """Await a value if it is awaitable."""

    if inspect.isawaitable(value):
        return await value
    if asyncio.isfuture(value):  # pragma: no cover - defensive
        return await value
    return value
