from dataclasses import dataclass, field
from typing import List, Dict, Any
import json


@dataclass
class Knowledge:
    """
    Representation of a student's conceptual knowledge state.
    
    Knowledge is modeled as a combination of
    - correct concepts the student has mastered
    - systematic misconceptions that influence reasoning and responses
    
    This representation is informed by educational research on learner
    modeling, misconception theory, and knowledge overlays.
    
    Correct knowledge is represented through an overlay model, where
    students possess a subset of concepts from a broader curricular
    knowledge base.
    
    Misconceptions represent persistent incorrect understandings or
    reasoning patterns associated with particular concepts, implemented
    through a bug library.
    
    Attributes
    ----------
    correct_concepts : 
        Concepts the student currently understands correctly.
    misconceptions :
        Misconceptions currently associated with the student.
    knowledge_base :
        Hierarchical curricular knowledge structure used to contextualize
        concepts and identify unknown areas.
    misconception_base :
        Repository of possible misconceptions associated with curricular
        concepts.
    """
    correct_concepts: List[str]
    misconceptions: List[str]
    
    knowledge_base_path: str = field(
        default = "data/knowledge_base.json",
        init = False
    )
    
    misconception_base_path: str = field(
        default = "data/misconceptions.json",
        init = False
    )
    
    knowledge_base: Dict[str, Any] = field(init = False)
    misconception_base: Dict[str, Any] = field(init = False)
    
    def __post_init__(self):
        with open(self.knowledge_base_path, "r") as f:
            self.knowledge_base = json.load(f)
        with open(self.misconception_base_path, "r") as f:
            self.misconception_base = json.load(f)

@dataclass
class Personality:
    """
    Representation of the stable personality traits of a student,
    influencing classroom participation and learning behavior.
    
    Personality traits are modeled as relatively stable attributes that
    affect how students engage with classroom activities, respond to
    feedback, and regulate emotional reactions.
    
    Each attribute is represented as a float in the range [0, 1],
    indicating the intensity of the personality trait.
    
    Trait dimensions are informed by educational psychology and the
    Big Five personaity framework.
    
    Attributes
    ----------
    participation :
        Tendency to voluntarily engage in classroom interaction.
        Associated primarily with extraversion.
    emotional_stability :
        Resistance to anxiety, discouragement, and emotional
        dysregulation during learning activities.
        Inversely related to neuroticisim.
    task_orientation :
        Degree of persistance, organization, and goal-directed
        behavior during learning tasks.
        Associated with conscientiousness.
    receptiveness :
        Openness to guidance, correction, and collaboration.
        Associated with agreeableness adn openness.
        
    These traits influence both classroom behavior and the way dynamic
    affective states evolve over time.
    """
    participation: float
    emotional_stability: float
    task_orientation: float
    receptiveness: float

@dataclass
class State:
    """
    Representation of the dynamic affective state of a student during
    classroom interaction.
    
    Unlike personality traits, which are stable over time, state
    variables captures short-term emotional and cognitive conditions
    that fluctuate throughout learning activities.
    
    Each attribute is represented as a float in the range [0,1],
    indicating the intensity of the affective state.
    
    State dimensions are informed by research in educational affect,
    including work by D'Mello, Graesser, and Pekrun.
    
    Attributes
    ----------
    boredom :
        Disengagement or lack of interest in classroom activity.
    engagement :
        Focus, involvement, or flow during learning.
    confusion :
        Cognitive disequilibrium caused by uncertainty, misunderstanding,
        or incomplete knowledge.
    frustration :
        Negative emotional response to difficulty, failure, or repeated
        struggle.
    delight :
        Positive affect associated with understanding, success, or
        encouragement.
    surprise :
        Reaction to unexpected information or outcomes.
    
    State is influenced by both knowledge and personality. For example,
    misconceptions may increase confusion, while emotional stability may
    reduce frustration during difficulty.
    """
    boredom: float
    engagement: float
    confusion: float
    frustration: float
    delight: float
    surprise: float

@dataclass
class Memory:
    turns_since_spoke: int = 999
    silence_streak: int = 0
    answer_streak: int = 0
    recent_praise: int = 0
    recent_correction: int = 0
    last_outcome: str = "none"

@dataclass
class Student:
    """
    Unified representation of a simulated student agent.
    
    A student is modeled as the interaction of multiple components:
    - Knowledge :
        What the student understands and misunderstands.
    - Personality :
        Stable traits influencing participation, emotional regulation,
        and receptiveness.
    - State :
        Dynamic affective conditions that fluctuate during classroom
        interaction.
    - Memory :
        Short-term interaction history used to influence conversational
        continuity and behavioral adaptation.
    
    This class serves as the primary interface for learner modeling
    within the classroom simulation system.
    """
    name: str
    knowledge: Knowledge
    personality: Personality
    state: State
    memory: Memory = field(default_factory=Memory)