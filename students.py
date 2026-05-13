import json
import math
import random
from typing import List, Tuple, Dict, Optional, Any

from student_models import Student, Knowledge, Personality, State


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def set_neutral_state(student: Student) -> None:
    student.state.boredom = 0.5
    student.state.engagement = 0.5
    student.state.confusion = 0.5
    student.state.frustration = 0.5
    student.state.delight = 0.5
    student.state.surprise = 0.5


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


def clamp_active_task_attempts(active_task: dict | None) -> int:
    if not active_task:
        return 0
    try:
        return max(0, int(active_task.get("attempt_count", 0)))
    except Exception:
        return 0


def load_students(path: str = "students.json") -> List[Student]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    students = []
    for s in raw:
        students.append(
            Student(
                name=s["name"],
                knowledge=Knowledge(**s["knowledge"]),
                personality=Personality(**s["personality"]),
                state=State(**s["state"]),
            )
        )

    return students


def topic_flags(teacher_input: str) -> Tuple[bool, bool]:
    text = teacher_input.lower()

    misconception_triggered = False
    unknown_area_triggered = False

    if "he " in text or "she " in text or "goes" in text:
        misconception_triggered = True

    if "yesterday" in text or "past tense" in text or "did" in text:
        unknown_area_triggered = True

    return misconception_triggered, unknown_area_triggered


def calculate_willingness(student: Student, experiment_mode: bool = False) -> float:
    if experiment_mode:
        return 0.5

    willingness = (
        0.32 * student.personality.participation
        + 0.20 * student.personality.emotional_stability
        + (
            0.16 * student.state.delight
            + 0.18 * student.state.engagement
            - 0.12 * student.state.confusion
            - 0.15 * student.state.frustration
            - 0.10 * student.state.boredom
        )
    )

    return clamp(willingness)


def recalc_willingness(student: Student, experiment_mode: bool = False) -> float:
    return calculate_willingness(student, experiment_mode=experiment_mode)


def recalc_proficiency(student: Student) -> float:
    all_concepts = flatten_knowledge_base(student.knowledge.knowledge_base)
    knowledge_size = len(all_concepts)
    known_size = len(student.knowledge.correct_concepts)

    if knowledge_size > 0:
        return clamp(known_size / knowledge_size)

    return 0.0


def build_turn_context(
    student: Student,
    teacher_input: str,
    classification: dict,
    experiment_mode: bool = False,
    active_task: dict | None = None
) -> dict:
    if experiment_mode:
        set_neutral_state(student)

    move_type = classification.get("move_type", "information")
    secondary_move = classification.get("secondary_move", "none")
    non_english_input = classification.get("non_english_input", False)
    expects_response = classification.get("expects_response", move_type not in ["information", "acknowledgement"])

    misconception_triggered, unknown_area_triggered = topic_flags(teacher_input)

    attempts = clamp_active_task_attempts(active_task)
    repeated_task_pressure = max(0, attempts - 1)

    proficiency = recalc_proficiency(student)

    confidence = (
        student.personality.emotional_stability
        + student.personality.task_orientation
    ) / 2

    participation = student.personality.participation

    correctness = proficiency * (1.0 - student.state.confusion)

    if misconception_triggered:
        correctness -= 0.15

    if unknown_area_triggered:
        correctness -= 0.20

    correctness -= 0.03 * repeated_task_pressure
    correctness = clamp(correctness)

    effort = clamp(
        0.45 * student.state.engagement
        + 0.25 * student.state.delight
        + 0.20 * participation
        + 0.10 * confidence
    )

    response_score = clamp(0.65 * correctness + 0.35 * effort)

    willingness = calculate_willingness(student, experiment_mode=experiment_mode)

    if willingness < 0.22:
        response_style = "silent"
    elif willingness < 0.45:
        response_style = "hesitant"
    elif willingness < 0.72:
        response_style = "normal"
    else:
        response_style = "confident"

    if non_english_input:
        answer_quality = "dont_know"
    elif not expects_response:
        answer_quality = "correct"
    elif move_type in ["greeting", "praise", "correction"]:
        answer_quality = "correct"
    elif response_score >= 0.78:
        answer_quality = "correct"
    elif response_score >= 0.50:
        answer_quality = "partial"
    elif response_score >= 0.28:
        answer_quality = "incorrect"
    else:
        answer_quality = "dont_know"

    return {
        "move_type": move_type,
        "secondary_move": secondary_move,
        "tone": classification.get("tone", "neutral"),
        "directed_to": classification.get("directed_to", "none"),
        "expects_response": expects_response,
        "topic": classification.get("topic", "unknown"),
        "difficulty": classification.get("difficulty", "medium"),
        "correctness": correctness,
        "effort": effort,
        "response_score": response_score,
        "response_style": response_style,
        "answer_quality": answer_quality,
        "misconception_triggered": misconception_triggered,
        "unknown_area_triggered": unknown_area_triggered,
        "willingness": willingness,
        "non_english_input": non_english_input,
        "repeated_task_pressure": repeated_task_pressure,
    }


