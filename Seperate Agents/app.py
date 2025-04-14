# --- Prompt Input ---
import streamlit as st
import json
import os
# --- Helper function to load file content ---
def load_file(path, is_json=False):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        if is_json:
            try:
                return json.load(f)
            except:
                return {"error": "Invalid JSON"}
        else:
            return f.read()
        
st.subheader("🤖 Ask Atlas")
user_prompt = st.text_input("What would you like to know?", placeholder="e.g., Any QA issues? What’s the schedule?")

if user_prompt:
    st.markdown("### 🧠 Project Atlas Says:")

    prompt = user_prompt.lower()

    # Trigger responses based on keyword detection
    if "schedule" in prompt or "scheduler" in prompt:
        scheduler_txt = load_file("scheduler_results.txt")
        if scheduler_txt:
            st.markdown("#### 📅 Scheduler Agent")
            st.code(scheduler_txt.strip())
        else:
            st.info("Scheduler has no updates.")

    if "safety" in prompt or "violation" in prompt:
        safety_json = load_file("safety_results.json", is_json=True)
        if safety_json and "violations" in safety_json:
            st.markdown("#### 🦺 Safety Agent")
            for v in safety_json["violations"]:
                st.warning(f"{v['violation']}\n\n🔧 {v['mitigation_strategy']}")
        else:
            st.info("No safety concerns reported.")

    if "qa" in prompt or "qc" in prompt or "inspection" in prompt:
        qaqc_json = load_file("qaqc_results.json", is_json=True)
        if qaqc_json and "inspections" in qaqc_json:
            st.markdown("#### 🧪 QA/QC Agent")
            for i in qaqc_json["inspections"]:
                st.error(f"{i['inspection_failure']}\n\n🔧 {i['recommended_rework']}")
        else:
            st.info("No QA/QC failures found.")

    if "dispatch" in prompt or "dispatcher" in prompt:
        json_data = load_file("dispatcher_results.json", is_json=True)
        if json_data and "Routing List" in json_data:
            st.markdown("#### 📦 Dispatcher Agent")
            for item in json_data["Routing List"]:
                st.success(f"🔀 {item['Details']} → *{item['Assigned Agent']}*")
        else:
            st.info("Dispatcher has no routes assigned.")

    if "scan" in prompt or "scanner" in prompt:
        txt = load_file("scanner_results.txt")
        if txt:
            st.markdown("#### 📡 Scanner Agent")
            for line in txt.split("\n"):
                if line.strip():
                    st.markdown(f"✅ {line.strip()}")
        else:
            st.info("No scanner results available.")

    if "plan" in prompt or "planner" in prompt:
        planner_json = load_file("planner_results.json", is_json=True)
        if planner_json and "actions" in planner_json:
            st.markdown("#### 📋 Planner Agent")
            st.subheader(planner_json.get("summary", "Mitigation Plan"))
            for step in planner_json["actions"]:
                st.markdown(f"🔧 {step['agent']}: {step['action']}")
        else:
            st.info("Planner has no mitigation actions.")

    if "evaluation" in prompt or "score" in prompt or "final" in prompt:
        eval_json = load_file("evaluation_results.json", is_json=True)
        if eval_json and "score" in eval_json:
            st.markdown("#### 📊 Evaluator Agent")
            st.metric(label="🧠 Plan Quality Score", value=f"{eval_json['score']} / 10")
            st.success(f"✅ SOP Compliance: {eval_json['sop_compliance']}")
            st.markdown(f"💬 Remarks:** {eval_json['remarks']}")
        else:
            st.info("No evaluation report yet.")

    if all(kw not in prompt for kw in ["scanner", "dispatcher", "scheduler", "safety", "qa", "qc", "planner", "evaluation", "score", "plan", "schedule"]):
        st.info("Couldn't understand your request. Try asking about schedule, safety, QA/QC, etc.")
