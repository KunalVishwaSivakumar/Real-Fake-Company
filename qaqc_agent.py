from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from dotenv import load_dotenv
import json
import os

load_dotenv()

# --- Load dispatcher output ---
dispatcher_path = "dispatcher_results.json"

if not os.path.exists(dispatcher_path):
    raise FileNotFoundError("dispatcher_results.json not found. Run dispatcher_agent.py first.")

with open(dispatcher_path, "r") as f:
    try:
        dispatcher_data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError("dispatcher_results.json is not valid JSON.")

# --- Filter QAQC-relevant issues ---
qaqc_issues = [
    route["Details"] for route in dispatcher_data.get("Routing List", [])
    if route.get("Assigned Agent") == "QAQCAgent"
]

# --- QAQC Analysis Logic ---
class QAQCLogic:
    def __init__(self, issues):
        self.issues = issues

    def analyze_and_recommend(self):
        if not self.issues:
            return {"inspections": [], "note": "✅ No failed inspections found."}

        results = []
        for issue in self.issues:
            results.append({
                "inspection_failure": issue,
                "recommended_rework": (
                    "Remove and reapply the affected material or component. "
                    "Ensure proper bonding and compliance with spec before requesting reinspection."
                )
            })
        return {"inspections": results}

# --- QAQC Tool ---
class QAQCTool(BaseTool):
    name: str = "InspectionFailureReviewer"
    description: str = "Analyzes failed inspection reports and recommends rework actions."

    def _run(self, **kwargs) -> str:
        logic = QAQCLogic(qaqc_issues)
        return json.dumps(logic.analyze_and_recommend())


# --- QAQC Agent ---
qaqc_agent = Agent(
    role="QA/QC Specialist",
    goal="Ensure inspection failures are addressed with proper rework.",
    backstory="You are in charge of quality control. You verify inspection failures are remediated promptly and effectively.",
    tools=[QAQCTool()],
    verbose=True
)

# --- QAQC Task ---
qaqc_task = Task(
    description="Use the provided tool to assess failed inspections and recommend corrective rework actions only.",
    expected_output="Structured output showing inspection issues and recommended rework.",
    agent=qaqc_agent,
    tool_choice="auto"
)

# --- Run Crew ---
crew = Crew(
    agents=[qaqc_agent],
    tasks=[qaqc_task],
    verbose=True
)

results = crew.kickoff()

# --- Save Result ---
try:
    parsed_output = results if isinstance(results, dict) else json.loads(str(results))
except json.JSONDecodeError:
    parsed_output = {"error": "Could not parse output", "raw": str(results)}

with open("qaqc_results.json", "w", encoding="utf-8") as f:
    json.dump(parsed_output, f, indent=2)

# --- Print Output ---
print("\n--- QAQC Output ---\n")
print(json.dumps(parsed_output, indent=2))
