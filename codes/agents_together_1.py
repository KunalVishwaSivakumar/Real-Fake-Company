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

crew = Crew(agents=[scanner_agent], tasks=[scanner_task], verbose=True)
scanner_output = crew.kickoff()

with open("scanner_results.txt", "w") as f:
    f.write(str(scanner_output))

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
        return json.dumps({"routing": DispatcherLogic(str(scanner_output)).route()}, indent=2)

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

crew = Crew(agents=[dispatcher_agent], tasks=[dispatcher_task], verbose=True)
dispatcher_output = crew.kickoff()

with open("dispatcher_results.json", "w") as f:
    f.write(str(dispatcher_output))

print("\n--- Scanner Output ---\n")
for line in str(scanner_output).split("\n"):
    print(line)

print("\n--- Dispatcher Output ---\n")
parsed_dispatch = json.loads(str(dispatcher_output))
for entry in parsed_dispatch.get("routing", []):
    print(f"- [{entry['issue_type']}] routed to {entry['agent']}: {entry['details']}")

# -----------------------------------------
# RUN NEXT AGENTS BASED ON DISPATCHER OUTPUT
# -----------------------------------------
dispatch_data = json.loads(str(dispatcher_output))
routes = dispatch_data.get("routing", [])

final_outputs = {}

for route in routes:
    issue_type = route["issue_type"]
    agent = route["agent"]
    detail = route["details"]

    class GenericIssueTool(BaseTool):
        name: str = Field(default=f"Handle{issue_type}")
        description: str = Field(default=f"Handles {issue_type} issues")

        def _run(self, **kwargs):
            if issue_type == "type_delay":
                return f"The HVAC shipment has been delayed by 3 weeks. To mitigate this delay, we need to implement a comprehensive plan that includes the following steps:\n1. **Communicate with the Vendor**: Contact the supplier to confirm the new delivery schedule and inquire about any possible solutions to expedite the shipment.\n2. **Adjust Project Timeline**: Revise the project schedule to accommodate the delay, ensuring that all team members are informed of the changes.\n3. **Identify Alternatives**: Explore alternative suppliers or products that could meet project specifications in a timely manner.\n4. **Prioritize Critical Tasks**: Focus on other critical path tasks that can progress during the delay to prevent a bottleneck in the project timeline.\n5. **Regular Updates**: Schedule regular updates with the team and stakeholders to keep everyone informed about the status of the shipment and any further adjustments to the timeline.\n6. **Document Changes**: Keep thorough documentation of the delay and the responses taken for accountability and future reference.\n\nBy following this plan, we aim to minimize the impact of the HVAC shipment delay on the overall project timeline."
            elif issue_type == "type_safety":
                return f"Mitigation plan for: {detail}\n1. Conduct a safety briefing to emphasize the importance of PPE compliance.\n2. Assign a safety officer to oversee PPE usage on Level 2.\n3. Implement regular PPE inspections and audits.\n4. Provide additional training sessions for all personnel on PPE requirements.\n5. Establish a reporting system for PPE violations.\n6. Encourage a culture of safety where employees can report concerns without fear of reprimand.\n7. Review and update PPE policies as necessary."
            elif issue_type == "type_inspection":
                return f"Mitigation plan for: {detail} includes reworking the affected area to ensure proper adhesion of the waterproofing membrane to the surface. Subsequent to the rework, a request for re-inspection should be made to confirm compliance with the specified standards."
            else:
                return f"Unhandled issue type: {issue_type}"

    issue_agent = Agent(
        role=agent,
        goal=f"Resolve {issue_type} issues effectively.",
        backstory=f"You handle all {issue_type} situations in the project.",
        tools=[GenericIssueTool()],
        verbose=True
    )

    issue_task = Task(
        description=f"Resolve the following issue: {detail}",
        expected_output=f"Mitigation plan for: {detail}",
        agent=issue_agent,
        tool_choice="required"
    )

    crew = Crew(agents=[issue_agent], tasks=[issue_task], verbose=True)
    output = crew.kickoff()
    final_outputs.setdefault(agent, []).append(str(output).strip())

# Save outputs in JSON
with open("agent_outputs.json", "w", encoding="utf-8") as f:
    json.dump(final_outputs, f, indent=2, ensure_ascii=False)

# Pretty CLI Output
print("\n--- Final Outputs from All Agents ---\n")
for agent, responses in final_outputs.items():
    print(f"\nAgent: {agent}")
    print("-" * 40)
    for r in responses:
        print(r.strip())
        print("-" * 40)
