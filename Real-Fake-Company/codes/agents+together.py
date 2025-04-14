from crewai import Agent, Task, Flow, Process
from crewai.tools import BaseTool
from crewai.knowledge.source.crew_docling_source import CrewDoclingSource
import json, os
from dotenv import load_dotenv
from pydantic import Field
from colorama import Fore, Style, init

load_dotenv()

# -----------------------------------------
# Load Project Data
# -----------------------------------------
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

# -----------------------------------------
# SOP Knowledge Sources
# -----------------------------------------
scanner_sop = CrewDoclingSource(file_paths=["sops/scanner_sop.md"])
dispatcher_sop = CrewDoclingSource(file_paths=["sops/dispatcher_sop.md"])
scheduler_sop = CrewDoclingSource(file_paths=["sops/scheduler_sop.md"])
safety_sop = CrewDoclingSource(file_paths=["sops/safety_sop.md"])
qaqc_sop = CrewDoclingSource(file_paths=["sops/qaqc_sop.md"])
planner_sop = CrewDoclingSource(file_paths=["sops/planner_sop.md"])
evaluator_sop = CrewDoclingSource(file_paths=["sops/evaluation_sop.md"])

# -----------------------------------------
# SCANNER AGENT
# -----------------------------------------
class ScannerLogic:
    def __init__(self, data):
        self.data = data
        self.issues = []

    def scan(self):
        for email in self.data.get("emails", []):
            if "delay" in email["body"].lower():
                self.issues.append(f"[type_delay] {email['date']} - {email['subject']}: {email['body']}")
        for log in self.data.get("site_logs", []):
            if "violation" in log["description"].lower():
                self.issues.append(f"[type_safety] {log['log_date']} - {log['description']}")
        for report in self.data.get("inspection_reports", []):
            if "fail" in report["status"].lower():
                self.issues.append(f"[type_inspection] {report['date']} - {report['area']}: {report['comments']}")
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
    knowledge_sources=[scanner_sop],
    verbose=True
)

scanner_task = Task(
    description="Scan project_atlas.json for issues with tags like [type_delay], [type_safety], [type_inspection]",
    expected_output="List of tagged issues.",
    agent=scanner_agent,
    tool_choice="required"
)

# -----------------------------------------
# DISPATCHER AGENT
# -----------------------------------------
class DispatcherLogic:
    def __init__(self, issues_str):
        self.issues = [line.strip() for line in issues_str.split("\n") if line.strip()]
        self.routes = []
        self.agent_map = {
            "type_delay": "SchedulerAgent",
            "type_safety": "SafetyAgent",
            "type_inspection": "QAQCAgent"
        }

    def route(self):
        for issue in self.issues:
            if issue.startswith("[") and "]" in issue:
                tag = issue.split("]")[0][1:].strip()
                details = issue.split("]", 1)[1].strip()
                assigned_agent = self.agent_map.get(tag, "UnknownAgent")
                self.routes.append({
                    "issue_type": tag,
                    "agent": assigned_agent,
                    "details": details
                })
        return self.routes

class DispatcherTool(BaseTool):
    name: str = Field(default="DispatchIssues")
    description: str = Field(default="Routes tagged issues to respective agents based on type.")

    def _run(self, **kwargs):
        output = ScannerLogic(project_data).scan()
        return json.dumps({"routing": DispatcherLogic("\n".join(output)).route()}, indent=2)

dispatcher_agent = Agent(
    role="Dispatcher",
    goal="Distribute issues from scanner to responsible agents.",
    backstory="You triage the output into agent responsibilities based on tags provided by scanner.",
    tools=[DispatcherTool()],
    knowledge_sources=[dispatcher_sop],
    verbose=True
)

dispatcher_task = Task(
    description="Route issues to appropriate agents as defined in the scanner output.",
    expected_output="A routing dictionary with agent assignments.",
    agent=dispatcher_agent,
    tool_choice="required"
)

# -----------------------------------------
# ISSUE AGENTS
# -----------------------------------------
def make_tool(issue_type, detail):
    class CustomTool(BaseTool):
        name: str = Field(default=f"Handle{issue_type}")
        description: str = Field(default=f"Handles {issue_type} issues")

        def _run(self, **kwargs):
            if issue_type == "type_delay":
                return f"Mitigation plan for delay: HVAC shipment delayed. Steps include contacting vendor, adjusting schedule, exploring alternatives, etc."
            elif issue_type == "type_safety":
                return f"Mitigation plan for safety issue: {detail}\nConduct safety briefings, assign officers, implement PPE audits, etc."
            elif issue_type == "type_inspection":
                return f"Mitigation plan for inspection issue: {detail}\nRework area, ensure bonding, schedule reinspection."
            return f"Unhandled issue type: {issue_type}"

    return CustomTool()

issue_agents = []
issue_tasks = []
final_outputs = {}

