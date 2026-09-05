import os
from typing import Dict, List, Any

class SimulationAgent:
    """
    Simulation Agent focused on offensive strategy and threat modeling.
    Transforms static vulnerabilities into dynamic attack paths by 
    simulating a sophisticated adversary's reasoning.
    """
    
    def __init__(self, model_client=None):
        # model_client for high-level reasoning and strategy generation
        self.model_client = model_client
        self.system_prompt = (
            "You are the Simulation Agent. Your role is to think like an advanced attacker.\n\n"
            "Tasks:\n"
            "1. Simulate attacker reasoning: Given a set of vulnerabilities, how would an adversary actually exploit them?\n"
            "2. Identify attack paths: Map the sequence of steps (chaining) from initial access to the target objective (e.g., Domain Admin, Data Exfiltration).\n"
            "3. Explain risks: Detail the real-world impact of these paths (e.g., 'Could lead to full ransomware deployment across the subnet').\n"
        )

    def simulate_attack_scenario(self, vulnerability_data: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates potential attack paths based on identified vulnerabilities and system context.
        """
        if not self.model_client:
            # Return a simulated attack chain for demonstration purposes
            return self._generate_mock_simulation(vulnerability_data)

        # Construct a complex prompt combining findings and system context
        prompt = (
            f"{self.system_prompt}\n\n"
            f"Vulnerabilities Identified:\n{vulnerability_data}\n\n"
            f"System/Network Context:\n{context}"
        )
        
        try:
            response = self.model_client.generate(prompt)
            return {"simulation_result": response}
        except Exception as e:
            return {"error": f"Simulation failed: {str(e)}"}

    def _generate_mock_simulation(self, vulns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Creates a plausible attack chain based on detected vulnerabilities.
        """
        paths = []
        risks = []
        
        # Extract vulnerability names for simple keyword matching
        vn_list = [v.get('name', '') for v in vulns]
        
        if any("SMB" in name for name in vn_list) and any("SSH" in name for name in vn_list):
            paths.append([
                "Step 1: Initial access via SSH brute-force or leaked credential.",
                "Step 2: Pivot to internal server using the established SSH tunnel.",
                "Step 3: Execute Remote Code Execution (RCE) via Outdated SMB on the internal server.",
                "Step 4: Elevate privileges to SYSTEM/Root."
            ])
            risks.append("Full system compromise and lateral movement across the internal network.")
        elif any("SSH" in name for name in vn_list):
            paths.append([
                "Step 1: Target SSH port for credential stuffing.",
                "Step 2: Gain limited shell access to a single user account."
            ])
            risks.append("Unauthorized access to user data and potential for further local privilege escalation.")
        else:
            paths.append(["No viable attack chain could be simulated from the provided vulnerabilities."])
            risks.append("Low risk of immediate compromise, but surface remains open.")

        return {
            "attacker_reasoning": "The adversary will likely look for the path of least resistance, targeting the outdated SMB service after gaining a foothold via SSH.",
            "attack_paths": paths,
            "impact_analysis": risks
        }

if __name__ == "__main__":
    # Simulation: VulnerabilityAgent -> SimulationAgent
    sim_agent = SimulationAgent()
    
    # Mock data from VulnerabilityAgent
    mock_vulns = [
        {"name": "Outdated SMB Protocol", "severity": "High"},
        {"name": "SSH Service Exposure", "severity": "Medium"}
    ]
    mock_context = {"network": "Internal LAN", "target": "File Server"}
    
    print("--- Starting Attack Simulation Phase ---")
    result = sim_agent.simulate_attack_scenario(mock_vulns, mock_context)
    
    print(f"\nReasoning: {result.get('attacker_reasoning')}")
    print("\nAttack Path:")
    for i, step in enumerate(result.get('attack_paths', [])[0]):
        print(f"  {step}")
    
    print(f"\nImpact: {result.get('impact_analysis')}")
