import sys
import os
import asyncio
import json

# Add service root and project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Add service root and project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
# tests -> gateway-service
service_root = os.path.abspath(os.path.join(current_dir, ".."))
# gateway-service -> services -> project_root
project_root = os.path.abspath(os.path.join(service_root, "../.."))

sys.path.insert(0, service_root)
sys.path.insert(0, project_root)
# Also add project_root to get shared module if needed, although adding project_root should be enough
# But if 'shared' is a top level package, it should work.
# Let's ensure 'shared' is importable.

from app.core.config import settings
from app.services.proxy_service import ProxyService
from shared.common.exceptions import BusinessError


async def test_502_error_handling():
    print("🚀 Starting Gateway Error Handling Test...")

    # Initialize ProxyService
    proxy_service = ProxyService()

    # URL that definitely doesn't exist
    target_service = "nonexistent-service"
    target_path = "test/path"

    print(f"📡 Attempting to forward request to: {target_service}")

    try:
        # We expect this to fail with 502 because the service doesn't exist
        # and fallback defaults (localhost:8000 etc) might not differ but
        # let's try to ***REMOVED*** a port we know is closed or handled by logic

        # Actually, ProxyService uses ServiceDiscovery.
        # If we ask for a service that isn't in the map, it might error earlier.
        # Let's use 'auth' but ensure it points to a closed port.
        # We can override the auth service port in settings temporarily or just expect connection refused.

        # Force a connection error by using a closed port override if possible,
        # OR just rely on the fact that 'auth-service' (default host) is probably not resolvable
        # or reachable if we run this script in isolation on the host machine (unless 127.0.0.1:8001 is running).

        # Let's assume nothing is running on port 9999.
        # We can mock the service_discovery or just use a dummy service name if we modify the map?
        # ProxyService uses self.service_name_map.

        # Better approach: Mock get_service_url to return a dead URL
        async def mock_get_service_url(name):
            return "http://127.0.0.1:9999"  # Presumably closed

        proxy_service.get_service_url = mock_get_service_url

        await proxy_service.forward_request(
            service_name="auth", path="login", method="POST", headers={}, query_params={}
        )
        print("❌ Expected BusinessError was NOT raised!")

    except BusinessError as e:
        print("✅ BusinessError caught!")
        print(f"   Code: {e.code}")
        print(f"   Message: {e.message}")
        print(f"   HTTP Status: {e.http_status_code}")
        print(f"   Details: {e.details}")

        # Verify specific fields
        if e.http_status_code == 502:
            print("✅ HTTP Status Code is 502")
        else:
            print(f"❌ Unexpected HTTP Status Code: {e.http_status_code}")

        if e.code == "SERVICE_UNAVAILABLE" or e.code == 502:  # Depending on logic
            print(f"✅ Error Code is correct: {e.code}")
        else:
            print(f"❌ Unexpected Error Code: {e.code}")

    except Exception as e:
        print(f"❌ Unexpected exception type: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await proxy_service.close()


if __name__ == "__main__":
    asyncio.run(test_502_error_handling())
