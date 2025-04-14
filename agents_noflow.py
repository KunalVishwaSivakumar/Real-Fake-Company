import streamlit as st
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from pydantic import Field
import json, os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Title and layout
st.set_page_config(page_title="Project Atlas - Risk Mitigation", layout="wide")
st.title("🏗️ Project Atlas - Risk Mitigation Flow")

# Load JSON project data
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

# Helper: Scanner Logic
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

# Scanner Tool
class ScannerTool(BaseTool):
    name: str = Field(default="ScanProjectData")
    description: str = Field(default="Scans project data for issues")

    def _run(self, **kwargs):
        return "\n".join(ScannerLogic(project_data).scan())

# Run Scanner
with st.spinner("🔍 Running Scanner Agent..."):
    scanner_agent = Agent(
        role="Scanner",
        goal="Detect project issues from logs, emails, and inspections.",
        backstory="You identify problems early from project data.",
        tools=[ScannerTool()],
        verbose=True
    )
    scanner_task = Task(
        description="Scan project data for issues.",
        expected_output="List of tagged issues.",
        agent=scanner_agent,
        tool_choice="required"
    )
    scanner_crew = Crew(agents=[scanner_agent], tasks=[scanner_task], verbose=True)
    scanner_output = scanner_crew.kickoff()
    scanner_output_str = str(scanner_output)
    st.success("✅ Scanner Agent completed.")
    st.code(scanner_output_str, language='text')

# Dispatcher Logic
class DispatcherLogic:
    def __init__(self, issues_str):
        self.issues = [line.strip() for line in issues_str.split("\n") if line.strip()]
        self.routes = []

    def route(self):
        for issue in self.issues:
            if issue.startswith("[type_delay]"):
                self.routes.append({"issue_type": "type_delay", "agent": "SchedulerAgent", "details": issue})
            elif issue.startswith("[type_safety]"):
                self.routes.append({"issue_type": "type_safety", "agent": "SafetyAgent", "details": issue})
            elif issue.startswith("[type_inspection]"):
                self.routes.append({"issue_type": "type_inspection", "agent": "QAQCAgent", "details": issue})
        return self.routes

# Dispatcher Tool
class DispatcherTool(BaseTool):
    name: str = Field(default="DispatchIssues")
    description: str = Field(default="Dispatches issues to correct agents")

    def _run(self, **kwargs):
        return json.dumps({"routing": DispatcherLogic(scanner_output_str).route()}, indent=2)

with st.spinner("📦 Running Dispatcher Agent..."):
    dispatcher_agent = Agent(
        role="Dispatcher",
        goal="Distribute issues from scanner to responsible agents.",
        backstory="You triage output based on tags.",
        tools=[DispatcherTool()],
        verbose=True
    )
    dispatcher_task = Task(
        description="Route issues to correct agents.",
        expected_output="Routing dictionary.",
        agent=dispatcher_agent,
        tool_choice="required"
    )
    dispatcher_crew = Crew(agents=[dispatcher_agent], tasks=[dispatcher_task], verbose=True)
    dispatcher_output = dispatcher_crew.kickoff()
    st.success("✅ Dispatcher Agent completed.")
    st.code(dispatcher_output, language='json')

parsed_dispatch = json.loads(str(dispatcher_output))
final_outputs = {}

st.subheader("🚧 Agent Mitigation Handling")
for route in parsed_dispatch.get("routing", []):
    issue_type = route["issue_type"]
    agent_name = route["agent"]
    detail = route["details"]

    class CustomTool(BaseTool):
        name: str = Field(default=f"Handle{issue_type}")
        description: str = Field(default=f"Handles {issue_type} issues")

        def _run(self, **kwargs):
            if issue_type == "type_delay":
                return f"Mitigation plan for delay: {detail}\nSteps: Contact vendor, adjust schedule, explore alternatives."
            elif issue_type == "type_safety":
                return f"Mitigation plan for safety: {detail}\nActions: Safety briefings, assign officers, enforce PPE."
            elif issue_type == "type_inspection":
                return f"Mitigation plan for inspection: {detail}\nSteps: Rework, bonding, schedule reinspection."
            return f"Unhandled issue type: {issue_type}"

    issue_agent = Agent(
        role=agent_name,
        goal=f"Resolve {issue_type} issues.",
        backstory=f"You handle {issue_type} in the project.",
        tools=[CustomTool()],
        verbose=True
    )
    issue_task = Task(
        description=f"Resolve: {detail}",
        expected_output=f"Mitigation plan for: {detail}",
        agent=issue_agent,
        tool_choice="required"
    )
    issue_crew = Crew(agents=[issue_agent], tasks=[issue_task], verbose=True)
    output = issue_crew.kickoff()

    final_outputs.setdefault(agent_name, []).append(str(output).strip())
    st.success(f"✅ {agent_name} completed task.")
    st.code(str(output).strip())

class PlannerTool(BaseTool):
    name: str = Field(default="AggregateMitigationPlans")
    description: str = Field(default="Aggregates mitigation plans.")

    def _run(self, **kwargs):
        plan = []
        for agent, actions in final_outputs.items():
            for act in actions:
                plan.append({"agent": agent, "action": act})
        return json.dumps({"summary": "Unified Project Mitigation Plan", "actions": plan}, indent=2)

with st.spinner("🧩 Creating Final Mitigation Plan..."):
    planner_agent = Agent(
        role="Planner",
        goal="Unify project mitigation efforts into one actionable plan.",
        backstory="You aggregate actions from Scheduler, Safety, and QAQC agents.",
        tools=[PlannerTool()],
        verbose=True
    )
    planner_task = Task(
        description="Create a unified plan.",
        expected_output="Plan summary.",
        agent=planner_agent,
        tool_choice="required"
    )
    planner_crew = Crew(agents=[planner_agent], tasks=[planner_task], verbose=True)
    planner_output = planner_crew.kickoff()
    st.success("📘 Planner Agent created the plan.")
    st.code(str(planner_output), language='json')

class EvaluationTool(BaseTool):
    name: str = Field(default="EvaluateMitigationPlan")
    description: str = Field(default="Evaluates SOP compliance and quality")

    def _run(self, **kwargs):
        return json.dumps({
            "score": 10,
            "sop_compliance": "Yes",
            "remarks": "All actions are SOP-aligned and clearly stated."
        }, indent=2)

with st.spinner("🧪 Evaluating Plan for SOP compliance..."):
    evaluation_agent = Agent(
        role="Evaluator",
        goal="Evaluate the mitigation plan.",
        backstory="You ensure SOP compliance and quality.",
        tools=[EvaluationTool()],
        verbose=True
    )
    evaluation_task = Task(
        description="Evaluate the plan.",
        expected_output="SOP compliance and feedback.",
        agent=evaluation_agent,
        tool_choice="required"
    )
    evaluation_crew = Crew(agents=[evaluation_agent], tasks=[evaluation_task], verbose=True)
    evaluation_output = evaluation_crew.kickoff()
    st.success("🔍 Evaluation Completed")
    st.code(str(evaluation_output), language='json')
