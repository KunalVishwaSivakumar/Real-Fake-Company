from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from dotenv import load_dotenv
import json
import os

load_dotenv()

# --- Helper to safely load JSON ---
def load_json(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return None
def load_text(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


# --- Load inputs from agents ---
scheduler_data = load_text("scheduler_results.txt")
safety_data = load_json("safety_results.json")
qaqc_data = load_json("qaqc_results.json")

# --- Planner Logic ---
class PlannerLogic:
    def __init__(self, scheduler, safety, qaqc):
        self.scheduler = scheduler
        self.safety = safety
        self.qaqc = qaqc

    def create_plan(self):
        plan = []

        # Scheduling
        if self.scheduler and isinstance(self.scheduler, str) and self.scheduler.strip():
            plan.append({
                "agent": "SchedulerAgent",
                "action": self.scheduler.strip()
            })

        # Safety
        if self.safety and "violations" in self.safety:
            for v in self.safety["violations"]:
                plan.append({
                    "agent": "SafetyAgent",
                    "action": f"{v['violation']} — {v['mitigation_strategy']}"
                })

        # QA/QC
        if self.qaqc and "inspections" in self.qaqc:
            for i in self.qaqc["inspections"]:
                plan.append({
                    "agent": "QAQCAgent",
                    "action": f"{i['inspection_failure']} — {i['recommended_rework']}"
                })

        if not plan:
            return {"summary": "No outstanding issues. Project mitigation plan is clear.", "actions": []}
        return {"summary": "Project Mitigation Plan", "actions": plan}

# --- CrewAI Tool ---
class PlannerTool(BaseTool):
    name: str = "AggregateMitigationPlan"
    description: str = "Reads outputs from all agents and generates a single, unified mitigation plan."

    def _run(self, **kwargs) -> str:
        logic = PlannerLogic(scheduler_data, safety_data, qaqc_data)
        return json.dumps(logic.create_plan(), indent=2)

# --- Agent ---
planner_agent = Agent(
    role="Planner",
    goal="Consolidate mitigation actions from all project agents.",
    backstory="You are the master coordinator. You gather insights from schedule, safety, and quality agents and assemble a unified action plan.",
    tools=[PlannerTool()],
    verbose=True
)

# --- Task ---
planner_task = Task(
    description="Use the provided tool to aggregate mitigation strategies from SchedulerAgent, SafetyAgent, and QAQCAgent. Build a unified project response plan.",
    expected_output="JSON object with a summary and action items from each agent.",
    agent=planner_agent,
    tool_choice="required"
)

# --- Run the Crew ---
crew = Crew(
    agents=[planner_agent],
    tasks=[planner_task],
    verbose=True
)

results = crew.kickoff()

# --- Save & Print ---
try:
    parsed = json.loads(str(results))
except json.JSONDecodeError:
    parsed = {"error": "Unable to parse planner output", "raw": str(results)}

with open("planner_results.json", "w", encoding="utf-8") as f:
    json.dump(parsed, f, indent=2)

print("\n--- Planner Output ---\n")
print(json.dumps(parsed, indent=2, ensure_ascii=False))

