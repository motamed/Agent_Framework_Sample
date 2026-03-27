"""Main entry point for Content Workflow with Azure AI Foundry"""

import asyncio
import logging
import threading
import webbrowser

import uvicorn
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from workflow.workflow import create_workflow
from agent_framework_devui import DevServer


async def async_main():
    """Create workflow and launch DevUI in the same event loop.

    AzureAIAgentsProvider creates async HTTP sessions tied to the current event loop.
    We must run workflow creation and the uvicorn server in the SAME loop,
    otherwise the provider's sessions become unusable ('Event loop is closed').
    """
    workflow = await create_workflow()

    server = DevServer(port=8090, host="127.0.0.1", ui_enabled=True, mode="developer")
    server._pending_entities = [workflow]
    app = server.get_app()

    # Auto-open browser after server is ready
    def open_browser():
        import http.client
        import time

        for _ in range(30):
            try:
                conn = http.client.HTTPConnection("127.0.0.1", 8090, timeout=1)
                try:
                    conn.request("GET", "/health")
                    if conn.getresponse().status == 200:
                        webbrowser.open("http://127.0.0.1:8090")
                        return
                finally:
                    conn.close()
            except (http.client.HTTPException, OSError, TimeoutError):
                pass
            time.sleep(0.5)
        webbrowser.open("http://127.0.0.1:8090")

    threading.Thread(target=open_browser, daemon=True).start()

    config = uvicorn.Config(app, host="127.0.0.1", port=8090, log_level="info")
    uv_server = uvicorn.Server(config)
    await uv_server.serve()


def main():
    """Create workflow and launch DevUI"""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("🚀 Starting Content Workflow with Conditional Logic")
    logger.info("📍 Available at: http://localhost:8090")
    logger.info("📝 Workflow: Evangelist → Reviewer → (Conditional) → Publisher")
    logger.info("⚙️  Make sure 'az login' has been run for authentication")

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
