import json
from datetime import datetime

MEMORY_FILE = "memory.json"


def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except:
        return {"sessions": []}


def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)


def log_interaction(topic, lecture, question, responses):
    memory = load_memory()

    session_entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "topic": topic,
        "teacher_notes": lecture,
        "question": question,
        "student_responses": responses
    }

    memory["sessions"].append(session_entry)

    save_memory(memory)