import streamlit as st
import json
import os

st.set_page_config(page_title="Project Atlas Risk Dashboard", layout="wide")
st.title("🏗️ Project Atlas Risk Mitigation Dashboard")

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

# --- Tabs for each phase ---
tabs = st.tabs([
    "📡 Scanner",
    "📦 Dispatcher",
    "🗓 Scheduler",
    "🦺 Safety",
    "🧪 QA/QC",
    "📋 Planner",
    "📊 Evaluator"
])

# 1. Scanner Output
txt = load_file("scanner_results.txt")
with tabs[0]:
    st.header("Scanner Output")
    if txt:
        for line in txt.split("\n"):
            if line.strip():
                st.markdown(f"✅ `{line.strip()}`")
    else:
        st.info("No scanner results found.")

# 2. Dispatcher Output
json_data = load_file("dispatcher_results.json", is_json=True)
with tabs[1]:
    st.header("Dispatcher Output")
    if json_data and "Routing List" in json_data:
        for item in json_data["Routing List"]:
            st.success(f"🔀 `{item['Details']}` → **{item['Assigned Agent']}**")
    else:
        st.info("No dispatcher routing data found.")

# 3. Scheduler Output
scheduler_txt = load_file("scheduler_results.txt")
with tabs[2]:
    st.header("Scheduler Agent Output")
    if scheduler_txt:
        st.code(scheduler_txt.strip())
    else:
        st.info("No scheduling issues found.")

# 4. Safety Output
safety_json = load_file("safety_results.json", is_json=True)
with tabs[3]:
    st.header("Safety Agent Output")
    if safety_json and "violations" in safety_json:
        for v in safety_json["violations"]:
            st.warning(f"🦺 {v['violation']}\n\n🔧 {v['mitigation_strategy']}")
    else:
        st.info("No safety violations reported.")

# 5. QAQC Output
qaqc_json = load_file("qaqc_results.json", is_json=True)
with tabs[4]:
    st.header("QA/QC Agent Output")
    if qaqc_json and "inspections" in qaqc_json:
        for i in qaqc_json["inspections"]:
            st.error(f"🔍 {i['inspection_failure']}\n\n🔧 {i['recommended_rework']}")
    else:
        st.info("No QA/QC issues found.")

# 6. Planner Output
planner_json = load_file("planner_results.json", is_json=True)
with tabs[5]:
    st.header("Planner Summary")
    if planner_json and "actions" in planner_json:
        st.subheader(planner_json.get("summary", "Mitigation Plan"))
        for step in planner_json["actions"]:
            st.markdown(f"**🔧 {step['agent']}**: {step['action']}")
    else:
        st.info("No mitigation plan found.")

# 7. Evaluator Output
eval_json = load_file("evaluation_results.json", is_json=True)
with tabs[6]:
    st.header("Final Evaluation Report")
    if eval_json and "score" in eval_json:
        st.metric(label="🧠 Plan Quality Score", value=f"{eval_json['score']} / 10")
        st.success(f"✅ SOP Compliance: {eval_json['sop_compliance']}")
        st.markdown(f"**💬 Remarks:** {eval_json['remarks']}")
    else:
        st.info("Evaluation data not available.")