# VISTTA: Prompt-Conditioned Classroom Personas

VISTTA is a student research prototype for exploring how persona instructions shape answers to the same classroom question. Streamlit shows each generated answer beside the student's avatar. The persona configuration describes Alice as curious and engaged, Bob as shy and confused, and Charlie as overconfident. Their configured understanding levels are 60%, 30%, and 40%, respectively.

Paste a lecture into the text area, enter a question about that lecture, and select **Submit**. The app sends the same lecture and question to a local Ollama instance three times, once per persona. Each prompt adds the student's personality, knowledge level, emotional state, and understanding level. The prompts ask for a short answer based on the lecture and use those settings to encourage different responses from the same model.

## Run locally

Create a virtual environment and install the dependencies from the repository root.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Follow the [official Ollama installation instructions](https://ollama.com/download). If Ollama is not already running, start it in a separate terminal.

```sh
ollama serve
```

Then pull the model and start Streamlit.

```sh
ollama pull llama3
streamlit run app.py
```

The defaults are `http://localhost:11434` and `llama3`. Set `OLLAMA_URL` or `OLLAMA_MODEL` to use a different local address or installed model. The offline tests mock Ollama responses and require neither an Ollama installation nor a model pull. Live `llama3` inference remains untested.

## Scope

Answers can vary across runs and may ignore the persona or lecture instructions. The app has no retrieval-augmented generation (RAG), vector store, speech recognition, emotion analysis, or interaction between personas. The repository contains no formal evaluation of persona consistency or learning outcomes.
