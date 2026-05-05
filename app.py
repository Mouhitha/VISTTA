import streamlit as st
from personas import AARAV, MEERA
from prompt_builder import build_prompt
from llm import ask_llama
from memory import log_interaction

st.title("Virtual Classroom Simulator")

lecture = st.text_area("Enter Lecture Notes")
question = st.text_input("Ask a Question to the Class")

# optional topic input (important for memory organization)
topic = st.text_input("Topic (e.g., Verb, Noun, Tenses)", value="General")

if st.button("Ask Students") and lecture and question:
    st.subheader("Student Responses")

    responses = {}  # 🔥 collect all responses for memory

    for persona in [AARAV, MEERA]:
        prompt = build_prompt(persona, lecture, question)
        response = ask_llama(prompt)

        responses[persona["name"]] = response

        st.markdown(f"### {persona['name']} ({persona['role']})")
        st.write(response)

    # 🔥 SAVE FULL CLASSROOM INTERACTION TO MEMORY
    log_interaction(
        topic=topic,
        lecture=lecture,
        question=question,
        responses=responses
    )

    st.success("Class session saved to memory.json ✔")