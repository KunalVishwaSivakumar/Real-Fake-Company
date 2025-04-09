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

# --- Filter safety-related issues ---
safety_issues = [
    route["Details"] for route in dispatcher_data.get("Routing List", [])
    if route.get("Assigned Agent") == "SafetyAgent"
]

# --- Safety Analysis Logic ---
class SafetyLogic:
    def __init__(self, issues):
        self.issues = issues

    def analyze_and_recommend(self):
        if not self.issues:
            return "✅ No safety issues detected. Site is currently compliant."

        recommendations = []
        for issue in self.issues:
            recommendations.append(
                f"⚠️ Safety Violation:\n{issue}\n"
                f"🔧 Mitigation Strategy: Conduct a mandatory PPE refresher session. "
                f"Assign a dedicated floor-level safety supervisor to ensure compliance.\n"
            )
        return "\n".join(recommendations)

# --- CrewAI Tool ---
class SafetyTool(BaseTool):
    name: str = "SafetyViolationResponder"
    description: str = "Analyzes safety violations and recommends corrective actions."

    def _run(self, **kwargs) -> str:
        logic = SafetyLogic(safety_issues)
        return logic.analyze_and_recommend()

# --- Agent Setup ---
safety_agent = Agent(
    role="Safety Officer",
    goal="Mitigate site safety risks by analyzing reported violations.",
    backstory="You ensure the construction site is compliant with all safety regulations and proactively handle any violations.",
    tools=[SafetyTool()],
    verbose=True
)

# --- Task Definition ---
safety_task = Task(
    description="Use the provided tool ONLY. Do not add new issues or make assumptions. Respond only to violations listed in dispatcher_results.json.",
    expected_output="Mitigation plan for each violation found in dispatcher_results.json.",
    agent=safety_agent,
    tool_choice="auto"
)

# --- Run Crew ---
crew = Crew(
    agents=[safety_agent],
    tasks=[safety_task],
    verbose=True
)

results = crew.kickoff()

# --- Save Result ---
# Try to convert CrewOutput → JSON-safe dict
try:
    parsed_result = json.loads(str(results))
except json.JSONDecodeError:
    parsed_result = {
        "violations": [
            {
                "raw_output": str(results),
                "note": "Could not parse as structured JSON. This is fallback raw text."
            }
        ]
    }

with open("safety_results.json", "w", encoding="utf-8") as f:
    json.dump(parsed_result, f, indent=2)


# --- Print Output ---
print("\n--- Safety Output ---\n")
for line in str(results).split("\n"):
    print(line)
