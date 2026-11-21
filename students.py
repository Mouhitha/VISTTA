import json
from pathlib import Path

STUDENTS_PATH = Path(__file__).resolve().parent / "students.json"
STRING_FIELDS = ("name", "personality", "knowledge", "emotion", "avatar")


def load_students():
    try:
        with STUDENTS_PATH.open(encoding="utf-8") as file:
            students = json.load(file)
    except OSError as error:
        raise OSError(f"Could not read the student configuration at {STUDENTS_PATH}.") from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"{STUDENTS_PATH} must contain valid UTF-8 JSON.") from error

    if not isinstance(students, list) or not students:
        raise ValueError("students.json must contain a nonempty list of students.")

    for index, student in enumerate(students, start=1):
        if not isinstance(student, dict):
            raise ValueError(f"Student {index} in students.json must be an object.")
        for field in STRING_FIELDS:
            if not isinstance(student.get(field), str):
                raise ValueError(f"Student {index} in students.json must have a string '{field}'.")

        understanding = student.get("understanding")
        if (
            isinstance(understanding, bool)
            or not isinstance(understanding, (int, float))
            or not 0 <= understanding <= 1
        ):
            raise ValueError(
                f"Student {index} in students.json must have a numeric 'understanding' "
                "between 0 and 1."
            )

    return students
