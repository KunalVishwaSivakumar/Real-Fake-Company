from crewai import Agent, Task, Crew
import json

# --- Scanner Logic ---
def run_scan(project_data):
    issues = []

    # Scan emails
    for email in project_data.get("emails", []):
        if "delay" in email["body"].lower():
            issues.append(f"[type_delay] {email['date']} - {email['subject']}: {email['body']}")

    # Scan site logs
    for log in project_data.get("site_logs", []):
        if "violation" in log["description"].lower():
            issues.append(f"[type_safety] {log['log_date']} - {log['description']}")

    # Scan inspection reports
    for report in project_data.get("inspection_reports", []):
        if "fail" in report["status"].lower():
            issues.append(f"[type_inspection] {report['date']} - {report['area']}: {report['comments']}")

    return "\n".join(issues)

# --- Load data ---
with open("project_atlas.json", "r") as f:
    project_data = json.load(f)

# --- Agent (no tools needed) ---
scanner_agent = Agent(
    role="Scanner",
    goal="Detect delays, safety issues, and inspection failures from project documents.",
    backstory="You carefully examine project records to spot problems before they escalate.",
    verbose=True
)

# --- Task ---
scanner_task = Task(
    description="Analyze all project data and list any delays, safety issues, or inspection failures using [type_xxx] tags.",
    expected_output="A detailed list of issues using [type_delay], [type_safety], and [type_inspection].",
    agent=scanner_agent,
)

# --- Run Crew ---
crew = Crew(
    agents=[scanner_agent],
    tasks=[scanner_task],
    verbose=True
)

# Simulate task result by manually calling the logic
print("\n--- Scanner Output ---\n")
print(run_scan(project_data))
