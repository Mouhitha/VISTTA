# Architecture

1. Streamlit accepts an English lecture and a question. On submission, it strips surrounding whitespace and warns if either field is empty.
2. The app loads three personas from `students.json`. For each persona it builds a prompt with the same lecture and question plus that student's personality, knowledge, configured emotion, and understanding level.
3. The app sends the prompts sequentially as separate `POST /api/generate` requests to Ollama. Each request asks the configured model for one complete response. The default is local `llama3`.
4. Streamlit renders each response beside the corresponding name and avatar. If an Ollama call fails, Streamlit displays an error and stops the remaining calls.

The personas are simulated independently. They do not see each other's answers or exchange messages. The JSON `attention` and `memory` keys are configuration placeholders and are currently unused. Emotional states come from the configuration. The source contains no RAG or vector store, speech API, emotion analysis pipeline, or validated learning outcomes.