def apply_teacher_effect(
    student: Student,
    classification: dict,
    experiment_mode: bool = False,
    active_task: dict | None = None
) -> None:
    if experiment_mode:
        set_neutral_state(student)
        return

    move_type = classification.get("move_type", "information")
    secondary_move = classification.get("secondary_move", "none")
    tone = classification.get("tone", "neutral")
    directed_to = classification.get("directed_to", "none")
    non_english_input = classification.get("non_english_input", False)
    expects_response = classification.get("expects_response", move_type not in ["information", "acknowledgement"])

    attempts = clamp_active_task_attempts(active_task)
    repeated_task_pressure = max(0, attempts - 1)

    multiplier = 1.0

    delight = student.state.delight
    confusion = student.state.confusion
    engagement = student.state.engagement
    boredom = student.state.boredom
    frustration = student.state.frustration
    surprise = student.state.surprise

    confidence = (
        student.personality.emotional_stability
        + student.personality.task_orientation
    ) / 2

    if move_type == "question":
        if expects_response:
            if directed_to == student.name:
                engagement += multiplier * 0.035
                surprise += multiplier * 0.01
                confusion += multiplier * 0.015 * repeated_task_pressure
                frustration += multiplier * 0.01 * repeated_task_pressure
                delight -= multiplier * 0.015 * repeated_task_pressure * (1.2 - confidence)

            elif directed_to in ["class", "none"]:
                engagement += multiplier * 0.02
                confusion += multiplier * 0.006 * repeated_task_pressure

            else:
                engagement += multiplier * 0.005

            if recalc_proficiency(student) < 0.55:
                confusion += multiplier * 0.02

    elif move_type == "greeting":
        engagement += multiplier * 0.02
        delight += multiplier * 0.01
        boredom -= multiplier * 0.01

    elif move_type == "praise":
        praise_fatigue = min(student.memory.recent_praise, 5)

        if directed_to == student.name:
            if praise_fatigue <= 1:
                delight += multiplier * 0.07 * (0.5 + student.personality.receptiveness)
                engagement += multiplier * 0.03
                frustration -= multiplier * 0.02
            elif praise_fatigue <= 3:
                delight += multiplier * 0.015
                engagement += multiplier * 0.005
            else:
                delight += multiplier * 0.002
                engagement -= multiplier * 0.005

        elif directed_to == "class":
            if praise_fatigue <= 1:
                delight += multiplier * 0.018
            elif praise_fatigue <= 3:
                delight += multiplier * 0.006
            else:
                engagement -= multiplier * 0.003

    elif move_type == "correction":
        correction_stack = min(student.memory.recent_correction, 3)

        if directed_to == student.name:
            delight -= multiplier * (0.06 + 0.02 * correction_stack) * (1.4 - student.personality.receptiveness)
            confusion += multiplier * (0.04 + 0.015 * correction_stack)
            frustration += multiplier * (0.03 + 0.01 * correction_stack) * (1.2 - student.personality.emotional_stability)
        else:
            engagement -= multiplier * 0.01

    elif move_type == "information":
        engagement -= multiplier * 0.005
        boredom += multiplier * 0.005

    elif move_type == "acknowledgement":
        engagement -= multiplier * 0.01

    if secondary_move == "praise":
        praise_fatigue = min(student.memory.recent_praise, 5)

        if directed_to == student.name or directed_to == "class":
            if praise_fatigue <= 1:
                delight += multiplier * 0.02
            elif praise_fatigue <= 3:
                delight += multiplier * 0.005
            else:
                engagement -= multiplier * 0.003

    if secondary_move == "correction":
        if directed_to == student.name:
            confusion += multiplier * 0.02
            frustration += multiplier * 0.015
            delight -= multiplier * 0.02 * (1.4 - student.personality.receptiveness)

    if tone == "positive":
        delight += multiplier * 0.006
        frustration -= multiplier * 0.004
    elif tone == "negative":
        delight -= multiplier * 0.02
        frustration += multiplier * 0.02

    if non_english_input:
        confusion += multiplier * 0.03
        engagement -= multiplier * 0.01
        surprise += multiplier * 0.02

    student.state.boredom = clamp(boredom)
    student.state.engagement = clamp(engagement)
    student.state.confusion = clamp(confusion)
    student.state.frustration = clamp(frustration)
    student.state.delight = clamp(delight)
    student.state.surprise = clamp(surprise)


