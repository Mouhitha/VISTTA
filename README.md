# A Weighted Approach to Student Persona Modeling in AI-Driven Educational Simulations

## Overview

This project explores research-informed student persona modeling for
AI-driven classroom simulation.

The system is designed to simulate interactions between a teacher and
multiple student agents in an educational setting. Each student agent
is modeled using a structured representation composed of knowledge,
personality, state, and memory. These components influence how
students interpret teacher input, decide whether to respond, and
generate classroom behavior.

The long-term goal of the project is to support preservice teacher
training through interactive educational simulation. Current work
focuses on investigating how different learner representation structures
affect simulated classroom interaction.

## Research Motivation

Many educational simulations rely on shallow or purely prompt-based
student personas. This project explores whether more structured and
research-informed learner representations can produce more coherent,
believable, and pedagogically meaningful classroom interaction.

The current learner model separates student representation into:
- Knowledge : conceptual understanding and misconceptions
- Personality : stable behavioral tendencies
- State : dynamic affective and cognitive conditions
- Memory : short-term interaction history

This separation allows different aspects of learner behavior to
influence classroom interaction independently while still interacting
dynamically during simulation.

## System Architecture

The system is organized as a modular classroom simulation pipeline
designed to separate learner representation, interaction logic, language
generation, and user interface concerns.

The architecture consists of four primary layers.

### User Interface Layer (`app.py`)

The Streamlit application provides the interactive classroom interface.
It is responsible for:

- receiving teacher input
- displaying classroom interaction
- visualizing student state
- maintaining conversation history
- coordinating simulation loop

This layer functions as the primary orchestration component for the
simulation.

### Learner Modeling Layer (`student_models.py`)

This layer defines the internal representation of simulated students.

Each student agent is composed of multiple interacting components:

- Knowledge
- Personality
- State
- Memory

Separating these dimensions allows the simulation to distinguish between:
- what a student knows
- how a student tends to behave
- how a student currently feels
- how recent interactions influence future behavior

This modular structure supports future expansion and experimentation with
alternative learner modeling approaches.

### Interaction Logic Layer (`students.py`)

This layer contains the behavioral and simulation logic governing
classroom interaction.

Responsibilities include:
- state updates
- turn-context construction
- response scoring
- participation modeling
- responder selection
- interaction memory updates

This layer acts as the bridge between learner representation and
observable classroom behavior.

### Language Generation Layer (`llm.py`)

This layer manages all interactions with large language models.

Responsibilities include:
- teacher input classification
- student prompt classification
- response generation
- simplified conversational reactions

The LLM layer converts structured learner state into natural-language
student responses while preserving the behavioral constraints defined
by the simulation pipeline.

## Student Representation Model

We model student agents as the interaction of four components:
- Knowledge : what the student knows and misunderstands
- Personality : stable behavioral tendencies
- State : moment-to-moment emotional and cognitive condition
- Memory : short-term interaction history

These components interact dynamically to produce realistic,
context-sensitive student behavior.

### Knowledge

Knowledge is represented using:
- correct concepts
- systematic misconceptions

Correct concepts are modeled using an overlay model approach in which
students possess a subset of concepts from a broader curricular
knowledge base.

Misconceptions represent persistent incorrect understandings or
reasoning patterns associated with specific concepts. They are modeled
using a bug library.

Knowledge and misconceptions are grounded in:
- curricular concept structures
- teacher-informed misconception examples
- educational learner modeling research

### Personality

Personality represents stable behavioral tendencies influencing
participation, emotional regulation, and responsiveness during classroom
interaction.

Trait dimensions are informed by educational psychology and the Big Five
personality framework.

Current dimensions include:
- Participation (extraversion)
- Emotional stability (inverse of neuroticism)
- Task orientation (conscientiousness)
- Receptiveness to guidance (agreeableness & openness to experience)

### State

State represents dynamic affective and cognitive conditions during
learning interaction.

Unlike personality traits, state variables fluctuate throughout classroom
interaction in response to teacher feedback, task difficulty, success and
failure, and participation patterns.

Current dimensions include:
- Boredom
- Engagement
- Confusion
- Frustration
- Delight
- Surprise

### Memory

Memory represents the short-term conversational and interaction history
within the classroom simulation.

Unlike knowledge, personality, adn affective state, memory is focused
primarily on recent classroom participation patterns and interaction
continuity.

Current memory variables include:
- turns since speaking
- silence streaks
- answer streaks
- recent praise
- recent correction
- previous interaction outcomes

The current memory system is intentionally lightweight and 
heuristic-based. Future work may explore more research-informed approaches
to educational agent memory and longitudinal learner adaptation.

## Interaction Pipeline

Each classroom interaction follows a multi-stage processing pipeline
designed to simulate classroom participation and student behavior.

### 1. Teacher Input

The simulation begins with teacher input entered through the Streamlit
interface.

Examples include:
- questions
- greetings
- praise
- corrections
- instructional statements

### 2. Input Classification

Teacher input is classified using the language model into structured
interaction categories, including:
- move type
- tone
- intended request
- expected response behavior

Additional rule-based refinement is applied to improve classification
consistency and classroom realism.

### 3. Student State Updates

Before response generation, each student's affective state is updated
based on:
- teacher tone
- interaction type
- targeting behavior
- recent classroom history

For example:
- praise may increase delight and engagement
- correction may increase confusion or frustration
- repeated difficulty may reduce participation

### 4. Turn Context Construction

A turn-specific interaction context is generated for each student.

This context combines:
- conceptual knowledge
- misconceptions
- personality traits
- affective state
- recent interaction history
- current classroom task information

The resulting context is used to estimate:
- response quality
- effort
- participation likelihood
- response style

### 5. Response Priority Calculation

