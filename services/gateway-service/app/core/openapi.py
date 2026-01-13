"""
OpenAPI Documentation Aggregation Module

Responsible for dynamically fetching and merging OpenAPI documentation from downstream services (Auth Service, Host Service) into the Gateway's Swagger UI.
"""

import os
import sys
from typing import List

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
import httpx

from app.core.config import settings

# Use try-except to handle path imports
try:
    from shared.common.loguru_config import get_logger
except ImportError:
    # If import fails, add project root directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
    from shared.common.loguru_config import get_logger

logger = get_logger(__name__)


def custom_openapi(app: FastAPI):
    """Custom OpenAPI generation function, aggregates downstream service documentation"""
    # Remove cache check to ensure real-time status of downstream services on every refresh
    # if app.openapi_schema:
    #     return app.openapi_schema

    # 1. Generate Gateway's own base documentation
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # 2. Define downstream service configuration
    # Format: (Service Name, Service Instance URLs, Route Prefix)
    downstream_services = [
        ("Auth Service", settings.auth_service_urls, "/api/v1/auth"),
        ("Host Service", settings.host_service_urls, "/api/v1/host"),
    ]

    # 3. Concurrently fetch and merge documentation
    timeout = 3.0

    with httpx.Client(timeout=timeout) as client:
        for name, urls, prefix in downstream_services:
            # Iterate through all instances of the service
            for url in urls:
                _fetch_and_merge(client, openapi_schema, name, url, prefix)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _fetch_and_merge(client: httpx.Client, base_schema: dict, name: str, url: str, prefix: str):
    """Fetch documentation from a single service instance and merge it"""
    try:
        docs_url = f"{url.rstrip('/')}/openapi.json"
        logger.info(f"Fetching OpenAPI docs from {name}: {docs_url}")

        response = client.get(docs_url)
        if response.status_code == 200:
            service_schema = response.json()
            _merge_schema(base_schema, service_schema, name, prefix, url)
            logger.info(f"Successfully merged {name} docs from {url}")
        else:
            logger.warning(f"Failed to fetch {name} docs from {url}: HTTP {response.status_code}")

    except Exception as e:
        logger.warning(f"Error fetching {name} docs from {url}: {e!s}")


def _merge_schema(base_schema: dict, service_schema: dict, service_name: str, prefix: str, service_url: str):
    """Merge service Schema into the main Schema"""

    # Extract IP:Port for display
    try:
        display_address = service_url.split("//")[1]
    except IndexError:
        display_address = service_url

    # Merge Paths
    service_paths = service_schema.get("paths", {})
    for path, methods in service_paths.items():
        # Tag Format: [Service Name @ IP:Port]
        tag_prefix = f"[{service_name} @ {display_address}]"

        for operation in methods.values():
            if "tags" in operation:
                operation["tags"] = [f"{tag_prefix} {tag}" for tag in operation["tags"]]
            else:
                operation["tags"] = [tag_prefix]

        # Merge paths directly
        # Note: If multiple instances return the same Path, the later one overwrites the earlier one
        # But since we want to confirm "visibility" and the Tag contains IP information
        # If Path is the same, does Swagger UI merge them?
        # In OpenAPI spec, paths is a Map, key is path string.
        # If two instances have the same path, key conflict occurs, resulting in overwrite.
        # Therefore, without modifying path key, only the last merge is retained.
        # This means users can only see interface definition of one instance, but Tag will show info of the last instance.
        # If user wants to see interfaces of both instances (e.g., for comparison), we need to modify Path Key.
        # Modification Plan: Append instance identifier to Path? e.g. /api/v1/auth/login -> /api/v1/auth/login?instance=8001 (pseudo query?)
        # Or /api/v1/auth/login (Instance 1)
        # No, Path must match actual request path.

        # Compromise Plan:
        # We merge in order. If content is identical, overwriting doesn't matter.
        # But we want Tag to reflect "aggregated multiple".
        # If overwritten, Tag also becomes Tag of the last instance.

        # Improvement: If Path already exists, try to merge Tag?
        if path in base_schema["paths"]:
            # Try to merge method-level tags
            existing_methods = base_schema["paths"][path]
            for method, operation in methods.items():
                if method in existing_methods:
                    # Append Tag, indicating interface also exists in current instance
                    existing_op = existing_methods[method]
                    # Avoid adding duplicate Tags (if logic allows)
                    # If we append Tag, Swagger UI will show this interface under two Tag groups!
                    # This is exactly what we want! User can see it in [Auth @ 8001] group, and also in [Auth @ 8002] group.
                    # And this is one Path/Method definition, referenced in two places.
                    new_tags = operation.get("tags", [])
                    existing_tags = existing_op.get("tags", [])
                    # Merge tags
                    combined_tags = list(set(existing_tags + new_tags))
                    existing_op["tags"] = combined_tags
                else:
                    # New method, add directly
                    existing_methods[method] = operation
        else:
            base_schema["paths"][path] = methods

    # Merge Components
    if "components" in service_schema:
        base_components = base_schema.setdefault("components", {})
        service_components = service_schema.get("components", {})

        for component_type, items in service_components.items():
            base_comp_type = base_components.setdefault(component_type, {})
            # Simple overwrite strategy
            base_comp_type.update(items)
