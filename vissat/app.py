import streamlit as st
from llm import generate_response
from students import load_students

# Load students
students = load_students()

st.title("AI Classroom Simulation (English Learning)")

# Input: Lecture and Question
lecture = st.text_area("Enter Lecture Content (English):")
question = st.text_input("Ask a Question:")

# Prompt creation function
def create_prompt(student, lecture, question):

    return f"""
You are a school student.

Your personality: {student['personality']}
Your knowledge level: {student['knowledge']}
Your emotion: {student['emotion']}

Your understanding level of this lecture is: {student['understanding'] * 100}%

RULES:
- Answer ONLY using the lecture content
- Do NOT use outside knowledge
- If understanding is LOW (<40%), show confusion
- If understanding is MEDIUM (40–70%), give partial answer
- If understanding is HIGH (>70%), answer correctly
- Stay consistent with your personality

Lecture:
{lecture}

Question:
{question}

Respond in 1-2 lines like a student.
"""

# Button action
if st.button("Submit") and lecture and question:
    st.subheader("Student Responses")

    for student in students:
        prompt = create_prompt(student, lecture, question)
        response = generate_response(prompt)

        # Layout for avatar + response
        col1, col2 = st.columns([1, 4])

        with col1:
            st.image(student["avatar"], width=80)

        with col2:
            st.markdown(f"**{student['name']}**")
            st.write(response)