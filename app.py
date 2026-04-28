import streamlit as st

from engine.personaloader import load_persona
from engine.prompt_builder import build_prompt
from llm.ollama import ask_llm

st.set_page_config(page_title="VISTTA Classroom", layout="wide")

st.title("🏫 VISTTA - Virtual Intelligent Classroom")

# -----------------------------
# LOAD PERSONAS
# -----------------------------
personas = {
    "Topper": load_persona("personas/student1.json"),
    "Average": load_persona("personas/student2.json"),
    "Weak": load_persona("personas/student3.json")
}

avatar_map = {
    "Topper": "assets/student1.png",
    "Average": "assets/student2.png",
    "Weak": "assets/student3.png"
}

# -----------------------------
# TEACHER SECTION (DIAS)
# -----------------------------
st.markdown("## 👩‍🏫 Teacher")

col_t1, col_t2, col_t3 = st.columns([1,2,1])

with col_t2:
    st.image("assets/teacher.png", width=200)
    st.caption("Teacher on Dias")

st.divider()

# -----------------------------
# INPUT SECTION
# -----------------------------
lecture = st.text_area("📘 Enter Lecture Notes")
question = st.text_input("❓ Ask Question to Students")

# -----------------------------
# CLASSROOM SIMULATION
# -----------------------------
if st.button("🎓 Start Class Simulation"):

    st.markdown("## 🧑‍🎓 Students in Classroom")

    cols = st.columns(3)

    results = {}

    for i, (label, persona) in enumerate(personas.items()):

        prompt = build_prompt(persona, lecture, question)
        response = ask_llm(prompt)

        results[label] = response

        with cols[i]:

            st.image(avatar_map[label], width=150)
            st.subheader(f"{persona['name']} ({label})")

            st.markdown("### 💬 Response")
            st.write(response)

            # Optional visual indicator of behavior
            confidence = persona["personality"]["confidence"]

            if confidence > 0.7:
                st.success(" 🟢")
            elif confidence > 0.4:
                st.warning(" 🟡")
            else:
                st.error(" 🔴")

st.divider()

st.caption("VISTTA Classroom Simulation - LLM Powered Student Personas")