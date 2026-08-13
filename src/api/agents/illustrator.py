"""Hero-image generation for the illustrator-CW agent.

Wraps the Foundry image deployment (gpt-image-2) as a best-effort call: on any
failure it returns ``None`` so article generation is never blocked.
"""
import os

from azure.identity import get_bearer_token_provider

from agent_framework_client import get_credential

_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"


def generate_hero_image(prompt: str) -> str | None:
    """Render an illustration and return it as a ``data:image/png;base64,...`` URL.

    Returns ``None`` if image generation is unavailable or fails.
    """
    try:
        from openai import AzureOpenAI

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not endpoint:
            return None
        deployment = os.getenv("AZURE_IMAGE_DEPLOYMENT_NAME", "gpt-image-2")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

        token_provider = get_bearer_token_provider(get_credential(), _COGNITIVE_SCOPE)
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=token_provider,
            api_version=api_version,
        )
        result = client.images.generate(
            model=deployment,
            prompt=prompt[:4000],
            size="1024x1024",
            n=1,
        )
        item = result.data[0]
        b64 = getattr(item, "b64_json", None)
        if b64:
            return f"data:image/png;base64,{b64}"
        url = getattr(item, "url", None)
        return url
    except Exception as exc:  # noqa: BLE001 - illustration is best-effort
        print(f"generate_hero_image unavailable, continuing without image: {exc}")
        return None
