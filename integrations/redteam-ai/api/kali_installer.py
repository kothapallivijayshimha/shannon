import subprocess
import logging
import sys
from typing import List, Dict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("KaliToolbox")

class KaliIndustrialInstaller:
    """
    Enterprise-grade installer for the Top 50 Kali Linux security tools.
    Categorized by the Red Team pipeline phases.
    """
    
    # Organized by Pipeline Phase for Autonomous AI mapping
    TOOL_MANIFEST = {
        "01_Reconnaissance": [
            "nmap", "dnsenum", "dirb", "gobuster", "nikto", "masscan", 
            "whois", "dig", "recon-ng", "theharvester", "shodan", "amass"
        ],
        "02_Vulnerabilities": [
            "metasploit-framework", "searchsploit", "openvas", "nmap",
            "nuclei", "unix-privesc-check", "linpeas", "winpeas"
        ],
        "03_Web_Analysis": [
            "burpsuite", "sqlmap", "wfuzz", "commix", "zap", "dirsearch",
            "photon", "xsstrike", "katana", "gau"
        ],
        "04_Password_Cracking": [
            "john", "hashcat", "hydra", "medusa", "cewl", "crunch"
        ],
        "05_Privilege_Escalation": [
            "mimikatz", "bloodhound", "powerview", "pwncat-cs", "beEF"
        ],
        "06_Sniffing_Spoofing": [
            "wireshark", "bettercap", "ettercap", "tcpdump", "responder"
        ],
        "07_Post_Exploitation": [
            "metasploit-framework", "socat", "netcat-traditional", "impacket"
        ],
        "08_Wireless_SDR": [
            "aircrack-ng", "kismet", "reaCtaPact", "wifite"
        ]
    }

    def __init__(self):
        self.installed_tools = []
        self.failed_tools = []

    def _install_package(self, package: str) -> bool:
        """Internal method to execute apt install."""
        logger.info(f"Deploying toolset: {package}...")
        try:
            # Use sudo and -y for non-interactive automation
            subprocess.run(
                ["sudo", "apt-get", "install", "-y", package],
                check=True,
                capture_output=True,
                text=True
            )
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Deployment failed for {package}: {e.stderr}")
            return False

    def deploy_full_arsenal(self):
        """
        Deploys all 50+ tools defined in the manifest.
        """
        logger.info("INITIATING INDUSTRIAL KALI TOOLSET DEPLOYMENT...")
        
        # First, update the system repository
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            logger.error("Failed to update apt repositories. Deployment may fail.")

        report = {}
        for category, tools in self.TOOL_MANIFEST.items():
            logger.info(f"Processing Category: {category}")
            category_success = []
            for tool in tools:
                if self._install_package(tool):
                    category_success.append(tool)
                    self.installed_tools.append(tool)
                else:
                    self.failed_tools.append(tool)
            report[category] = category_success

        self._print_final_report(report)

    def _print_final_report(self, report: Dict[str, List[str]]):
        print("\n" + "="*60)
        print(" RED TEAM AI - TOOLSET DEPLOYMENT SUMMARY")
        print("="*60)
        for cat, tools in report.items():
            print(f" {cat}: {len(tools)} tools installed")
            for t in tools:
                print(f"  [✓] {t}")
        
        print("-" * 60)
        print(f"Total Successful: {len(self.installed_tools)}")
        print(f"Total Failed: {len(self.failed_tools)}")
        if self.failed_tools:
            print(f"Failed Tools: {', '.join(self.failed_tools)}")
        print("="*60)

if __name__ == "__main__":
    # Check if running as root/sudo
    installer = KaliIndustrialInstaller()
    installer.deploy_full_arsenal()
