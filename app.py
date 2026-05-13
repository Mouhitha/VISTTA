import random
import re
import time
from typing import Any, List

import streamlit as st

from students import (
    load_students,
    build_turn_context,
    apply_teacher_effect,
    apply_post_response_effect,
    choose_responders,
    set_neutral_state,
)
from llm import (
    build_student_prompt,
    build_recent_context,
    generate_response,
    classify_teacher_input,
    short_reaction,
    non_english_reaction,
)

st.set_page_config(page_title="AI Classroom Simulation", layout="wide")


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def flatten_knowledge_base(obj: Any) -> List[str]:
    concepts = []

    def collect(item):
        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(key, str):
                    concepts.append(key)
                collect(value)
        elif isinstance(item, list):
            for value in item:
                collect(value)
        elif isinstance(item, str):
            concepts.append(item)

    collect(obj)

    cleaned = []
    seen = set()

    for concept in concepts:
        concept = concept.strip()
        if concept and concept not in seen:
            cleaned.append(concept)
            seen.add(concept)

    return cleaned


def get_unknown_areas(student) -> List[str]:
    all_concepts = flatten_knowledge_base(student.knowledge.knowledge_base)

    return [
        concept
        for concept in all_concepts
        if concept not in student.knowledge.correct_concepts
    ]


def state_color(value):
    if value >= 0.7:
        return "#22c55e"
    elif value >= 0.4:
        return "#f59e0b"
    return "#ef4444"


def delta_color(delta):
    if delta > 0:
        return "#16a34a"
    elif delta < 0:
        return "#dc2626"
    return "#6b7280"


def format_delta(value):
    if value > 0:
        return f"+{value:.2f}"
    return f"{value:.2f}"