Students are assigned weighted response-priority scores based on:
- participation tendencies
- emotional state
- conceptual understanding
- conversational history
- teacher targeting behavior

This stage determines which students are most likely to respond during
the current interaction.

### 6. Responder Selection

One or more student agents are selected probabilistically from the
highest-priority candidates.

Selection behavior varies depending on interaction type.

Examples:
- corrections typically target one student
- class questions may produce multiple responses
- informational statements may produce no response

### 7. Response Generation

Selected students generate natural-language responses using the language
model.

Prompts are constructed using:
- learner representation
- interaction context
- response quality
- conversational style

This allows generated responses to reflect differences in:
- understanding
- confidence
- misconceptions
- emotional state

### 8. Post-Interaction Updates

After responses are generated:
- memory variables are updated
- affective state is adjusted
- interaction history is stored

These updates influence future classroom behavior and create interaction
continuity across turns.

## File Structure

The app is organized to support modularity, clarity, and future expansion.

```
/data
    knowledge_base.json
    misconceptions.json

app.py
llm.py
student_models.py
students.py

requirements.txt
students.json
```

### At a Glance

`app.py` --> UI + main loop
`llm.py` --> LLM logic (classification + response)
`student_models.py` --> student representation model
`students.py` --> formulas + scoring
`students.json` --> student data

### `app.py`

This file serves as the main application for the project.

Does:
- Takes teacher input
- Calls LLM to classify input
- Applies rule-based fixes
- Updates student states
- Calculates scores
- Chooses responders
- Generates responses
- Saves history
- Displays results

Flow:
- Teacher input
- Classify teacher input
- Refine classification
- Update student state
- Compute derived variables
- Choose responders
- Generate response
- Save + display

### `llm.py`

This file handles contact with the LLM and is used to decide the system
behavior and ensure the final response sounds like a student.

There are two LLM options at this time:
- Ollama
- Gemini API

The first call to the LLM classifies the teacher input, returning:
- `move_type`
- `tone`
- `directed_to`

At this time, the possible move types include:
- question
- greeting
- praise
- correction
- information
- acknowledgement

Next, build the prompt for the second call to the LLM using:
- knowledge
- personality
- state
- answer quality
- response style

Then, generate the response by sending the prompt to the LLM.

In some cases, a short reaction can be generated instead of using the
LLM for maximal simplicity. Examples include:
- greeting --> Hi
- praise --> Thanks
- correction --> Okay

### `student_models.py`

Contains the student model representation. For more information, see
the "Student Representation Model" section.

### `students.py`

This file contains the core logic.

Contents include:
- formulas
- state updates
- scoring
- responder selection

#### Core Formulas

Correctness:
correctness = proficiency × (1 - confusion)

Meaning:
How likely the student is to answer correctly.

Why:
Confusion reduces performance even if knowledge is high.

Effort:
effort =
0.45 × engagement

0.25 × morale
0.20 × participation_tendency
0.10 × confidence

Meaning:
How much the student tries.

Why:
Students don’t only depend on knowledge, but also motivation.

Response Score:
response_score =
0.65 × correctness

0.35 × effort

Meaning:
Overall answer quality.

Used to decide:
correct / partial / incorrect / dont_know

Willingness:
willingness =
0.32 × participation_tendency

0.22 × confidence
0.16 × morale
0.18 × engagement
0.12 × confusion

Meaning:
Whether the student will speak.

Why:
Separates knowing from speaking.

Response Style:
willingness < 0.22 → silent
< 0.45 → hesitant
< 0.72 → normal
≥ 0.72 → confident

Meaning:
How the student speaks.

Answer Quality:
response_score ≥ 0.78 → correct
≥ 0.50 → partial
≥ 0.28 → incorrect
< 0.28 → dont_know

Meaning:
Type of answer sent to LLM.

RESPONSE PRIORITY (WHO SPEAKS)

score =
personality part

state part
knowledge part
control modifiers

Personality part:
0.28 × participation_tendency

0.18 × confidence

Why:
Confident and active students speak more.

State part:
0.14 × willingness

0.08 × engagement
0.05 × morale
0.08 × confusion

Why:
Current emotional state affects participation.

Knowledge part:
0.19 × correctness

Why:
Students who understand are more likely to answer.

Control modifiers:

If directed_to == student:
+0.60

Why:
If teacher calls a student, they should answer.

#### State Updates

Teacher input affects state:

Question:
engagement increases

Praise:
morale increases
engagement increases

Correction:
morale decreases
confusion increases

Post-response effects:

Success:
morale increases
confusion decreases
engagement increases

Struggle:
morale decreases
confusion increases

Silent:
silence streak increases

#### Responder Rules

information → no response
acknowledgement → no response
correction → only corrected student
praise → only praised student
question (named) → that student answers
question (class) → 1 (sometimes 2) students answer
greeting → 1–2 students answer

### `students.json`

Defines each student:
- knowledge (ability)
- personality (behavior traits)
- state (starting values)

## Setup

To set up the environment for this project, run these commands:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### API Configuration

This project requires a Gemini API key.

1. Create a key from Google AI Studio
2. Set the environment variable in your terminal:
```
export GEMINI_API_KEY="your_api_key_here"
```

## Running the Application

Start the Streamlit interface from the project root:

```
streamlit run app.py
```

The application will launch a local classroom simulation interface
where teacher prompts can be entered interactively.

## Future Work

Planned future improvements include:
- expanded misconception modeling
- research-informed memory architectures
- research-informed response score calculations
- research-informed persona design
- research-informed state updates
- strenghtened interdependency between knowledge, personality, and state
- incorporation of current classroom context
- research-informed classroom move types
- research-informed teacher move classification
- further alignment with general fifth-grade English education
- allowing knowledge representations to update dynamically
- incorporating greater variation in initial affective states
