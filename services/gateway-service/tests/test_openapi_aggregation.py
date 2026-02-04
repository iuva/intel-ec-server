import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

# Use absolute import assuming pytest/python path is set correctly
from app.core.openapi import custom_openapi, _merge_schema


class TestOpenAPIAggregation(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI(title="Gateway Service", version="1.0.0")

    @patch("app.core.openapi.httpx.Client")
    @patch("app.core.openapi.get_openapi")
    def test_custom_openapi_success(self, mock_get_openapi, mock_client):
        """测试成功聚合多个服务文档，包括多实例"""
        # Mock Gateway 自身文档
        mock_get_openapi.return_value = {
            "openapi": "3.0.2",
            "info": {"title": "Gateway Service", "version": "1.0.0"},
            "paths": {"/health": {"get": {"summary": "Health Check", "tags": ["Health"]}}},
        }

        # Mock 下游服务响应
        # Instance 1
        mock_response_auth_1 = MagicMock()
        mock_response_auth_1.status_code = 200
        mock_response_auth_1.json.return_value = {"paths": {"/login": {"post": {"tags": ["Auth"], "summary": "Login"}}}}

        # Instance 2 (Same Code, Different Tag in final result due to IP)
        mock_response_auth_2 = MagicMock()
        mock_response_auth_2.status_code = 200
        mock_response_auth_2.json.return_value = {"paths": {"/login": {"post": {"tags": ["Auth"], "summary": "Login"}}}}

        mock_response_host = MagicMock()
        mock_response_host.status_code = 200
        mock_response_host.json.return_value = {
            "paths": {"/hosts": {"get": {"tags": ["Host"], "summary": "List Hosts"}}}
        }

        # 设置 Mock Client 的 get 方法返回值
        # 顺序: Auth1, Auth2, Host
        mock_client_instance = mock_client.return_value
        mock_client_instance.__enter__.return_value = mock_client_instance
        # 注意: 取决于 config.py 中 list 的顺序。
        mock_client_instance.get.side_effect = [mock_response_auth_1, mock_response_auth_2, mock_response_host]

        # Patch settings to return multiple instances
        with patch("app.core.openapi.settings") as mock_settings:
            mock_settings.auth_service_urls = ["http://127.0.0.1:8001", "http://127.0.0.1:8002"]
            mock_settings.host_service_urls = ["http://127.0.0.1:8003"]

            # 使用列表时，downstream_services 初始化是在 function 内还是 global?
            # 在 custom_openapi 函数内部:
            # downstream_services = [("Auth", settings.auth_service_urls, ...)]
            # 所以 Patch 生效。

            # 执行
            schema = custom_openapi(self.app)

        # 验证结果
        self.assertIsNotNone(schema)
        paths = schema["paths"]

        # 验证 Path 合并
        self.assertIn("/login", paths)
        self.assertIn("/hosts", paths)

        # 验证 Tags 包含所有实例
        # /login 应该包含 [Auth Service @ 127.0.0.1:8001] 和 [Auth Service @ 127.0.0.1:8002]
        # 注意：由于路径合并逻辑，同一个 operation 对象的 tags 列表会被累加
        login_tags = paths["/login"]["post"]["tags"]
        print(f"DEBUG: Login Tags: {login_tags}")

        self.assertTrue(any("127.0.0.1:8001" in tag for tag in login_tags), "Instance 8001 tag missing")
        self.assertTrue(any("127.0.0.1:8002" in tag for tag in login_tags), "Instance 8002 tag missing")

        # 验证 Host
        host_tags = paths["/hosts"]["get"]["tags"]
        self.assertTrue(any("127.0.0.1:8003" in tag for tag in host_tags))

    @patch("app.core.openapi.httpx.Client")
    @patch("app.core.openapi.get_openapi")
    def test_custom_openapi_partial_failure(self, mock_get_openapi, mock_client):
        """测试部分服务不可用时的容错性"""
        mock_get_openapi.return_value = {
            "openapi": "3.0.2",
            "info": {"title": "Gateway", "version": "1.0"},
            "paths": {},
        }

        # Auth 1 成功
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"paths": {"/auth": {"get": {}}}}

        # Auth 2 失败 (Response Error)
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500

        # Host 失败 (Exception)

        mock_client_instance = mock_client.return_value
        mock_client_instance.__enter__.return_value = mock_client_instance

        # get 调用顺序：Auth1 -> Auth2 -> Host
        # 第三个调用抛出异常
        mock_client_instance.get.side_effect = [mock_response_ok, mock_response_fail, Exception("Connection Error")]

        with patch("app.core.openapi.settings") as mock_settings:
            mock_settings.auth_service_urls = ["http://127.0.0.1:8001", "http://127.0.0.1:8002"]
            mock_settings.host_service_urls = ["http://127.0.0.1:8003"]

            schema = custom_openapi(self.app)

        # 验证
        self.assertIn("/auth", schema["paths"])
        # Auth 1 tag 应该在
        # Auth 2 tag 应该不在


if __name__ == "__main__":
    unittest.main()