def apply_post_response_effect(
    student: Student,
    turn_context: dict,
    was_selected: bool,
    outcome: str,
    experiment_mode: bool = False,
    active_task: dict | None = None
) -> None:
    multiplier = 1.0

    attempts = clamp_active_task_attempts(active_task)
    repeated_task_pressure = max(0, attempts - 1)

    boredom = student.state.boredom
    engagement = student.state.engagement
    confusion = student.state.confusion
    frustration = student.state.frustration
    delight = student.state.delight
    surprise = student.state.surprise

    if was_selected:
        student.memory.turns_since_spoke = 0
        student.memory.silence_streak = 0
        student.memory.answer_streak += 1
    else:
        student.memory.turns_since_spoke += 1
        student.memory.answer_streak = 0
        student.memory.silence_streak += 1

    student.memory.recent_praise = max(0, student.memory.recent_praise - 1)
    student.memory.recent_correction = max(0, student.memory.recent_correction - 1)

    if experiment_mode:
        if outcome == "success":
            student.memory.last_outcome = "success"
        elif outcome == "struggle":
            student.memory.last_outcome = "struggle"
        elif outcome == "praised":
            student.memory.recent_praise += 2
            student.memory.last_outcome = "praised"
        elif outcome == "corrected":
            student.memory.recent_correction += 2
            student.memory.last_outcome = "corrected"
        elif outcome == "silent":
            student.memory.last_outcome = "silent"
        else:
            student.memory.last_outcome = "none"

        set_neutral_state(student)
        return

    if outcome == "success":
        delight += multiplier * 0.05
        confusion -= multiplier * 0.04
        engagement += multiplier * 0.03
        boredom -= multiplier * 0.02
        frustration -= multiplier * 0.02
        student.memory.last_outcome = "success"

    elif outcome == "struggle":
        delight -= multiplier * (0.03 + 0.015 * repeated_task_pressure)
        confusion += multiplier * (0.05 + 0.02 * repeated_task_pressure)
        frustration += multiplier * (0.03 + 0.015 * repeated_task_pressure)
        engagement -= multiplier * 0.01
        student.memory.last_outcome = "struggle"

    elif outcome == "praised":
        praise_fatigue = min(student.memory.recent_praise, 5)

        if praise_fatigue <= 1:
            delight += multiplier * 0.05
            engagement += multiplier * 0.025
            frustration -= multiplier * 0.02
        elif praise_fatigue <= 3:
            delight += multiplier * 0.012
            engagement += multiplier * 0.003
        else:
            delight += multiplier * 0.001
            engagement -= multiplier * 0.006

        student.memory.recent_praise += 2
        student.memory.last_outcome = "praised"

    elif outcome == "corrected":
        correction_stack = min(student.memory.recent_correction, 3)
        delight -= multiplier * (0.05 + 0.02 * correction_stack) * (1.3 - student.personality.receptiveness)
        confusion += multiplier * (0.04 + 0.015 * correction_stack)
        frustration += multiplier * (0.03 + 0.015 * correction_stack) * (1.2 - student.personality.emotional_stability)
        engagement -= multiplier * 0.01
        student.memory.recent_correction += 2
        student.memory.last_outcome = "corrected"

    elif outcome == "silent":
        student.memory.last_outcome = "silent"

        if student.memory.silence_streak >= 3:
            engagement -= multiplier * 0.015
            boredom += multiplier * 0.01

    else:
        student.memory.last_outcome = "none"

    if student.memory.recent_correction >= 2:
        delight -= multiplier * 0.02
        frustration += multiplier * 0.02

    if not was_selected and student.memory.turns_since_spoke >= 4:
        if student.personality.participation >= 0.6:
            engagement += multiplier * 0.01
        else:
            delight -= multiplier * 0.01
            boredom += multiplier * 0.01

    student.state.boredom = clamp(boredom)
    student.state.engagement = clamp(engagement)
    student.state.confusion = clamp(confusion)
    student.state.frustration = clamp(frustration)
    student.state.delight = clamp(delight)
    student.state.surprise = clamp(surprise)


