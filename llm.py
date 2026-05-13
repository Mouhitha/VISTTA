import json
import random
import re
import requests
import os
from typing import Any, List
import streamlit as st
from google import genai
from google.genai import types


GREETING_REPLIES = ["Hi", "Hello", "Hi teacher", "Hello teacher"]
PRAISE_REPLIES = ["Thanks", "Thank you", "Okay", "Yay, thanks"]
CORRECTION_REPLIES = ["Okay", "Sorry", "Oh, okay", "I understand", "Okay, I try again"]
NON_ENGLISH_REPLIES = [
    "In English?",
    "Can you say it in English?",
    "I don't understand",
    "Sorry?",
]




def get_gemini_client():
    if "GEMINI_API_KEY" not in st.secrets:
        raise RuntimeError("GEMINI_API_KEY is missing in Streamlit secrets")

    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(api_key=api_key)

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


def short_reaction(move_type: str) -> str:
    if move_type == "greeting":
        return random.choice(GREETING_REPLIES)
    if move_type == "praise":
        return random.choice(PRAISE_REPLIES)
    if move_type == "correction":
        return random.choice(CORRECTION_REPLIES)
    return ""


def non_english_reaction() -> str:
    return random.choice(NON_ENGLISH_REPLIES)


def extract_json_object(text: str) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found")

    return json.loads(match.group(0))


def build_recent_context(history: list, max_turns: int = 4, active_task_text: str = "") -> str:
    if not history and not active_task_text:
        return ""

    recent = history[-max_turns:]
    lines = []

    lines.append("Recent classroom memory:")
    lines.append(
        "Use this memory to understand teacher follow-ups, corrections, repeated praise, repeated questions, "
        "and whether a student response is actually expected."
    )

    if active_task_text:
        lines.append("")
        lines.append("Structured active task memory:")
        lines.append(active_task_text)

    last_question = None
    last_responder = None
    last_response = None

    for item in recent:
        teacher = item.get("teacher", "")
        cls = item.get("classification", {})
        move_type = cls.get("move_type", "information")
        secondary_move = cls.get("secondary_move", "none")
        directed_to = cls.get("directed_to", "none")
        expects_response = cls.get("expects_response", False)

        lines.append(f"Teacher said: {teacher}")
        lines.append(
            f"Classified as: {move_type}; Secondary: {secondary_move}; "
            f"Directed to: {directed_to}; Expects response: {expects_response}"
        )

        if move_type == "question":
            last_question = teacher

        for r in item.get("responses", []):
            student_name = r.get("student_name", "")
            student_response = r.get("student_response", "")
            lines.append(f"{student_name} replied: {student_response}")
            last_responder = student_name
            last_response = student_response

    lines.append("")
    lines.append("Inferred recent context:")
    lines.append(f"- Last active task/question: {last_question if last_question else 'none'}")
    lines.append(f"- Last student who answered: {last_responder if last_responder else 'none'}")
    lines.append(f"- Last student answer: {last_response if last_response else 'none'}")

    return "\n".join(lines)


