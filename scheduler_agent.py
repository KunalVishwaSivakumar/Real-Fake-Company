from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from dotenv import load_dotenv
import json
import os

load_dotenv()

# --- Load dispatcher output (validated) ---
dispatcher_path = "dispatcher_results.json"

if not os.path.exists(dispatcher_path):
    raise FileNotFoundError("dispatcher_results.json not found. Run dispatcher_agent.py first.")

with open(dispatcher_path, "r") as f:
    try:
        dispatcher_data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError("dispatcher_results.json is not valid JSON.")

# --- Filter scheduler-relevant issues ---
scheduler_issues = [
    route["details"] for route in dispatcher_data.get("routing", [])
    if route.get("agent") == "SchedulerAgent"
]

# --- Logic to generate schedule recommendations ---
class SchedulerLogic:
    def __init__(self, issues):
        self.issues = issues

    def analyze_and_suggest(self):
        if not self.issues:
            return "No delays found. Project schedule is on track."

        suggestions = []
        for issue in self.issues:
            suggestion = (
                f"Delay Identified:\n{issue}\n"
                f"Suggested Action: Coordinate with vendor and reschedule the impacted task. "
                f"Consider pushing it to a buffer date like May 30.\n"
            )
            suggestions.append(suggestion)
        return "\n".join(suggestions)

# --- Tool wrapper for CrewAI ---
class SchedulerTool(BaseTool):
    name: str = "ScheduleIssueResolution"
    description: str = "Analyzes project delays and suggests schedule changes to reduce risk."

    def _run(self, **kwargs) -> str:
        logic = SchedulerLogic(scheduler_issues)
        return logic.analyze_and_suggest()

# --- Scheduler Agent ---
scheduler_agent = Agent(
    role="Scheduler",
    goal="Reduce risk of project delay by resolving scheduling conflicts and delays.",
    backstory="You are the project schedule specialist. You evaluate delays and recommend fixes to keep things on track.",
    tools=[SchedulerTool()],
    verbose=True
)

# --- Task for Scheduler Agent ---
scheduler_task = Task(
    description="Use the provided tool to analyze known project delays and propose realistic, specific schedule mitigations. Do not invent new issues.",
    expected_output="One action item per delay issue pulled from dispatcher_results.json.",
    agent=scheduler_agent,
    tool_choice="auto"
)

# --- Execute Crew ---
crew = Crew(
    agents=[scheduler_agent],
    tasks=[scheduler_task],
    verbose=True
)

results = crew.kickoff()

# --- Save result ---
with open("scheduler_results.txt", "w") as f:
    f.write(str(results))

# --- Print formatted output ---
print("\n--- Scheduler Output ---\n")
for line in str(results).split("\n"):
    print(line)