def calculate_response_priority(
    student: Student,
    classification: dict,
    turn_context: dict,
    experiment_mode: bool = False
) -> float:
    if experiment_mode:
        set_neutral_state(student)

    move_type = classification.get("move_type", "information")
    directed_to = classification.get("directed_to", "none")
    expects_response = classification.get("expects_response", move_type not in ["information", "acknowledgement"])

    if not expects_response:
        return -999.0

    state_factor = 0.35 if experiment_mode else 1.0

    confidence = (
        student.personality.emotional_stability
        + student.personality.task_orientation
    ) / 2

    score = (
        0.28 * student.personality.participation
        + 0.18 * confidence
        + state_factor * (
            0.14 * calculate_willingness(student, experiment_mode=experiment_mode)
            + 0.08 * student.state.engagement
            + 0.05 * student.state.delight
            - 0.08 * student.state.confusion
            - 0.06 * student.state.boredom
            - 0.06 * student.state.frustration
        )
        + 0.19 * turn_context["correctness"]
        - 0.04 * turn_context.get("repeated_task_pressure", 0)
    )

    if directed_to == student.name:
        score += 0.60
    elif directed_to not in ["none", "class"]:
        if move_type == "question":
            score -= 0.45
        elif move_type == "correction":
            score -= 1.00
        elif move_type == "praise":
            score -= 0.80

    if move_type == "question":
        score += 0.06
    elif move_type == "greeting":
        score += 0.05
    elif move_type == "praise":
        if directed_to == student.name:
            score += 0.30
        elif directed_to == "class":
            score += 0.04
        else:
            score -= 0.18
    elif move_type == "correction":
        if directed_to == student.name:
            score += 0.18
        else:
            score -= 0.22
    elif move_type == "information":
        score -= 0.80
    elif move_type == "acknowledgement":
        score -= 1.00

    if not experiment_mode:
        if student.memory.turns_since_spoke == 0:
            score -= 0.18
        elif student.memory.turns_since_spoke == 1:
            score -= 0.08

        if student.memory.turns_since_spoke >= 4:
            score += 0.05

        if student.memory.recent_correction >= 2:
            score -= 0.06

    return score


def softmax_sample(candidates: List[Tuple[Student, float]], temperature: float = 0.6) -> Optional[Tuple[Student, float]]:
    if not candidates:
        return None

    values = [score / max(temperature, 1e-6) for _, score in candidates]
    m = max(values)
    exps = [math.exp(v - m) for v in values]
    total = sum(exps)
    probs = [e / total for e in exps]

    idx = random.choices(range(len(candidates)), weights=probs, k=1)[0]
    return candidates[idx]


