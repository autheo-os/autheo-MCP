"""
Autheo MCP DevHub / Hive Admin API client.
"""

from __future__ import annotations

from typing import Any

from autheo_mcp.services.config import AutheoConfig
from autheo_mcp.services.http import AutheoHttpClient, path_id


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

    async def get_health(self) -> dict[str, Any]:
        try:
            data = await self.http.request("GET", self._url("/healthz"), text=True)
            return {"status": "healthy", "data": data}
        except Exception as exc:
            return {"status": "unhealthy", "error": str(exc)}

    async def list_nodes(self) -> dict[str, Any]:
        result = await self.http.get(self._url("/v1/nodes"))
        if isinstance(result, list):
            return {"nodes": result}
        return result

    async def get_node(self, node_id: str) -> dict[str, Any]:
        nodes = (await self.list_nodes()).get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id or node.get("name") == node_id:
                return node
        raise ValueError(f"Node not found: {node_id}")

    async def list_deployments(
        self,
        tenant: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if tenant:
            headers["x-hive-team"] = tenant
        result = await self.http.get(
            self._url("/deployments"),
            headers=headers,
        )
        if isinstance(result, list):
            return {"deployments": result}
        return result

    async def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        deployment_id = path_id(deployment_id)
        deployments = await self.list_deployments()
        for dep in deployments.get("deployments", []):
            if dep.get("id") == deployment_id:
                return dep
        raise ValueError(f"Deployment not found: {deployment_id}")

    async def get_build(self, build_id: str) -> dict[str, Any]:
        return await self.http.get(self._url(f"/v1/builds/{path_id(build_id)}"))

    async def get_job_logs(
        self,
        job_id: str,
        tail: int = 200,
    ) -> dict[str, Any]:
        if not 1 <= tail <= 2000:
            raise ValueError("tail must be between 1 and 2000")
        build = await self.get_build(job_id)
        logs = build.get("lines", build.get("logs", []))
        if isinstance(logs, str):
            logs = logs.splitlines()
        return {"job_id": job_id, "tail": tail, "logs": logs[-tail:], "source": "build"}

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
            self._url(f"/v1/projects/{path_id(project_id)}/settings")
        )

    async def search_projects(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        deployments = await self.list_deployments()
        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for dep in deployments.get("deployments", []):
            project = dep.get("project", "")
            if project and query_lower in project.lower() and project not in seen:
                seen.add(project)
                results.append({
                    "project_id": project,
                    "deployment_id": dep.get("id"),
                    "alias": dep.get("alias"),
                })
        return results

    async def estimate_deployment(
        self,
        runtime: str,
        cpu_milli: int,
        memory_mib: int,
        storage_mib: int,
        replicas: int = 1,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        raise NotImplementedError("The pinned DevHub has no /v1/estimate route; use a listing estimate")

    async def list_projects(self) -> dict[str, Any]:
        deployments = await self.list_deployments()
        names = sorted({d["project"] for d in deployments.get("deployments", []) if d.get("project")})
        return {"projects": [{"id": name, "name": name} for name in names],
                "source": "deployments", "complete_inventory": False}

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self.get_build(job_id)

    async def deployment_resources(self, deployment_id: str) -> dict[str, Any]:
        return await self.http.get(self._url(f"/v1/deployments/{path_id(deployment_id)}/resources"))

    async def mesh_health(self) -> dict[str, Any]:
        return await self.http.get(self._url("/v1/mesh"))

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

    async def close(self) -> None:
        await self.http.close()


def format_nodes(nodes_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Normalize a DevHub nodes response into a concise list.
    """

    nodes = nodes_payload.get("nodes", nodes_payload.get("items", []))
    result: list[dict[str, Any]] = []
    for node in nodes:
        cap = node.get("capacity") or {
            "cpu": node.get("cpu_cores"),
            "ram_gb": node["mem_total_mb"] / 1024 if node.get("mem_total_mb") is not None else None,
            "storage_gb": node.get("disk_total_gb"),
            "gpu": node.get("gpu_model"), "gpu_count": node.get("gpu_count"),
        }
        result.append(
            {
                "id": node.get("id") or node.get("node_id") or node.get("name"),
                "name": node.get("name"),
                "status": node.get("status", node.get("connectivity", "unknown")),
                "online": node.get("online", node.get("healthy", node.get("status") == "online")),
                "version": node.get("version"),
                "address": node.get("address"),
                "region": node.get("region"),
                "stake": node.get("stake"),
                "capacity": cap,
                "capacity_kind": "reported_hardware_not_reservable_supply",
            }
        )
    return result


def format_deployment(deployment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": deployment.get("id") or deployment.get("deployment_id"),
        "name": deployment.get("name"),
        "project": deployment.get("project"),
        "status": deployment.get("status"),
        "image": deployment.get("image"),
        "runtime": deployment.get("runtime"),
        "node_id": deployment.get("node_id"),
        "created_at": deployment.get("created_at"),
        "updated_at": deployment.get("updated_at"),
        "resources": deployment.get("resources"),
        "endpoints": deployment.get("endpoints"),
        "raw": deployment,
    }


def format_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": job.get("id") or job.get("job_id"),
        "status": job.get("status", job.get("state")),
        "project": job.get("project"),
        "deployment_id": job.get("deployment_id"),
        "created_at": job.get("created_at", job.get("started_ms")),
        "updated_at": job.get("updated_at", job.get("finished_ms")),
        "logs_url": job.get("logs_url"),
        "raw": job,
    }
