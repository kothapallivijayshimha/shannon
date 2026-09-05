from .base import BaseAgent, safe_run


class ReconAgent(BaseAgent):
    """Multi-step reconnaissance agent.
    
    Detects intent from the task description and runs
    appropriate recon steps: subdomain, HTTP probe, or port scan.
    """

    name = "recon"

    async def run(self, task: str) -> dict:
        task_lower = task.lower()
        domain = task.split()[-1]

        if "subdomain" in task_lower:
            return await self._enum_subdomains(domain)

        if "http" in task_lower or "httpx" in task_lower:
            return await self._probe_http(domain)

        if "port" in task_lower or "naabu" in task_lower:
            return await self._scan_ports(domain)

        # Default: run full recon chain
        return await self._full_recon(domain)

    async def _enum_subdomains(self, domain: str) -> dict:
        results = safe_run("subfinder -d {} -silent", domain)
        return {
            "agent": "recon",
            "step": "subdomain_enum",
            "target": domain,
            "count": len(results),
            "results": results,
        }

    async def _probe_http(self, domain: str) -> dict:
        results = safe_run("echo {} | httpx -silent", domain)
        return {
            "agent": "recon",
            "step": "http_probe",
            "target": domain,
            "count": len(results),
            "results": results,
        }

    async def _scan_ports(self, domain: str) -> dict:
        results = safe_run("echo {} | naabu -silent", domain)
        return {
            "agent": "recon",
            "step": "port_scan",
            "target": domain,
            "count": len(results),
            "results": results,
        }

    async def _full_recon(self, domain: str) -> dict:
        subdomains = safe_run("subfinder -d {} -silent", domain)

        http_results = []
        if subdomains:
            http_results = safe_run("echo {} | httpx -silent", " ".join(subdomains))

        port_results = []
        if http_results:
            port_results = safe_run("echo {} | naabu -silent", http_results[0])

        return {
            "agent": "recon",
            "step": "full_recon",
            "target": domain,
            "subdomains": {"count": len(subdomains), "results": subdomains},
            "http_services": {"count": len(http_results), "results": http_results},
            "open_ports": {"count": len(port_results), "results": port_results},
        }
