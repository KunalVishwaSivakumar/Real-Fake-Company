from crewai import Agent, Task, Crew
from crewai.tools import BaseTool  # ✅ Latest import method
import json
from dotenv import load_dotenv
import os

load_dotenv()


# --- Scanner Logic ---
class ScannerAgentLogic:
    def __init__(self, project_data):
        self.project_data = project_data
        self.issues = []

    def scan_emails(self):
        for email in self.project_data.get("emails", []):
            if "delay" in email["body"].lower():
                self.issues.append(f"[type_delay] {email['date']} - {email['subject']}: {email['body']}")

    def scan_site_logs(self):
        for log in self.project_data.get("site_logs", []):
            if "violation" in log["description"].lower():
                self.issues.append(f"[type_safety] {log['log_date']} - {log['description']}")

    def scan_inspection_reports(self):
        for report in self.project_data.get("inspection_reports", []):
            if "fail" in report["status"].lower():
                self.issues.append(f"[type_inspection] {report['date']} - {report['area']}: {report['comments']}")

    def run_scan(self):
        self.scan_emails()
        self.scan_site_logs()
        self.scan_inspection_reports()
        return "\n".join(self.issues)

# --- Load project data ---
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

# --- Define Tool using BaseTool ---
class ScannerTool(BaseTool):
    name: str = "ScanProjectData"
    description: str = "Scans project data to detect delays, safety violations, and inspection failures."

    def _run(self, **kwargs) -> str:
        scanner = ScannerAgentLogic(project_data)
        return scanner.run_scan()

# --- Agent with ScannerTool ---
scanner_agent = Agent(
    role="Scanner",
    goal="Detect project issues from logs, emails, and inspection data.",
    backstory="You're the first line of defense in spotting issues in a construction project.",
    tools=[ScannerTool()],
    verbose=True
)

# --- Task assigned to Scanner ---
scanner_task = Task(
    description=(
        "Scan all project-related documents including emails, site logs, and inspection reports. "
        "Identify any issues related to delays, safety violations, or failed inspections. "
        "Clearly tag each issue using the appropriate format such as [type_delay], [type_safety], or [type_inspection]."
    ),
    expected_output="List of tagged issues found in the project data.",
    agent=scanner_agent
)

# --- Run the Crew ---
crew = Crew(
    agents=[scanner_agent],
    tasks=[scanner_task],
    verbose=True
)



results = crew.kickoff()
with open("scanner_results.txt", "w") as out_file:
    out_file.write(str(results))
print("\n--- Scanner Output ---\n")
print(results)