def build_student_prompt(student, teacher_input: str, turn_result: dict, recent_context: str = "") -> str:
    correct_concepts = (
        ", ".join(student.knowledge.correct_concepts)
        if student.knowledge.correct_concepts
        else "none"
    )

    misconceptions = (
        ", ".join(student.knowledge.misconceptions)
        if student.knowledge.misconceptions
        else "none"
    )

    all_concepts = flatten_knowledge_base(student.knowledge.knowledge_base)

    unknown_areas_list = [
        concept
        for concept in all_concepts
        if concept not in student.knowledge.correct_concepts
    ]

    unknown_areas = (
        ", ".join(unknown_areas_list)
        if unknown_areas_list
        else "none"
    )

    move_type = turn_result.get("move_type", "question")
    secondary_move = turn_result.get("secondary_move", "none")
    non_english_input = turn_result.get("non_english_input", False)
    expects_response = turn_result.get("expects_response", True)

    if non_english_input:
        extra_rules = """
- The classroom language is English.
- The teacher input is not in English.
- Do NOT answer the content normally.
- Respond only with a very short reaction such as:
  "In English?"
  "Can you say it in English?"
  "I don't understand"
  "Sorry?"
- Keep it very short.
"""
    elif not expects_response:
        extra_rules = """
- The teacher is not really asking for a student answer.
- If you respond at all, respond very briefly.
- Do not invent a new answer or task.
"""
    elif move_type == "question":
        extra_rules = """
- This is a question, task, or continuation of a previous task.
- If the teacher input is short or vague, use RECENT CLASSROOM MEMORY to understand the task.
- If there is an active task, answer that task.
- If the teacher asks "what do you think", "are you sure", or "do you agree", respond based on the recent classroom discussion.
- Do not invent a completely new task.
- Answer like a real student in class, not like an expert.
- Keep it short: usually 1 sentence, sometimes 2 short sentences.
- Use simple everyday English.
- Do not use rare or advanced words just because you know them.
- Do not try to impress the teacher.
- If answer_quality is "correct", give a simple correct answer a child might know.
- If answer_quality is "partial", give a partly correct or uncertain answer.
- If answer_quality is "incorrect", make a realistic learner mistake.
- If answer_quality is "dont_know", say you do not know or guess simply.
- Small learner mistakes are allowed if answer_quality is partial or incorrect.
"""
    elif move_type == "greeting":
        extra_rules = """
- This is a greeting.
- Respond very shortly.
"""
    elif move_type == "praise":
        extra_rules = """
- The teacher is praising the student.
- Respond very shortly and naturally.
"""
    elif move_type == "correction":
        extra_rules = """
- The teacher is correcting the student.
- Do NOT repeat the corrected full sentence unless explicitly asked to repeat it.
- Respond only with a short reaction.
- Good examples:
  "Okay"
  "Sorry"
  "Oh, okay"
  "I understand"
- Keep it very short.
"""
    elif move_type == "information":
        extra_rules = """
- This is information only.
- Normally do not answer.
"""
    else:
        extra_rules = """
- This is a short classroom exchange.
- Keep the response short and natural.
"""

    recent_context_block = ""
    if recent_context:
        recent_context_block = f"""
RECENT CLASSROOM MEMORY
{recent_context}
"""

    recent_student_context = f"""
Recent student memory
- Turns since this student last spoke: {student.memory.turns_since_spoke}
- Silence streak: {student.memory.silence_streak}
- Answer streak: {student.memory.answer_streak}
- Recent praise count: {student.memory.recent_praise}
- Recent correction count: {student.memory.recent_correction}
- Last outcome: {student.memory.last_outcome}
"""

    return f"""
You are a Swedish child aged 10-12 learning English in school.

Your job is to respond like a real student in class, not like an AI assistant.

The classroom language is English.
If the teacher uses another language, do not continue normally. Ask for English briefly.

Use simple English suitable for a Swedish child aged 10-12.
Do not use advanced, rare, technical, or encyclopedic words unless the teacher directly teaches them.
Do not try to impress the teacher.
Do not answer like a dictionary, search engine, or AI assistant.
If the question asks for something difficult or outside normal child knowledge, give a simple uncertain answer.
Do not speak like a teacher.
Keep the answer short and natural.
Do not explain your profile or internal state.
Return only the student's reply.

Important realism rule:
If a real 10-12-year-old English learner would probably not know the answer, do not give an expert answer.
Prefer a simple guess, a partial answer, or "I don't know".
The student can be wrong, unsure, simple, or incomplete. That is realistic.
Never show off with very advanced vocabulary.
Use only common school-level English words unless the teacher gives a specific word.
For vocabulary questions, prefer simple words like elephant, beautiful, interesting, computer, classroom, football, yesterday, or because.
Do not answer with famous "longest words" such as antidisestablishmentarianism or pneumonoultramicroscopicsilicovolcanoconiosis.

{recent_context_block}

STUDENT PROFILE

Name: {student.name}

Knowledge
- Correct Concepts: {correct_concepts}
- Misconceptions: {misconceptions}
- Unknown Areas: {unknown_areas}

Personality
- Participation Tendency: {student.personality.participation}
- Emotional Stability: {student.personality.emotional_stability}
- Task Orientation: {student.personality.task_orientation}
- Receptiveness to Guidance: {student.personality.receptiveness}

Current State
- Boredom: {student.state.boredom}
- Engagement: {student.state.engagement}
- Confusion: {student.state.confusion}
- Frustration: {student.state.frustration}
- Delight: {student.state.delight}
- Surprise: {student.state.surprise}

{recent_student_context}

CURRENT TURN DECISION
- Classroom move type: {turn_result["move_type"]}
- Secondary move: {secondary_move}
- Tone: {turn_result["tone"]}
- Expects student response: {expects_response}
- Response style: {turn_result["response_style"]}
- Answer quality: {turn_result["answer_quality"]}
- Topic: {turn_result.get("topic", "unknown")}
- Difficulty: {turn_result.get("difficulty", "medium")}
- Non-English teacher input: {non_english_input}

Rules:
- "correct" means answer correctly in simple English
- "partial" means partly correct but not perfect
- "incorrect" means make a realistic learner mistake
- "dont_know" means sound unsure or say you do not know
- If response style is hesitant, sound unsure
- If response style is confident, sound more certain
- Use misconceptions if relevant
- Struggle with unknown areas if relevant
- Do not use knowledge that is unrealistic for this child profile
{extra_rules}

TEACHER INPUT
{teacher_input}
""".strip()


