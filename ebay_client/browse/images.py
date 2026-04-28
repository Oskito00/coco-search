"""Image serialization helpers for eBay Browse responses."""

import json
from typing import Any, Mapping, Sequence


def get_main_image_url(item_data: Mapping[str, Any]) -> str | None:
    """Return the primary image URL for an item summary."""
    image = item_data.get("image") or {}

    if not isinstance(image, Mapping):
        return None

    image_url = image.get("imageUrl")
    return str(image_url) if image_url else None


def serialize_images(item_data: Mapping[str, Any]) -> str:
    """Serialize primary and thumbnail image URLs for storage."""
    thumbnail_images = item_data.get("thumbnailImages") or []

    return json.dumps(
        {
            "main": get_main_image_url(item_data),
            "thumbnails": [
                image.get("imageUrl")
                for image in thumbnail_images
                if isinstance(image, Mapping)
            ],
        }
    )
