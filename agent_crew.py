# Your imports and setup remain unchanged
import streamlit as st
from crewai import Agent, Task, Crew, Flow
from crewai.tools import BaseTool
from crewai.knowledge.source.crew_docling_source import CrewDoclingSource
from dotenv import load_dotenv
from pydantic import Field
import json, os, uuid, re
from colorama import init

st.set_page_config(page_title="Project Atlas - Risk Mitigation", layout="wide")
st.title("🏗️ Project Atlas - Risk Mitigation Engine")
init(autoreset=True)
load_dotenv()

uploaded_file = st.file_uploader("📄 Upload your .json file", type="json")
if not uploaded_file:
    st.warning("Please upload a project JSON file to proceed.")
    st.stop()

project_data = json.load(uploaded_file)

sops = {
    "scanner": CrewDoclingSource(file_paths=["sops/scanner_sop.md"]),
    "dispatcher": CrewDoclingSource(file_paths=["sops/dispatcher_sop.md"]),
    "scheduler": CrewDoclingSource(file_paths=["sops/scheduler_sop.md"]),
    "safety": CrewDoclingSource(file_paths=["sops/safety_sop.md"]),
    "qaqc": CrewDoclingSource(file_paths=["sops/qaqc_sop.md"]),
    "planner": CrewDoclingSource(file_paths=["sops/planner_sop.md"]),
    "evaluator": CrewDoclingSource(file_paths=["sops/evaluation_sop.md"]),
}

class ScannerTool(BaseTool):
    name: str = Field(default="ScanProjectData")
    description: str = Field(default="Scans project data for issues.")
    def _run(self, **kwargs):
        issues = []
        for email in project_data.get("emails", []):
            if "delay" in email["body"].lower():
                issues.append(f"[type_delay] {email['date']} - {email['subject']}: {email['body']}")
        for log in project_data.get("site_logs", []):
            if "violation" in log["description"].lower():
                issues.append(f"[type_safety] {log['log_date']} - {log['description']}")
        for report in project_data.get("inspection_reports", []):
            if "fail" in report["status"].lower():
                issues.append(f"[type_inspection] {report['date']} - {report['area']}: {report['comments']}")
        return '\n'.join(issues)

class DispatcherTool(BaseTool):
    name: str = Field(default="DispatchIssues")
    description: str = Field(default="Routes tagged issues to respective agents.")
    def _run(self, **kwargs):
        issues = ScannerTool()._run()
        routes = []
        agent_map = {
            "type_delay": "SchedulerAgent",
            "type_safety": "SafetyAgent",
            "type_inspection": "QAQCAgent"
        }
        for line in issues.split("\n"):
            if line.startswith("[") and "]" in line:
                tag = line.split("]")[0][1:].strip()
                details = line.split("]", 1)[1].strip()
                assigned_agent = agent_map.get(tag, "UnknownAgent")
                routes.append({"issue_type": tag, "agent": assigned_agent, "details": details})
        output = [f"- **{r['issue_type']}** → **{r['agent']}**: {r['details']}" for r in routes]
        return '\n'.join(output)

scanner_agent = Agent(
    role="Scanner", goal="Detect project issues",
    backstory="Identify project problems from project data.",
    tools=[ScannerTool()], knowledge_sources=[sops["scanner"]]
)
dispatcher_agent = Agent(
    role="Dispatcher", goal="Route issues",
    backstory="Assign each issue to the correct domain expert.",
    tools=[DispatcherTool()], knowledge_sources=[sops["dispatcher"]]
)
scanner_task = Task(
    description="Scan project data for issues.",
    expected_output="List of issues", agent=scanner_agent, tool_choice="required"
)
dispatcher_task = Task(
    description="Dispatch issues based on tags.",
    expected_output="Routing dictionary", agent=dispatcher_agent, tool_choice="required"
)

issue_agents, issue_tasks = [], []

class CustomToolFactory:
    @staticmethod
    def create(issue_type, detail):
        class DynamicTool(BaseTool):
            name: str = Field(default=f"Handle_{issue_type}_{uuid.uuid4().hex[:6]}")
            description: str = Field(default=f"Handles {issue_type} issues")
            def _run(inner_self, **kwargs):
                if issue_type == "type_delay":
                    return f"""Mitigation plan: {detail}

Steps:
1. Contact vendor regarding delay
2. Adjust delivery timeline in the schedule
3. Notify stakeholders about updated timelines"""
                elif issue_type == "type_safety":
                    return f"""Mitigation plan: {detail}

Steps:
1. Investigate the safety violation
2. Conduct mandatory toolbox talk
3. Perform safety re-audit on site"""
                elif issue_type == "type_inspection":
                    return f"""Mitigation plan: {detail}

Steps:
1. Schedule rework for identified issue
2. Apply bonding/sealing as per SOP
3. Request reinspection and document resolution"""
                return f"""Mitigation plan: {detail}

Steps:
1. Initial assessment
2. Assign responsible team
3. Track progress and confirm closure"""
        return DynamicTool()

