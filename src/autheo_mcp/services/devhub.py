"""
Autheo MCP DevHub / Hive Admin API client.
"""

from __future__ import annotations

from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.http import AutheoHttpClient


class DevHubClient:
    """
    Client for the Hive Admin / DevHub internal control-plane API.
    """

    def __init__(
        self,
        config: AutheoConfig | None = None,
        http: AutheoHttpClient | None = None,
    ) -> None:
        self.config = config or AutheoConfig()
        self.http = http or AutheoHttpClient(self.config)

    def _url(self, path: str) -> str:
        base = self.config.devhub_url.rstrip("/")
        return f"{base}{path}"

    async def health(self) -> dict[str, Any]:
        return {"status": await self.http.get(self._url("/healthz"))}

    async def list_nodes(self) -> list[dict[str, Any]]:
        return await self.http.get(self._url("/v1/nodes"))

    async def get_node(self, node_id: str) -> dict[str, Any]:
        nodes = await self.list_nodes()
        for node in nodes:
            if node.get("id") == node_id or node.get("name") == node_id:
                return node
        raise ValueError(f"Node not found: {node_id}")

    async def list_deployments(
        self,
        tenant: str | None = None,
    ) -> list[dict[str, Any]]:
        headers: dict[str, str] = {}
        if tenant:
            headers["x-hive-team"] = tenant
        result = await self.http.get(
            self._url("/deployments"),
            headers=headers,
        )
        if isinstance(result, list):
            return result
        return result.get("deployments", [])

    async def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        deployments = await self.list_deployments()
        for dep in deployments:
            if dep.get("id") == deployment_id:
                return dep
        raise ValueError(f"Deployment not found: {deployment_id}")

    async def get_build(self, build_id: str) -> dict[str, Any]:
        return await self.http.get(self._url(f"/v1/builds/{build_id}"))

    async def get_job_logs(
        self,
        job_id: str,
        tail: int = 200,
    ) -> dict[str, Any]:
        # Jobs are represented by builds in the DevHub/Hive API.
        build = await self.get_build(job_id)
        logs: list[str] = build.get("logs", [])
        if tail > 0:
            logs = logs[-tail:]
        return {
            "job_id": job_id,
            "tail": tail,
            "logs": logs,
        }

    async def get_job_artifacts(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        build = await self.get_build(job_id)
        return {
            "job_id": job_id,
            "artifacts": build.get("artifacts", []),
        }

    async def get_project(self, project_id: str) -> dict[str, Any]:
        return await self.http.get(
            self._url(f"/v1/projects/{project_id}/settings")
        )

    async def search_projects(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        deployments = await self.list_deployments()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for dep in deployments:
            project = dep.get("project", "")
            if project and query_lower in project.lower() and project not in seen:
                seen.add(project)
                results.append({
                    "project_id": project,
                    "deployment_id": dep.get("id"),
                    "alias": dep.get("alias"),
                })
        return results

    async def wallet_config(self) -> dict[str, Any]:
        return await self.http.get(
            self._url("/v1/billing/wallet-config")
        )

    async def cluster_status(self) -> dict[str, Any]:
        return await self.http.get(self._url("/v1/cluster"))

    async def overview(self) -> dict[str, Any]:
        return await self.http.get(self._url("/v1/overview"))

    async def security_posture(self) -> dict[str, Any]:
        return await self.http.get(self._url("/v1/security/posture"))