def generate_response(
    prompt: str,
    model: str = "llama3",
    temperature: float = 0.45,
    provider: str = "ollama"
) -> str:
    if provider == "gemini":
        client = get_gemini_client()

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=45,
            ),
        )

        if response.text:
            return response.text.strip()

        return "I don't know."

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        },
        timeout=120
    )

    data = response.json()

    if "response" in data:
        return data["response"].strip()

    if "error" in data:
        return f"ERROR: {data['error']}"

    return f"Unexpected response: {data}"


def build_classification_prompt(text: str, student_names: list[str], recent_context: str = "", strict_retry: bool = False) -> str:
    names = "|".join(student_names)
    memory_block = f"\nRecent classroom memory:\n{recent_context}\n" if recent_context else ""

    retry_line = ""
    if strict_retry:
        retry_line = """
Your previous answer was not valid JSON. This time return ONLY one valid JSON object.
No markdown. No explanation. No text before or after the JSON.
"""

    return f"""
{retry_line}
You are the classroom-intent brain for a teacher-training simulation.

The students are Swedish children aged 10-12 learning English.

Return ONLY valid JSON. No markdown. No explanation outside the JSON.

Use this exact JSON format:
{{
  "move_type": "question|greeting|praise|correction|information|acknowledgement",
  "secondary_move": "none|praise|correction|information|question|acknowledgement",
  "tone": "positive|neutral|negative",
  "directed_to": "{names}|class|none",
  "expects_response": true,
  "topic": "vocabulary|grammar|sentence_structure|past_tense|pronouns|classroom_management|unknown",
  "difficulty": "easy|medium|hard",
  "non_english_input": false,
  "reason": "short explanation"
}}

Important:
- If one sentence praises one student and then asks another student to do something, the PRIMARY move is the question and directed_to is the student being asked.
- Example: "Good job Emma. Now Leo, could you make a sentence using banana?"
  means move_type question, secondary_move praise, directed_to Leo.
- The target of the response-eliciting action is more important than the first name mentioned.
- If there is "Now Leo", "Leo, could you", "Leo can you", directed_to should be Leo.
- If there is "Now Emma", "Emma, could you", "Emma can you", directed_to should be Emma.
- If teacher says "Good job to both of you", "you both", "everyone", or similar, directed_to should be class.
- If teacher says "The correct way is..." or "No, the verb is...", it is correction/information and usually expects_response is false.
- If teacher asks students to answer, try, make a sentence, explain, or give an opinion, expects_response is true.
- If teacher says "Hello class", it is English, greeting, directed_to class, non_english_input false.
- If teacher says "What did you do yesterday?", it is question, directed_to class, topic past_tense.
- If teacher says "go on", "continue", "try again", "try your best", "same question", or "your turn", use memory and classify as question.
- If praise/correction/acknowledgement has no explicit target, infer it is directed to the most recent student who answered.

Examples:

Teacher: "Good job Emma. Now Leo, could you make a sentence using word banana?"
{{
  "move_type": "question",
  "secondary_move": "praise",
  "tone": "positive",
  "directed_to": "Leo",
  "expects_response": true,
  "topic": "sentence_structure",
  "difficulty": "medium",
  "non_english_input": false,
  "reason": "Teacher praises Emma, then asks Leo to make a sentence."
}}

Teacher: "No, the verb is eat. A verb is what you are doing. Good try."
{{
  "move_type": "correction",
  "secondary_move": "praise",
  "tone": "positive",
  "directed_to": "none",
  "expects_response": false,
  "topic": "grammar",
  "difficulty": "easy",
  "non_english_input": false,
  "reason": "Teacher corrects the answer and adds encouragement; no new answer is requested."
}}

Teacher: "Okay so what did you guys do yesterday?"
{{
  "move_type": "question",
  "secondary_move": "none",
  "tone": "neutral",
  "directed_to": "class",
  "expects_response": true,
  "topic": "past_tense",
  "difficulty": "medium",
  "non_english_input": false,
  "reason": "Teacher asks the class a question about yesterday."
}}

Teacher: "Hello class!"
{{
  "move_type": "greeting",
  "secondary_move": "none",
  "tone": "positive",
  "directed_to": "class",
  "expects_response": true,
  "topic": "classroom_management",
  "difficulty": "easy",
  "non_english_input": false,
  "reason": "Teacher greets the class."
}}

{memory_block}

Teacher input:
{text}
""".strip()