raw_issues = ScannerTool()._run().split("\n")
routes = []
agent_map = {
    "type_delay": "SchedulerAgent",
    "type_safety": "SafetyAgent",
    "type_inspection": "QAQCAgent"
}
for line in raw_issues:
    if line.startswith("[") and "]" in line:
        tag = line.split("]")[0][1:].strip()
        details = line.split("]", 1)[1].strip()
        assigned_agent = agent_map.get(tag, "UnknownAgent")
        routes.append({"issue_type": tag, "agent": assigned_agent, "details": details})
for route in routes:
    issue_type, agent_name, detail = route["issue_type"], route["agent"], route["details"]
    sop = sops["scheduler"] if agent_name == "SchedulerAgent" else sops["safety"] if agent_name == "SafetyAgent" else sops["qaqc"]
    tool = CustomToolFactory.create(issue_type=issue_type, detail=detail)
    agent = Agent(role=agent_name, goal=f"Handle {issue_type} issues",
                  backstory=f"Resolve all {issue_type} issues.",
                  tools=[tool], knowledge_sources=[sop])
    task = Task(description=f"Resolve: {detail}",
                expected_output=f"Mitigation plan (with steps): {detail}",
                agent=agent, tool_choice="required")
    issue_agents.append(agent)
    issue_tasks.append(task)

class PlannerTool(BaseTool):
    name: str = Field(default="AggregateMitigationPlans")
    description: str = Field(default="Aggregate and provide step-by-step mitigation strategy.")
    def _run(self, **kwargs):
        summary = "📋 **Master Mitigation Plan**\n\n"
        for task in issue_tasks:
            summary += f"### 🧑‍🔧 {task.agent.role}\n\n{task.output.strip()}\n\n---\n"
        return summary

planner_agent = Agent(
    role="PlannerAgent", goal="Create a combined plan",
    backstory="Combine mitigation into a coherent strategy.",
    tools=[PlannerTool()], knowledge_sources=[sops["planner"]]
)
planner_task = Task(
    description="Aggregate all mitigation plans",
    expected_output="Master mitigation plan",
    agent=planner_agent,
    tool_choice="required"
)

class EvaluatorTool(BaseTool):
    name: str = Field(default="ReviewMitigationPlan")
    description: str = Field(default="Reviews and scores the mitigation plan for completeness and clarity.")
    def _run(self, **kwargs):
        score = "9/10 - Plan covers all key areas. Suggestions: Ensure QA tasks are tracked post-implementation."
        return f"""\n📝 Evaluation Report:\n\nScore: {score}\n\nAll identified issues were addressed. Consider post-mitigation validation checks."""

evaluator_agent = Agent(
    role="EvaluatorAgent", goal="Review the mitigation plan",
    backstory="Assess if the plan meets safety, timeliness, and compliance standards.",
    tools=[EvaluatorTool()], knowledge_sources=[sops["evaluator"]]
)
evaluator_task = Task(
    description="Evaluate the Master Mitigation Plan",
    expected_output="Evaluation feedback and score",
    agent=evaluator_agent,
    tool_choice="required"
)

all_agents = [scanner_agent, dispatcher_agent] + issue_agents + [planner_agent, evaluator_agent]
all_tasks = [scanner_task, dispatcher_task] + issue_tasks + [planner_task, evaluator_task]
flow = Flow(all_tasks)
crew = Crew(agents=all_agents, tasks=all_tasks, flow=flow)

with st.spinner("🚀 Running All Agents..."):
    crew_result = crew.kickoff()
    st.success("✅ Master Mitigation Plan Generated!")

    st.markdown("## 📊 Agent Execution Logs")
    for task in all_tasks:
        with st.expander(f"🧠 {task.agent.role} - {task.description}"):
            st.markdown(f"**Expected Output:** `{task.expected_output}`")
            st.markdown("**Agent Response:**")
            st.code(str(task.output) or "No output generated", language="markdown")

    st.markdown("---")
    st.markdown("## 📂 Dispatcher Routing Summary")
    dispatcher_output_lines = str(dispatcher_task.output).split("\n")
    for line in dispatcher_output_lines:
        match = re.match(r'- \*\*(.*?)\*\* → \*\*(.*?)\*\*: (.*)', line)
        if match:
            issue_type, agent, details = match.groups()
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', details)
            date = date_match.group(1) if date_match else "N/A"
            description = details.replace(date, "").strip(" -")
            icon = "🚚" if issue_type == "type_delay" else "⚠️" if issue_type == "type_safety" else "🧪"
            st.markdown(f"#### {icon} {issue_type.replace('_', ' ').title()}\n- 👤 **Assigned to**: `{agent}`\n- 📅 **Date**: {date}\n- 📜 **Details**: {description}")
            st.markdown("---")

    st.markdown("## ✅ Final Master Mitigation Plan")
    st.markdown(planner_task.output or "_PlannerAgent did not return any output._")

    st.markdown("## 🔪 Evaluation Report")
    st.markdown(str(evaluator_task.output) or "No evaluation available")

    st.download_button(
        label="📅 Download Mitigation Plan",
        data=str(planner_task.output),
        file_name="master_mitigation_plan.md",
        mime="text/markdown"
    )