def choose_responders(
    students: List[Student],
    classification: dict,
    turn_contexts: Dict[str, dict],
    similarity_threshold: float = 0.08,
    rng: Optional[random.Random] = None,
    experiment_mode: bool = False,
):
    rng = rng or random
    move_type = classification.get("move_type", "information")
    directed_to = classification.get("directed_to", "none")
    expects_response = classification.get("expects_response", move_type not in ["information", "acknowledgement"])

    all_scores = []
    for student in students:
        score = calculate_response_priority(
            student,
            classification,
            turn_contexts[student.name],
            experiment_mode=experiment_mode
        )
        all_scores.append((student, score))

    all_scores.sort(key=lambda x: x[1], reverse=True)

    if not expects_response:
        return [], all_scores

    if move_type in ["acknowledgement", "information"]:
        return [], all_scores

    if not all_scores:
        return [], all_scores

    responders = []
    top_score = all_scores[0][1]

    if move_type == "correction":
        if directed_to not in ["none", "class"]:
            target = next((pair for pair in all_scores if pair[0].name == directed_to), None)
            if target and target[1] > -0.50:
                return [target], all_scores
            return [], all_scores

        if all_scores[0][1] > -0.50:
            return [all_scores[0]], all_scores

        return [], all_scores

    if move_type == "praise":
        if directed_to not in ["none", "class"]:
            target = next((pair for pair in all_scores if pair[0].name == directed_to), None)
            if target and target[1] > -0.50:
                return [target], all_scores
            return [], all_scores

        if directed_to == "class":
            candidates = [pair for pair in all_scores if pair[1] > -0.20]
            return candidates[:2], all_scores

        if all_scores[0][1] > -0.20:
            return [all_scores[0]], all_scores

        return [], all_scores

    if move_type == "question" and directed_to not in ["none", "class"]:
        target = next((pair for pair in all_scores if pair[0].name == directed_to), None)
        others = [pair for pair in all_scores if pair[0].name != directed_to]

        if target is None:
            return [], all_scores

        if target[1] < -0.10 and not experiment_mode:
            return [], all_scores

        responders.append(target)

        interruption_prob = 0.0 if experiment_mode else 0.08

        if others:
            best_other = others[0]
            best_other_confidence = (
                best_other[0].personality.emotional_stability
                + best_other[0].personality.task_orientation
            ) / 2

            if (
                rng.random() < interruption_prob
                and best_other[1] > 0.55
                and best_other[0].personality.participation > 0.65
                and best_other_confidence > 0.55
            ):
                responders.append(best_other)

        return responders[:2], all_scores

    if move_type == "question":
        if top_score < -0.25 and not experiment_mode:
            return [], all_scores

        if experiment_mode:
            silence_prob = 0.0
        else:
            if top_score < 0:
                silence_prob = 0.75
            elif top_score < 0.25:
                silence_prob = 0.45
            elif top_score < 0.45:
                silence_prob = 0.22
            else:
                silence_prob = 0.08

        if rng.random() < silence_prob:
            return [], all_scores

        top_candidates = all_scores[: min(3, len(all_scores))]
        first = softmax_sample(top_candidates, temperature=0.55)

        if first:
            responders.append(first)

        if (
            not experiment_mode
            and directed_to in ["class", "none"]
            and len(all_scores) > 1
            and responders
            and abs(all_scores[0][1] - all_scores[1][1]) <= similarity_threshold
            and rng.random() < 0.25
        ):
            remaining = [x for x in top_candidates if x[0].name != responders[0][0].name]
            second = softmax_sample(remaining, temperature=0.7)
            if second:
                responders.append(second)

        return responders, all_scores

    if move_type == "greeting":
        if top_score < -0.10 and not experiment_mode:
            return [], all_scores

        if experiment_mode:
            silence_prob = 0.0
        else:
            if top_score < 0.20:
                silence_prob = 0.30
            else:
                silence_prob = 0.12

        if rng.random() < silence_prob:
            return [], all_scores

        top_candidates = all_scores[: min(3, len(all_scores))]
        first = softmax_sample(top_candidates, temperature=0.7)

        if first:
            responders.append(first)

        if len(all_scores) > 1 and responders and rng.random() < 0.35 and not experiment_mode:
            remaining = [x for x in top_candidates if x[0].name != responders[0][0].name]
            second = softmax_sample(remaining, temperature=0.9)
            if second:
                responders.append(second)

        return responders[:2], all_scores

    return [], all_scores