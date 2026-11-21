import json
from pathlib import Path

import pytest

import students


@pytest.fixture
def student_config(tmp_path, monkeypatch):
    path = tmp_path / "students.json"
    student = {
        "name": "Élodie",
        "personality": "curious",
        "knowledge": "medium",
        "emotion": "engaged",
        "understanding": 0.6,
        "avatar": "avatars/student1.avif",
        "attention": 0.8,
        "memory": [],
    }
    monkeypatch.setattr(students, "STUDENTS_PATH", path)
    return path, student


def write_config(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_loads_valid_student(student_config):
    path, student = student_config
    write_config(path, [student])

    assert students.load_students() == [student]


@pytest.mark.parametrize("field", ["name", "personality", "knowledge", "emotion", "avatar"])
def test_requires_string_fields(student_config, field):
    path, student = student_config
    del student[field]
    write_config(path, [student])

    with pytest.raises(ValueError, match=f"Student 1.*string '{field}'"):
        students.load_students()


@pytest.mark.parametrize("understanding", [-0.1, 1.1, True, "0.6", None])
def test_rejects_invalid_understanding(student_config, understanding):
    path, student = student_config
    write_config(path, [dict(student, understanding=understanding)])

    with pytest.raises(ValueError, match="numeric 'understanding' between 0 and 1"):
        students.load_students()


@pytest.mark.parametrize("data", [[], {}])
def test_requires_nonempty_list(student_config, data):
    path, _ = student_config
    write_config(path, data)

    with pytest.raises(ValueError, match="nonempty list"):
        students.load_students()


def test_ignores_working_directory(tmp_path, monkeypatch):
    (tmp_path / "students.json").write_text("[]", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert students.STUDENTS_PATH == Path(students.__file__).resolve().with_name("students.json")
    loaded = students.load_students()
    assert [student["name"] for student in loaded] == ["Alice", "Bob", "Charlie"]
    assert all((students.STUDENTS_PATH.parent / student["avatar"]).is_file() for student in loaded)
