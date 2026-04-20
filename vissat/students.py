import json

def load_students():
    with open("students.json", "r") as file:
        return json.load(file)