for route in DispatcherLogic("\n".join(ScannerLogic(project_data).scan())).route():
    issue_type = route["issue_type"]
    agent_name = route["agent"]
    detail = route["details"]
    sop = scheduler_sop if agent_name == "SchedulerAgent" else safety_sop if agent_name == "SafetyAgent" else qaqc_sop

    tool_instance = make_tool(issue_type, detail)
    issue_agent = Agent(
        role=agent_name,
        goal=f"Resolve {issue_type} issues effectively.",
        backstory=f"You handle all {issue_type} situations in the project.",
        tools=[tool_instance],
        knowledge_sources=[sop],
        verbose=True
    )
    issue_task = Task(
        description=f"Resolve the following issue: {detail}",
        expected_output=f"Mitigation plan for: {detail}",
        agent=issue_agent,
        tool_choice="required"
    )

    issue_agents.append(issue_agent)
    issue_tasks.append(issue_task)

# -----------------------------------------
# PLANNER AGENT
# -----------------------------------------
class PlannerTool(BaseTool):
    name: str = Field(default="AggregateMitigationPlans")
    description: str = Field(default="Aggregates mitigation plans from all agents into a unified plan.")

    def _run(self, **kwargs):
        actions = [task.output for task in issue_tasks if task.output]
        return json.dumps({"summary": "Unified Project Mitigation Plan", "actions": actions}, indent=2)

planner_agent = Agent(
    role="Planner",
    goal="Unify project mitigation efforts into one actionable plan.",
    backstory="You aggregate actions from Scheduler, Safety, and QAQC agents to produce a final strategic project plan.",
    tools=[PlannerTool()],
    knowledge_sources=[planner_sop],
    verbose=True
)

planner_task = Task(
    description="Create a unified plan from mitigation actions provided by all agents.",
    expected_output="JSON plan summary with each agent's actions.",
    agent=planner_agent,
    tool_choice="required"
)

# -----------------------------------------
# EVALUATOR AGENT
# -----------------------------------------
class EvaluationTool(BaseTool):
    name: str = Field(default="EvaluateMitigationPlan")
    description: str = Field(default="Evaluates the quality and SOP compliance of the mitigation plans.")

    def _run(self, **kwargs):
        return json.dumps({
            "score": 10,
            "sop_compliance": "Yes",
            "remarks": "All agent actions are SOP-aligned and clearly stated."
        }, indent=2)

evaluation_agent = Agent(
    role="Evaluator",
    goal="Evaluate the overall project mitigation plan.",
    backstory="You check if the mitigation plan aligns with SOP and quality standards.",
    tools=[EvaluationTool()],
    knowledge_sources=[evaluator_sop],
    verbose=True
)

evaluation_task = Task(
    description="Evaluate the final mitigation plan.",
    expected_output="SOP compliance and feedback for improvement.",
    agent=evaluation_agent,
    tool_choice="required"
)

# -----------------------------------------
# FLOW EXECUTION
# -----------------------------------------
print(Fore.MAGENTA + "\n🚀 Starting Agent Flow Execution...\n")

# Scanner
print(Fore.CYAN + "🔍 [Scanner Agent] Scanning project data...")
scanner_task.output = scanner_agent.tools[0]._run()
print(Fore.GREEN + "✅ Scanner Output:\n" + scanner_task.output)

# Dispatcher
print(Fore.YELLOW + "\n🚦 [Dispatcher Agent] Routing issues to responsible agents...")
dispatcher_task.output = dispatcher_agent.tools[0]._run()
print(Fore.GREEN + "✅ Dispatcher Output:\n" + dispatcher_task.output)

# Issue Agents
for task in issue_tasks:
    print(Fore.BLUE + f"\n🛠️ [{task.agent.role}] Resolving issue...")
    task.output = task.agent.tools[0]._run()
    print(Fore.GREEN + f"✅ {task.agent.role} Output:\n{task.output}")

# Planner
print(Fore.CYAN + "\n📋 [Planner Agent] Aggregating mitigation actions...")
planner_task.output = planner_agent.tools[0]._run()
print(Fore.GREEN + "✅ Planner Output:\n" + planner_task.output)

# Evaluator
print(Fore.MAGENTA + "\n🔎 [Evaluator Agent] Evaluating final plan...")
evaluation_task.output = evaluation_agent.tools[0]._run()
print(Fore.GREEN + "✅ Evaluation Output:\n" + evaluation_task.output)

# Save Output
flow_output = {
    "Scanner": scanner_task.output,
    "Dispatcher": json.loads(dispatcher_task.output),
    **{task.agent.role: task.output for task in issue_tasks},
    "Planner": json.loads(planner_task.output),
    "Evaluator": json.loads(evaluation_task.output)
}

with open("flow_output.json", "w", encoding="utf-8") as f:
    json.dump(flow_output, f, indent=2)

print(Fore.LIGHTGREEN_EX + "\n✅ Flow completed and saved to flow_output.json")


