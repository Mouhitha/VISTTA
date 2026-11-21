# Limitations

- Responses can vary across runs and depend on the installed model. A response that follows a persona prompt is one observation and does not establish consistent behavior.
- The app puts the lecture and question directly into the prompt. Instructions embedded in either field can compete with the persona and lecture-only instructions. The app does not detect prompt injection or check whether the answer is grounded in the lecture.
- The configured understanding scores are fixed inputs. The app does not infer understanding from the lecture or measure learning.
- This repository contains no formal quantitative evaluation or user study.
