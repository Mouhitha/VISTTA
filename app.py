from pathlib import Path

import streamlit as st

from llm import OllamaError, generate_response
from prompting import create_prompt
from students import load_students

APP_DIR = Path(__file__).resolve().parent
students = load_students()

st.title("AI Classroom Simulation (English Learning)")

lecture = st.text_area("Enter Lecture Content (English):").strip()
question = st.text_input("Ask a Question:").strip()

if st.button("Submit"):
    if not lecture or not question:
        st.warning("Enter both lecture content and a question.")
    else:
        st.subheader("Student Responses")

        for student in students:
            prompt = create_prompt(student, lecture, question)
            try:
                response = generate_response(prompt)
            except OllamaError as error:
                st.error(str(error))
                break

            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(str(APP_DIR / student["avatar"]), width=80)
            with col2:
                st.markdown(f"**{student['name']}**")
                st.write(response)
