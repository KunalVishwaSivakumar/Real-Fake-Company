# run_all_agents.py
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
import json, os
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# -----------------------------------------
# SCANNER AGENT
# -----------------------------------------
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

class ScannerLogic:
    def __init__(self, data):
        self.data = data
        self.issues = []

    def scan(self):
        for email in self.data.get("emails", []):
            if "delay" in email["body"].lower():
                self.issues.append(f"[type_delay] {email['date']} - {email['subject']}: {email['body']} | agent: SchedulerAgent")
        for log in self.data.get("site_logs", []):
            if "violation" in log["description"].lower():
                self.issues.append(f"[type_safety] {log['log_date']} - {log['description']} | agent: SafetyAgent")
        for report in self.data.get("inspection_reports", []):
            if "fail" in report["status"].lower():
                self.issues.append(f"[type_inspection] {report['date']} - {report['area']}: {report['comments']} | agent: QAQCAgent")
        return self.issues

class ScannerTool(BaseTool):
    name: str = Field(default="ScanProjectData")
    description: str = Field(default="Scans project data for delays, safety violations, and inspection issues.")

    def _run(self, **kwargs):
        return "\n".join(ScannerLogic(project_data).scan())

scanner_agent = Agent(
    role="Scanner",
    goal="Detect project issues from logs, emails, and inspections.",
    backstory="You identify problems early from project data.",
    tools=[ScannerTool()],
    verbose=True
)

scanner_task = Task(
    description="Scan project_atlas.json for issues with tags like [type_delay], [type_safety], [type_inspection]",
    expected_output="List of tagged issues.",
    agent=scanner_agent,
    tool_choice="required"
)

scanner_crew = Crew(agents=[scanner_agent], tasks=[scanner_task], verbose=True)
scanner_output = scanner_crew.kickoff()

scanner_output_str = str(scanner_output)
with open("scanner_results.txt", "w") as f:
    f.write(scanner_output_str)

# -----------------------------------------
# DISPATCHER AGENT
# -----------------------------------------
class DispatcherLogic:
    def __init__(self, issues_str):
        self.issues = [line.strip() for line in issues_str.split("\n") if line.strip()]
        self.routes = []

    def route(self):
        for issue in self.issues:
            if issue.startswith("[") and "]" in issue and "| agent:" in issue:
                tag = issue.split("]")[0][1:].strip()
                rest = issue.split("]", 1)[1].strip()
                details, agent_part = rest.split("| agent:", 1)
                self.routes.append({
                    "issue_type": tag,
                    "agent": agent_part.strip(),
                    "details": details.strip()
                })
        return self.routes

class DispatcherTool(BaseTool):
    name: str = Field(default="DispatchIssues")
    description: str = Field(default="Routes tagged issues to respective agents based on pre-assigned labels from scanner.")

    def _run(self, **kwargs):
        with open("scanner_results.txt", "r") as sf:
            raw_issues = sf.read()
        return json.dumps({"routing": DispatcherLogic(raw_issues).route()}, indent=2)

dispatcher_agent = Agent(
    role="Dispatcher",
    goal="Distribute issues from scanner to responsible agents.",
    backstory="You triage the output into agent responsibilities based on tags provided by scanner.",
    tools=[DispatcherTool()],
    verbose=True
)

dispatcher_task = Task(
    description="Route issues to appropriate agents as defined in the scanner output.",
    expected_output="A routing dictionary with agent assignments.",
    agent=dispatcher_agent,
    tool_choice="required"
)

dispatcher_crew = Crew(agents=[dispatcher_agent], tasks=[dispatcher_task], verbose=True)
dispatcher_output = dispatcher_crew.kickoff()

with open("dispatcher_results.json", "w") as f:
    f.write(str(dispatcher_output))

print("\n--- Scanner Output ---\n")
print(scanner_output_str)

print("\n--- Dispatcher Output ---\n")
print(dispatcher_output)