def render_metric(label, value):
    value = clamp(value)
    color = state_color(value)

    st.markdown(
        f"""
        <div style="margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:4px;">
                <span style="color:#374151;">{label}</span>
                <span style="color:#111827; font-weight:600;">{value:.2f}</span>
            </div>
            <div style="background:#e5e7eb; border-radius:999px; height:8px;">
                <div style="width:{int(value*100)}%; background:{color}; height:8px; border-radius:999px;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def snapshot_state(student):
    return {
        "boredom": student.state.boredom,
        "engagement": student.state.engagement,
        "confusion": student.state.confusion,
        "frustration": student.state.frustration,
        "delight": student.state.delight,
        "surprise": student.state.surprise,
    }


def compute_deltas(before, after):
    return {
        "boredom": after["boredom"] - before["boredom"],
        "engagement": after["engagement"] - before["engagement"],
        "confusion": after["confusion"] - before["confusion"],
        "frustration": after["frustration"] - before["frustration"],
        "delight": after["delight"] - before["delight"],
        "surprise": after["surprise"] - before["surprise"],
    }


def neutralize_all_students(students):
    for student in students:
        set_neutral_state(student)


def shorten(text: str, max_len: int = 70) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def find_last_responder_name(history: list) -> str:
    for item in reversed(history):
        responses = item.get("responses", [])
        if responses:
            return responses[-1]["student_name"]
    return "none"


def extract_task_from_text(text: str) -> dict:
    lowered = text.lower()

    word_patterns = [
        r'word\s+"([^"]+)"',
        r"word\s+'([^']+)'",
        r"word\s+([a-zA-Z]+)",
        r"using\s+the\s+word\s+([a-zA-Z]+)",
        r"with\s+the\s+word\s+([a-zA-Z]+)",
    ]

    word = None
    for pattern in word_patterns:
        match = re.search(pattern, lowered)
        if match:
            word = match.group(1).strip(" .,!?:;\"'")
            break

    is_sentence_task = any(
        phrase in lowered
        for phrase in [
            "make a sentence",
            "form a sentence",
            "write a sentence",
            "use it in a sentence",
            "sentence using",
            "sentence with",
        ]
    )

    if is_sentence_task:
        return {
            "type": "sentence",
            "word": word,
            "description": f"Make a sentence using the word {word}" if word else "Make a sentence",
        }

    if "past tense" in lowered:
        return {
            "type": "past_tense",
            "word": word,
            "description": "Use or explain past tense",
        }

    if "pronoun" in lowered:
        return {
            "type": "pronoun",
            "word": word,
            "description": "Work with pronouns",
        }

    return {
        "type": "unknown",
        "word": word,
        "description": "",
    }


def get_active_task_text() -> str:
    task = st.session_state.get("active_task", {})
    if not task or not task.get("description"):
        return ""

    return (
        f"Active task: {task.get('description')}\n"
        f"Task type: {task.get('type')}\n"
        f"Target word: {task.get('word')}\n"
        f"Attempt count: {task.get('attempt_count')}\n"
        f"Last target: {task.get('last_target')}"
    )


def update_active_task_memory(classification: dict, teacher_input: str, responders: list):
    move_type = classification.get("move_type", "information")
    directed_to = classification.get("directed_to", "none")

    if "active_task" not in st.session_state:
        st.session_state.active_task = {
            "description": "",
            "type": "none",
            "word": None,
            "attempt_count": 0,
            "last_target": "none",
        }

    task_info = extract_task_from_text(teacher_input)

    if move_type == "question" and task_info["description"]:
        st.session_state.active_task = {
            "description": task_info["description"],
            "type": task_info["type"],
            "word": task_info["word"],
            "attempt_count": 1,
            "last_target": directed_to,
        }

    elif move_type == "question" and not task_info["description"]:
        if st.session_state.active_task.get("description"):
            st.session_state.active_task["attempt_count"] += 1
            if directed_to != "none":
                st.session_state.active_task["last_target"] = directed_to

    if responders:
        st.session_state.active_task["last_target"] = responders[0][0].name


def refine_classification(raw_cls: dict, teacher_input: str, student_names: list[str], history: list) -> dict:
    text = teacher_input.strip().lower()

    valid_moves = {
        "question",
        "greeting",
        "praise",
        "correction",
        "information",
        "acknowledgement",
    }

    valid_secondary_moves = {
        "none",
        "praise",
        "correction",
        "information",
        "question",
        "acknowledgement",
    }

    valid_topics = {
        "vocabulary",
        "grammar",
        "sentence_structure",
        "past_tense",
        "pronouns",
        "classroom_management",
        "unknown",
    }

    valid_difficulties = {
        "easy",
        "medium",
        "hard",
    }

    cls = {
        "move_type": raw_cls.get("move_type", "information"),
        "secondary_move": raw_cls.get("secondary_move", "none"),
        "tone": raw_cls.get("tone", "neutral"),
        "directed_to": raw_cls.get("directed_to", "none"),
        "expects_response": bool(raw_cls.get("expects_response", False)),
        "topic": raw_cls.get("topic", "unknown"),
        "difficulty": raw_cls.get("difficulty", "medium"),
        "non_english_input": bool(raw_cls.get("non_english_input", False)),
        "reason": raw_cls.get("reason", ""),
    }

    if cls["move_type"] not in valid_moves:
        cls["move_type"] = "information"

    if cls["secondary_move"] not in valid_secondary_moves:
        cls["secondary_move"] = "none"

    if cls["tone"] not in ["positive", "neutral", "negative"]:
        cls["tone"] = "neutral"

    if cls["topic"] not in valid_topics:
        cls["topic"] = "unknown"

    if cls["difficulty"] not in valid_difficulties:
        cls["difficulty"] = "medium"

    valid_targets = student_names + ["class", "none"]
    if cls["directed_to"] not in valid_targets:
        cls["directed_to"] = "none"

    english_markers = [
        "hello", "hi", "good morning", "good afternoon",
        "what", "why", "how", "when", "where", "who",
        "can you", "could you", "please", "try", "make",
        "sentence", "word", "good job", "well done",
        "correct", "wrong", "verb", "noun", "adjective",
        "teacher", "student", "class", "answer", "question",
        "past tense", "pronoun", "grammar", "english",
    ]

    if any(marker in text for marker in english_markers):
        cls["non_english_input"] = False

    group_target_markers = [
        "both of you",
        "you both",
        "all of you",
        "everyone",
        "the class",
        "class",
        "you guys",
    ]

    if any(marker in text for marker in group_target_markers):
        cls["directed_to"] = "class"

    if cls["directed_to"] == "none":
        for name in student_names:
            if re.search(rf"\b{re.escape(name.lower())}\b", text):
                cls["directed_to"] = name
                break

    if cls["move_type"] in ["praise", "correction", "acknowledgement"]:
        if cls["directed_to"] == "none":
            last_responder = find_last_responder_name(history)
            if last_responder != "none":
                cls["directed_to"] = last_responder

    continuation_markers = [
        "go on",
        "continue",
        "try your best",
        "try again",
        "now you try",
        "same question",
        "your turn",
    ]

    if cls["move_type"] == "greeting" and any(marker in text for marker in continuation_markers):
        cls["move_type"] = "question"
        cls["expects_response"] = True

        if cls["directed_to"] == "none":
            last_responder = find_last_responder_name(history)
            if last_responder != "none":
                cls["directed_to"] = last_responder

    if cls["move_type"] in ["information", "acknowledgement"]:
        if "?" in text:
            cls["move_type"] = "question"
            cls["expects_response"] = True

    return cls


if "students" not in st.session_state:
    st.session_state.students = load_students()

if "history" not in st.session_state:
    st.session_state.history = []

if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

if "active_task" not in st.session_state:
    st.session_state.active_task = {
        "description": "",
        "type": "none",
        "word": None,
        "attempt_count": 0,
        "last_target": "none",
    }

LESSON_CONTEXT = "Basic English classroom for Swedish children aged 10-12."

st.sidebar.header("Simulation Settings")

experiment_mode = st.sidebar.checkbox(
    "Experiment Mode",
    value=False,
    help="Fixes all affective state variables at 0.50 and removes fatigue/random silence.",
)

llm_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["ollama", "gemini"],
    index=0,
    help="Choose local Ollama or Gemini API.",
)

if llm_provider == "ollama":
    selected_model = st.sidebar.text_input(
        "Ollama model",
        value="llama3",
    )
else:
    selected_model = st.sidebar.selectbox(
        "Gemini model",
        options=["gemini-2.5-flash", "gemini-2.5-flash-lite"],
        index=1,
    )

if st.sidebar.button("Reset Classroom"):
    st.session_state.students = load_students()
    st.session_state.history = []
    st.session_state.turn_index = 0
    st.session_state.active_task = {
        "description": "",
        "type": "none",
        "word": None,
        "attempt_count": 0,
        "last_target": "none",
    }
    st.rerun()

st.title("AI Classroom Simulation")
st.caption("Basic English classroom for ages 10–12.")

if experiment_mode:
    neutralize_all_students(st.session_state.students)
    st.info("Experiment Mode is ON: all affective states are fixed at 0.50, with fatigue/random silence disabled.")

if llm_provider == "gemini":
    st.success(f"Using Gemini API model: {selected_model}")
else:
    st.info(f"Using local Ollama model: {selected_model}")

left, right = st.columns([1, 1.5])

with left:
    st.subheader("Teacher Input")

    with st.form("teacher_form", clear_on_submit=True):
        teacher_input = st.text_area(
            "What does the teacher say?",
            placeholder='Example: Leo, please make a sentence with the word car.\nOr: Now you try, Leo.\nOr: Same question, Emma.',
            height=140,
        )
        submitted = st.form_submit_button("Send to classroom")

    active_task_text = get_active_task_text()
    if active_task_text:
        with st.expander("Current active task memory", expanded=False):
            st.text(active_task_text)

    st.caption("Best results: use one teacher action per turn. Mixed turns are treated as one primary classroom move.")

    st.subheader("Students")

    students = st.session_state.students
    if experiment_mode:
        neutralize_all_students(students)

    cols = st.columns(len(students)) if len(students) <= 3 else st.columns(3)

    for i, student in enumerate(students):
        with cols[i % len(cols)]:
            st.markdown(
                f"""
                <div style="
                    background:white;
                    border-radius:12px;
                    padding:12px;
                    border:1px solid #e5e7eb;
                    margin-bottom:10px;">
                    <strong>{student.name}</strong><br>
                    <span style="color:#6b7280; font-size:0.8rem;">dynamic affective state</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            render_metric("Boredom", student.state.boredom)
            render_metric("Engagement", student.state.engagement)
            render_metric("Confusion", student.state.confusion)
            render_metric("Frustration", student.state.frustration)
            render_metric("Delight", student.state.delight)
            render_metric("Surprise", student.state.surprise)

            with st.expander(f"Show {student.name}'s profile"):
                st.markdown("**Knowledge**")

                correct_concepts = (
                    ", ".join(student.knowledge.correct_concepts)
                    if student.knowledge.correct_concepts
                    else "None"
                )

                misconceptions = (
                    ", ".join(student.knowledge.misconceptions)
                    if student.knowledge.misconceptions
                    else "None"
                )

                unknown_areas_list = get_unknown_areas(student)
                unknown_areas = (
                    ", ".join(unknown_areas_list)
                    if unknown_areas_list
                    else "None"
                )

                st.write(f"Correct concepts: {correct_concepts}")
                st.write(f"Misconceptions: {misconceptions}")
                st.write(f"Unknown areas: {unknown_areas}")

                st.markdown("**Personality**")
                st.write(f"Participation tendency: {student.personality.participation}")
                st.write(f"Emotional stability: {student.personality.emotional_stability}")
                st.write(f"Task orientation: {student.personality.task_orientation}")
                st.write(f"Receptiveness to guidance: {student.personality.receptiveness}")

                st.markdown("**Short-term memory**")
                st.write(f"Turns since spoke: {student.memory.turns_since_spoke}")
                st.write(f"Silence streak: {student.memory.silence_streak}")
                st.write(f"Answer streak: {student.memory.answer_streak}")
                st.write(f"Recent praise: {student.memory.recent_praise}")
                st.write(f"Recent correction: {student.memory.recent_correction}")
                st.write(f"Last outcome: {student.memory.last_outcome}")

with right:
    st.subheader("Classroom Conversation")

    if submitted and teacher_input.strip():
        try:
            with st.spinner("Students are thinking..."):
                timings = {}
                total_start = time.perf_counter()

                students = st.session_state.students
                if experiment_mode:
                    neutralize_all_students(students)

                st.session_state.turn_index += 1
                student_names = [s.name for s in students]

                t = time.perf_counter()
                active_task_text = get_active_task_text()
                recent_context = build_recent_context(
                    st.session_state.history,
                    max_turns=4,
                    active_task_text=active_task_text,
                )
                timings["recent_context"] = time.perf_counter() - t

                t = time.perf_counter()
                raw_classification = classify_teacher_input(
                    teacher_input,
                    student_names=student_names,
                    model=selected_model,
                    recent_context=recent_context,
                    provider=llm_provider,
                )
                timings["llm_classification"] = time.perf_counter() - t

                t = time.perf_counter()
                classification = refine_classification(
                    raw_classification,
                    teacher_input,
                    student_names,
                    st.session_state.history,
                )
                timings["classification_refinement"] = time.perf_counter() - t

                pre_turn_states = {
                    student.name: snapshot_state(student)
                    for student in students
                }

                t = time.perf_counter()
                for student in students:
                    apply_teacher_effect(
                        student,
                        classification,
                        experiment_mode=experiment_mode,
                        active_task=st.session_state.active_task,
                    )
                timings["teacher_effects"] = time.perf_counter() - t

                if classification.get("non_english_input", False):
                    for student in students:
                        student.state.confusion = min(1.0, student.state.confusion + 0.03)
                        student.state.engagement = max(0.0, student.state.engagement - 0.01)
                        student.state.surprise = min(1.0, student.state.surprise + 0.02)

                if experiment_mode:
                    neutralize_all_students(students)

                t = time.perf_counter()
                turn_contexts = {
                    student.name: build_turn_context(
                        student,
                        teacher_input,
                        classification,
                        experiment_mode=experiment_mode,
                        active_task=st.session_state.active_task,
                    )
                    for student in students
                }
                timings["turn_contexts"] = time.perf_counter() - t

                t = time.perf_counter()
                responders, all_scores = choose_responders(
                    students,
                    classification,
                    turn_contexts,
                    similarity_threshold=0.08,
                    rng=random,
                    experiment_mode=experiment_mode,
                )
                timings["responder_selection"] = time.perf_counter() - t

                if classification.get("non_english_input", False):
                    move_type = classification["move_type"]
                    if move_type == "question":
                        if all_scores and all_scores[0][1] > 0.45 and random.random() < 0.35:
                            responders = [all_scores[0]]
                        else:
                            responders = []
                    elif move_type == "greeting":
                        responders = [all_scores[0]] if all_scores else []
                    elif move_type in ["praise", "correction"]:
                        responders = [all_scores[0]] if all_scores else []
                    else:
                        responders = []

                t = time.perf_counter()
                update_active_task_memory(classification, teacher_input, responders)
                timings["active_task_update"] = time.perf_counter() - t

                round_data = {
                    "turn_index": st.session_state.turn_index,
                    "teacher": teacher_input,
                    "raw_classification": raw_classification,
                    "classification": classification,
                    "responses": [],
                    "all_scores": [],
                    "no_response": False,
                    "experiment_mode": experiment_mode,
                    "student_updates": [],
                    "recent_context": recent_context,
                    "active_task": dict(st.session_state.active_task),
                    "timings": timings,
                    "llm_provider": llm_provider,
                    "selected_model": selected_model,
                }

                for student, score in all_scores:
                    round_data["all_scores"].append({
                        "student_name": student.name,
                        "score": score,
                    })

                selected_names = {student.name for student, _ in responders}
                responder_text = {}

                if not responders:
                    round_data["no_response"] = True
                    for student in students:
                        apply_post_response_effect(
                            student,
                            turn_contexts[student.name],
                            was_selected=False,
                            outcome="silent",
                            experiment_mode=experiment_mode,
                            active_task=st.session_state.active_task,
                        )
                else:
                    for student, score in responders:
                        result = turn_contexts[student.name]

                        if classification.get("non_english_input", False):
                            t = time.perf_counter()
                            response = non_english_reaction()
                            timings[f"short_non_english_reaction_{student.name}"] = time.perf_counter() - t

                        elif classification["move_type"] in ["greeting", "praise", "correction"]:
                            t = time.perf_counter()
                            response = short_reaction(classification["move_type"])
                            timings[f"short_reaction_{student.name}"] = time.perf_counter() - t

                        else:
                            active_task_text = get_active_task_text()
                            recent_context_for_prompt = recent_context
                            if active_task_text:
                                recent_context_for_prompt += "\n\n" + active_task_text

                            t = time.perf_counter()
                            prompt = build_student_prompt(
                                student,
                                teacher_input,
                                result,
                                recent_context=recent_context_for_prompt,
                            )
                            prompt += f"\n\nLesson context:\n{LESSON_CONTEXT}"
                            timings[f"prompt_building_{student.name}"] = time.perf_counter() - t

                            t = time.perf_counter()
                            response = generate_response(
                                prompt,
                                model=selected_model,
                                temperature=0.45,
                                provider=llm_provider,
                            )
                            timings[f"llm_response_generation_{student.name}"] = time.perf_counter() - t

                        responder_text[student.name] = {
                            "text": response,
                            "score": score,
                        }

                        if classification["move_type"] == "praise":
                            outcome = "praised"
                        elif classification["move_type"] == "correction":
                            outcome = "corrected"
                        else:
                            if result["answer_quality"] == "correct":
                                outcome = "success"
                            elif result["answer_quality"] in ["partial", "incorrect", "dont_know"]:
                                outcome = "struggle"
                            else:
                                outcome = "none"

                        apply_post_response_effect(
                            student,
                            result,
                            was_selected=True,
                            outcome=outcome,
                            experiment_mode=experiment_mode,
                            active_task=st.session_state.active_task,
                        )

                    for student in students:
                        if student.name not in selected_names:
                            apply_post_response_effect(
                                student,
                                turn_contexts[student.name],
                                was_selected=False,
                                outcome="silent",
                                experiment_mode=experiment_mode,
                                active_task=st.session_state.active_task,
                            )

                if experiment_mode:
                    neutralize_all_students(students)

                post_turn_states = {
                    student.name: snapshot_state(student)
                    for student in students
                }

                for student in students:
                    before = pre_turn_states[student.name]
                    after = post_turn_states[student.name]
                    deltas = compute_deltas(before, after)

                    round_data["student_updates"].append({
                        "student_name": student.name,
                        "answered": student.name in selected_names,
                        "response_text": responder_text.get(student.name, {}).get("text"),
                        "priority_score": next(
                            (s["score"] for s in round_data["all_scores"] if s["student_name"] == student.name),
                            None,
                        ),
                        "before": before,
                        "after": after,
                        "delta": deltas,
                    })

                for student_name, info in responder_text.items():
                    matching_update = next(
                        u for u in round_data["student_updates"] if u["student_name"] == student_name
                    )

                    round_data["responses"].append({
                        "student_name": student_name,
                        "student_response": info["text"],
                        "priority_score": info["score"],
                        "state": matching_update["after"],
                    })

                timings["total_turn_time"] = time.perf_counter() - total_start
                st.session_state.history.append(round_data)

        except Exception as e:
            st.error(f"Error: {e}")

    if not st.session_state.history:
        st.write("No classroom interaction yet.")

    for idx, item in enumerate(reversed(st.session_state.history)):
        cls = item["classification"]
        raw_cls = item.get("raw_classification", {})
        mode_label = "ON" if item.get("experiment_mode", False) else "OFF"
        lang_label = "non-English" if cls.get("non_english_input", False) else "English"
        provider_label = item.get("llm_provider", "unknown")
        model_label = item.get("selected_model", "unknown")
        title = f"Turn {item.get('turn_index', '?')} — {cls['move_type']} — {shorten(item['teacher'], 60)}"

        with st.expander(title, expanded=(idx == 0)):
            st.markdown(f"**Teacher:** {item['teacher']}")

            if item.get("timings"):
                total_time = item["timings"].get("total_turn_time", 0)
                classification_time = item["timings"].get("llm_classification", 0)
                generation_total = sum(
                    value for key, value in item["timings"].items()
                    if key.startswith("llm_response_generation")
                )

                st.info(
                    f"Total: {total_time:.2f}s | "
                    f"Classification: {classification_time:.2f}s | "
                    f"Response generation: {generation_total:.2f}s"
                )

            st.markdown(
                f"""
                <span style="background:#ecfeff; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Move: {cls["move_type"]}
                </span>
                <span style="background:#f0fdf4; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Tone: {cls["tone"]}
                </span>
                <span style="background:#fefce8; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Directed to: {cls["directed_to"]}
                </span>
                <span style="background:#f3e8ff; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Experiment Mode: {mode_label}
                </span>
                <span style="background:#e0f2fe; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Input language: {lang_label}
                </span>
                <span style="background:#fee2e2; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Provider: {provider_label}
                </span>
                <span style="background:#dcfce7; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    Model: {model_label}
                </span>
                """,
                unsafe_allow_html=True,
            )

            with st.expander("AI vs final classification", expanded=False):
                st.markdown("**Raw AI classification**")
                st.json(raw_cls)

                st.markdown("**Final classification after app rules**")
                st.json(cls)

            if item.get("timings"):
                with st.expander("Timing breakdown", expanded=False):
                    for name, seconds in item["timings"].items():
                        st.write(f"{name}: {seconds:.2f}s")

            if item.get("active_task", {}).get("description"):
                with st.expander("Active task at this turn", expanded=False):
                    st.json(item["active_task"])

            if item.get("recent_context"):
                with st.expander("Recent memory used for this turn", expanded=False):
                    st.text(item["recent_context"])

            if cls.get("non_english_input", False):
                st.info("Non-English teacher input detected by the model. Students used limited classroom reactions.")

            score_html = ""
            for s in item["all_scores"]:
                score_html += f"""
                <span style="background:#eef2ff; padding:4px 8px; border-radius:999px; font-size:0.8rem; margin-right:6px;">
                    {s["student_name"]}: {s["score"]:.2f}
                </span>
                """
            st.markdown(score_html, unsafe_allow_html=True)

            if item.get("no_response", False):
                st.markdown("_No student responds._")

            for r in item["responses"]:
                st.markdown(f"**{r['student_name']}:** {r['student_response']}")

            st.markdown("**State changes this turn**")

            for u in item["student_updates"]:
                status = "answered" if u["answered"] else "silent"
                status_bg = "#dcfce7" if u["answered"] else "#f3f4f6"

                st.markdown(
                    f"""
                    <div style="border:1px solid #e5e7eb; border-radius:12px; padding:10px; margin-bottom:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                            <strong>{u['student_name']}</strong>
                            <span style="background:{status_bg}; padding:4px 8px; border-radius:999px; font-size:0.8rem;">
                                {status}
                            </span>
                        </div>
                        <div style="margin-bottom:6px; color:#6b7280; font-size:0.9rem;">
                            Score: {u['priority_score']:.2f}
                        </div>
                    """,
                    unsafe_allow_html=True,
                )

                if u["response_text"]:
                    st.markdown(f"_Response:_ {u['response_text']}")

                for key, label in [
                    ("boredom", "Boredom"),
                    ("engagement", "Engagement"),
                    ("confusion", "Confusion"),
                    ("frustration", "Frustration"),
                    ("delight", "Delight"),
                    ("surprise", "Surprise"),
                ]:
                    delta = u["delta"][key]
                    dcolor = delta_color(delta)
                    dtext = format_delta(delta)
                    st.markdown(
                        f"""
                        <div style="display:flex; justify-content:space-between; font-size:0.9rem; margin-bottom:2px;">
                            <span>{label}</span>
                            <span>
                                {u["before"][key]:.2f} → {u["after"][key]:.2f}
                                <span style="color:{dcolor}; font-weight:600; margin-left:8px;">{dtext}</span>
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)