import os
from typing import Dict, Any, List

from .recon_agent import ReconAgent
from .vulnerability_agent import VulnerabilityAgent
from .simulation_agent import SimulationAgent
from .strategic_ai import AdvancedSecurityAI
from .database import IntelligenceDatabase
from .report_generator import SecurityReportGenerator

class RedTeamProjectOrchestrator:
    """
    Red Team AI Project Orchestrator (V4 - Report Integrated).
    Manages the loop from reconnaissance to la professional audit report.
    """
    
    def __init__(self, model_client=None):
        self.model_client = model_client
        self.db = IntelligenceDatabase()
        
        self.recon_agent = ReconAgent(model_client=model_client)
        self.vuln_agent = VulnerabilityAgent(model_client=model_client)
        self.sim_agent = SimulationAgent(model_client=model_client)
        self.strategist = AdvancedSecurityAI(model_client=model_client)
        
        self.report_prompt = (
            "You are the Red Team AI Project Lead. Synthesize a final executive report.\n"
            "Provide an overall Threat Score, Vulnerability Summary, and a prioritized Mitigation Roadmap."
        )

    def run_full_assessment(self, network_info: str, system_details: str, logs: str) -> str:
        """
        Executes the pipeline and generates a professional Markdown audit report.
        """
        if not self.model_client:
            return "Error: No model client configured."

        target_key = network_info.split(',')[0].strip()
        
        # 1. Recon
        assets = self.recon_agent.collect({"network_info": network_info, "system_details": system_details, "logs": logs})
        self.db.store_recon(target_key, assets)

        # 2. Vuln
        vulns = self.vuln_agent.analyze_assets(assets)
        for v in vulns:
            if isinstance(v, dict):
                self.db.store_vulnerability(target_key, v.get('severity', 'Unknown'), v.get('name', 'Unknown'), v.get('description', ''))

        # 3. Simulation
        simulation = self.sim_agent.simulate_attack_scenario(vulns, assets)
        if isinstance(simulation, dict):
            self.db.store_attack_path(target_key, simulation.get('attack_paths', []), simulation.get('impact_analysis', 'Unknown'))

        # 4. Synthesis & Report Generation
        combined_evidence = f"Assets: {assets}\nFindings: {vulns}\nSim: {simulation}"
        final_summary = self.model_client.generate(f"{self.report_prompt}\n\nData: {combined_evidence}")

        # INTEGRATION: Use the Professional Report Generator
        report_gen = SecurityReportGenerator(target_key)
        report_gen.add_section("Executive Summary", final_summary, "executive")
        report_gen.add_section("Technical Findings", str(vulns), "technical")
        report_gen.add_section("Simulated Attack Path", str(simulation), "technical")
        report_gen.add_section("Remediation Plan", "Apply patches and disable SMBv1 immediately.", "remediation")

        return report_gen.generate_markdown()