def normalize_classification(parsed: dict) -> dict:
    return {
        "move_type": parsed.get("move_type", "information"),
        "secondary_move": parsed.get("secondary_move", "none"),
        "tone": parsed.get("tone", "neutral"),
        "directed_to": parsed.get("directed_to", "none"),
        "expects_response": bool(parsed.get("expects_response", False)),
        "topic": parsed.get("topic", "unknown"),
        "difficulty": parsed.get("difficulty", "medium"),
        "non_english_input": bool(parsed.get("non_english_input", False)),
        "reason": parsed.get("reason", ""),
    }


def classify_teacher_input(
    text: str,
    student_names=None,
    model: str = "llama3",
    recent_context: str = "",
    provider: str = "ollama"
) -> dict:
    if student_names is None:
        student_names = ["Emma", "Leo", "Maya"]

    for attempt in range(2):
        prompt = build_classification_prompt(
            text=text,
            student_names=student_names,
            recent_context=recent_context,
            strict_retry=(attempt == 1)
        )

        if provider == "gemini":
            client = get_gemini_client()

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=220,
                    response_mime_type="application/json",
                ),
            )

            raw = response.text.strip() if response.text else ""

        else:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0
                    }
                },
                timeout=120
            )

            data = response.json()
            raw = data.get("response", "").strip()

        try:
            parsed = extract_json_object(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed JSON is not an object")

            result = normalize_classification(parsed)
            result["raw_model_output"] = raw
            return result

        except Exception:
            if attempt == 0:
                continue

    t = text.strip().lower()
    move_type = "information"
    secondary_move = "none"
    tone = "neutral"
    directed_to = "none"
    expects_response = False
    topic = "unknown"
    difficulty = "medium"
    reason = "Fallback classifier used after JSON retry failed."

    if any(x in t for x in ["wrong", "not right", "not quite", "you should say", "should have said", "better is", "correct way", "the verb is"]):
        move_type = "correction"
        expects_response = False
        topic = "grammar"

    elif any(x in t for x in ["good job", "well done", "great job", "nice work", "good work", "excellent", "very good", "super good"]):
        move_type = "praise"
        expects_response = True
        tone = "positive"

    if any(x in t for x in ["good try", "good job", "well done", "excellent", "very good", "super good"]):
        if move_type != "praise":
            secondary_move = "praise"
        tone = "positive"

    if any(x in t for x in ["go on", "continue", "try your best", "try again", "now you try", "same question", "your turn"]):
        move_type = "question"
        expects_response = True

    elif "?" in t or any(x in t for x in ["what", "why", "how", "when", "where", "who", "please", "can you", "could you", "make a sentence", "tell me", "answer", "try"]):
        move_type = "question"
        expects_response = True

    elif t in {"hello", "hi", "hello class", "hi class", "good morning", "good afternoon"}:
        move_type = "greeting"
        expects_response = True
        tone = "positive"

    elif t in {"ok", "okay", "yes", "yeah", "alright", "correct"}:
        move_type = "acknowledgement"
        expects_response = False

    if "yesterday" in t or "past tense" in t:
        topic = "past_tense"
    elif "verb" in t or "grammar" in t:
        topic = "grammar"
    elif "sentence" in t:
        topic = "sentence_structure"

    if any(x in t for x in ["both of you", "you both", "everyone", "all of you", "class", "you guys"]):
        directed_to = "class"
    else:
        mentioned = [name for name in student_names if re.search(rf"\b{re.escape(name.lower())}\b", t)]
        if move_type == "question" and mentioned:
            directed_to = mentioned[-1]
        elif mentioned:
            directed_to = mentioned[0]

    return {
        "move_type": move_type,
        "secondary_move": secondary_move,
        "tone": tone,
        "directed_to": directed_to,
        "expects_response": expects_response,
        "topic": topic,
        "difficulty": difficulty,
        "non_english_input": False,
        "reason": reason,
        "raw_model_output": "",
    }