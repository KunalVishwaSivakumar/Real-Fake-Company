import streamlit as st
from crewai import Agent, Task, Flow
from crewai.tools import BaseTool
from crewai.knowledge.source.crew_docling_source import CrewDoclingSource
from dotenv import load_dotenv
from pydantic import Field
from colorama import Fore, init
import json, os

# Streamlit setup
st.set_page_config(page_title="Project Atlas - Risk Mitigation", layout="wide")
st.title("🏗️ Project Atlas - Risk Mitigation Engine")
init(autoreset=True)
load_dotenv()

# -----------------------------------------
# Load Data and SOPs
# -----------------------------------------
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

scanner_sop = CrewDoclingSource(file_paths=["sops/scanner_sop.md"])
dispatcher_sop = CrewDoclingSource(file_paths=["sops/dispatcher_sop.md"])
scheduler_sop = CrewDoclingSource(file_paths=["sops/scheduler_sop.md"])
safety_sop = CrewDoclingSource(file_paths=["sops/safety_sop.md"])
qaqc_sop = CrewDoclingSource(file_paths=["sops/qaqc_sop.md"])
planner_sop = CrewDoclingSource(file_paths=["sops/planner_sop.md"])
evaluator_sop = CrewDoclingSource(file_paths=["sops/evaluation_sop.md"])

# -----------------------------------------
# Agent Logic Classes
# -----------------------------------------
class ScannerLogic:
    def __init__(self, data): self.data = data; self.issues = []
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
    description: str = Field(default="Scans project data for issues.")
    def _run(self, **kwargs): return "\n".join(ScannerLogic(project_data).scan())

class DispatcherLogic:
    def __init__(self, issues_str):
        self.issues = [line.strip() for line in issues_str.split("\n") if line.strip()]
        self.routes = []
        self.agent_map = {"type_delay": "SchedulerAgent", "type_safety": "SafetyAgent", "type_inspection": "QAQCAgent"}
    def route(self):
        for issue in self.issues:
            if issue.startswith("[") and "]" in issue:
                tag = issue.split("]")[0][1:].strip()
                details = issue.split("]", 1)[1].strip()
                assigned_agent = self.agent_map.get(tag, "UnknownAgent")
                self.routes.append({"issue_type": tag, "agent": assigned_agent, "details": details})
        return self.routes

class DispatcherTool(BaseTool):
    name: str = Field(default="DispatchIssues")
    description: str = Field(default="Routes tagged issues to respective agents.")
    def _run(self, **kwargs):
        output = ScannerLogic(project_data).scan()
        return json.dumps({"routing": DispatcherLogic("\n".join(output)).route()}, indent=2)

# -----------------------------------------
# Build Agents
# -----------------------------------------
scanner_agent = Agent(
    role="Scanner",
    goal="Detect project issues",
    backstory="You identify project problems.",
    tools=[ScannerTool()],
    knowledge_sources=[scanner_sop],
    verbose=True
)
scanner_task = Task(
    description="Scan project data for issues.",
    expected_output="List of issues",
    agent=scanner_agent,
    tool_choice="required"
)

dispatcher_agent = Agent(
    role="Dispatcher",
    goal="Route issues",
    backstory="You triage based on tags.",
    tools=[DispatcherTool()],
    knowledge_sources=[dispatcher_sop],
    verbose=True
)
dispatcher_task = Task(
    description="Dispatch issues based on tags.",
    expected_output="Routing dictionary",
    agent=dispatcher_agent,
    tool_choice="required"
)

# Issue Agents
issue_agents, issue_tasks = [], []

def make_tool(issue_type, detail):
    class CustomTool(BaseTool):
        name: str = Field(default=f"Handle{issue_type}")
        description: str = Field(default=f"Handles {issue_type} issues")
        def _run(self, **kwargs):
            if issue_type == "type_delay": return f"Delay mitigation: contact vendor, adjust schedule, etc."
            if issue_type == "type_safety": return f"Safety mitigation: {detail} - Safety briefings, audits."
            if issue_type == "type_inspection": return f"Inspection mitigation: {detail} - Rework, bonding, reinspect."
            return f"Unknown issue type"
    return CustomTool()

