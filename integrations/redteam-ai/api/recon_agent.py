import os
from typing import Dict, Any, List
from .tools.executor import ToolExecutor

class ReconAgent:
    """
    Upgraded Recon Agent. 
    Now uses the ToolExecutor to perform ACTUAL network scans 
    instead of relying on mock data.
    """
    
    def __init__(self, model_client=None):
        self.model_client = model_client
        self.executor = ToolExecutor()
        self.memory = {}

    def collect(self, raw_input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes real-world reconnaissance and organizes results.
        """
        target = raw_input_data.get("network_info", "")
        
        if not target:
            return {"error": "No target provided for recon."}

        # 1. Logic: Decide which tool to use based on target format
        # In a fully autonomous mode, the LLM would decide this. 
        # Here, we implement a professional decision tree.
        
        print(f"[ReconAgent] Initiating active scan on {target}...")
        
        # Use Nmap for initial surface discovery
        scan_result = self.executor.run("nmap_quick", target)
        
        if scan_result.success:
            print(f"[ReconAgent] Nmap scan completed successfully.")
            # We pass the actual stdout to the next agent
            assets = {
                "network_info": target,
                "scan_output": scan_result.stdout,
                "system_details": raw_input_data.get("system_details", "Unknown"),
                "logs": raw_input_data.get("logs", "No logs provided"),
                "verified": True
            }
        else:
            print(f"[ReconAgent] Scan failed: {scan_result.stderr}")
            assets = {
                "network_info": target,
                "scan_output": "Scan failed. Defaulting to passive analysis.",
                "system_details": raw_input_data.get("system_details", "Unknown"),
                "logs": raw_input_data.get("logs", "No logs provided"),
                "verified": False
            }

        # Persistent Storage
        self.memory.update(assets)
        return assets

    def prepare_for_next_agent(self) -> Dict[str, Any]:
        return {
            "recon_status": "COMPLETE",
            "findings": self.memory,
            "handoff_note": "Real-world scan data attached. Ready for vulnerability mapping."
        }