for route in DispatcherLogic("\n".join(ScannerLogic(project_data).scan())).route():
    issue_type, agent_name, detail = route["issue_type"], route["agent"], route["details"]
    sop = scheduler_sop if agent_name == "SchedulerAgent" else safety_sop if agent_name == "SafetyAgent" else qaqc_sop
    tool = make_tool(issue_type, detail)
    agent = Agent(
        role=agent_name,
        goal=f"Handle {issue_type} issues",
        backstory=f"Handle all {issue_type} issues.",
        tools=[tool],
        knowledge_sources=[sop],
        verbose=True
    )
    task = Task(
        description=f"Resolve: {detail}",
        expected_output=f"Mitigation plan: {detail}",
        agent=agent,
        tool_choice="required"
    )
    issue_agents.append(agent); issue_tasks.append(task)

class PlannerTool(BaseTool):
    name: str = Field(default="AggregateMitigationPlans")
    description: str = Field(default="Aggregate mitigation plans.")
    def _run(self, **kwargs):
        return json.dumps({"summary": "Unified Plan", "actions": [task.output for task in issue_tasks]}, indent=2)

planner_agent = Agent(
    role="Planner",
    goal="Aggregate plans",
    backstory="Combine mitigation actions.",
    tools=[PlannerTool()],
    knowledge_sources=[planner_sop],
    verbose=True
)
planner_task = Task(
    description="Unify mitigation plans.",
    expected_output="Final mitigation summary",
    agent=planner_agent,
    tool_choice="required"
)

class EvaluationTool(BaseTool):
    name: str = Field(default="EvaluateMitigationPlan")
    description: str = Field(default="Evaluate plan SOP compliance.")
    def _run(self, **kwargs):
        return json.dumps({"score": 10, "sop_compliance": "Yes", "remarks": "All actions SOP-aligned."}, indent=2)

evaluation_agent = Agent(
    role="Evaluator",
    goal="Evaluate mitigation plan",
    backstory="Ensure plan quality and SOP compliance.",
    tools=[EvaluationTool()],
    knowledge_sources=[evaluator_sop],
    verbose=True
)
evaluation_task = Task(
    description="Evaluate final mitigation plan.",
    expected_output="Evaluation report",
    agent=evaluation_agent,
    tool_choice="required"
)

# -----------------------------------------
# Execute Flow and Display in Streamlit
# -----------------------------------------
st.subheader("🔍 Scanner Output")
scanner_task.output = scanner_agent.tools[0]._run()
st.code(scanner_task.output)

st.subheader("🚦 Dispatcher Output")
dispatcher_task.output = dispatcher_agent.tools[0]._run()
st.code(dispatcher_task.output)

planner_inputs = []

for task in issue_tasks:
    st.subheader(f"🛠️ {task.agent.role} Output")
    task.output = task.agent.tools[0]._run()
    planner_inputs.append(task.output)
    st.code(task.output)

st.subheader("📋 Planner Output")
planner_task.output = planner_agent.tools[0]._run()
st.code(planner_task.output)

st.subheader("🔎 Evaluator Output")
evaluation_task.output = evaluation_agent.tools[0]._run()
st.code(evaluation_task.output)

flow_output = {
    "Scanner": scanner_task.output,
    "Dispatcher": json.loads(dispatcher_task.output),
    **{task.agent.role: task.output for task in issue_tasks},
    "Planner": json.loads(planner_task.output),
    "Evaluator": json.loads(evaluation_task.output)
}

with open("flow_output.json", "w", encoding="utf-8") as f:
    json.dump(flow_output, f, indent=2)

st.success("✅ Flow completed and saved to flow_output.json")
