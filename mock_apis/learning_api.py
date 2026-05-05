"""
Mock Learning REST API — Layer 1 service on port 8002.
Returns realistic topic and resource data. No database needed.
Agents always access this through the MCP server, never directly.
"""
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Learning API", version="1.0")


class Topic(BaseModel):
    id: str
    name: str
    description: str
    estimated_hours: float
    difficulty: str
    category: str


class Resource(BaseModel):
    id: str
    title: str
    type: str
    url: str
    duration_min: int
    topic_id: str


class StudyBlock(BaseModel):
    time: str
    activity: str
    duration_min: int
    notes: str


class StudySchedule(BaseModel):
    topic: str
    total_hours: float
    blocks: list[StudyBlock]


_TOPICS = {
    "tech": [
        Topic(id="t1", name="Python Async Programming", description="Master asyncio, coroutines, and concurrent I/O in Python.", estimated_hours=4.0, difficulty="intermediate", category="tech"),
        Topic(id="t2", name="Large Language Models Explained", description="How transformers work, tokenization, attention mechanisms, and fine-tuning basics.", estimated_hours=3.0, difficulty="beginner", category="tech"),
        Topic(id="t3", name="Docker & Container Fundamentals", description="Build, ship, and run containers — from Dockerfile to docker-compose.", estimated_hours=3.5, difficulty="beginner", category="tech"),
        Topic(id="t4", name="System Design Basics", description="Learn how to design scalable systems: load balancers, caches, databases, and queues.", estimated_hours=5.0, difficulty="intermediate", category="tech"),
        Topic(id="t5", name="Graph Theory & Algorithms", description="BFS, DFS, shortest paths, and spanning trees — with Python implementations.", estimated_hours=4.0, difficulty="intermediate", category="tech"),
    ],
    "science": [
        Topic(id="s1", name="Quantum Computing Primer", description="Qubits, superposition, entanglement, and quantum gates — no physics PhD required.", estimated_hours=3.0, difficulty="beginner", category="science"),
        Topic(id="s2", name="Climate Science 101", description="How the greenhouse effect works, feedback loops, and what the data actually shows.", estimated_hours=2.5, difficulty="beginner", category="science"),
        Topic(id="s3", name="Neuroscience of Habit Formation", description="How habits are encoded in the brain and science-backed strategies to build new ones.", estimated_hours=2.0, difficulty="beginner", category="science"),
        Topic(id="s4", name="CRISPR & Gene Editing", description="How CRISPR-Cas9 works, current applications, and ethical considerations.", estimated_hours=3.0, difficulty="intermediate", category="science"),
    ],
    "arts": [
        Topic(id="a1", name="Photography Composition", description="Rule of thirds, leading lines, light, and storytelling through a lens.", estimated_hours=2.0, difficulty="beginner", category="arts"),
        Topic(id="a2", name="Music Theory Fundamentals", description="Scales, chords, rhythm, and how to read sheet music from scratch.", estimated_hours=4.0, difficulty="beginner", category="arts"),
        Topic(id="a3", name="Watercolor Painting Basics", description="Color mixing, wet-on-wet techniques, and creating texture — for complete beginners.", estimated_hours=3.0, difficulty="beginner", category="arts"),
        Topic(id="a4", name="Creative Writing: Flash Fiction", description="Craft a complete story in under 1000 words — structure, tension, and voice.", estimated_hours=2.5, difficulty="beginner", category="arts"),
    ],
    "history": [
        Topic(id="h1", name="The Roman Empire: Rise and Fall", description="From republic to empire to collapse — key figures, battles, and legacies.", estimated_hours=3.5, difficulty="beginner", category="history"),
        Topic(id="h2", name="History of the Internet", description="From ARPANET to the World Wide Web to social media — a 50-year story.", estimated_hours=2.0, difficulty="beginner", category="history"),
        Topic(id="h3", name="The Silk Road", description="Trade, culture, disease, and diplomacy across 4000 miles of ancient routes.", estimated_hours=2.5, difficulty="beginner", category="history"),
        Topic(id="h4", name="Women in Science: Untold Stories", description="Marie Curie, Rosalind Franklin, Katherine Johnson, and many overlooked pioneers.", estimated_hours=2.0, difficulty="beginner", category="history"),
    ],
}

_RESOURCES = {
    "t1": [
        Resource(id="r_t1_1", title="Python asyncio — The Complete Guide", type="article", url="https://realpython.com/async-io-python/", duration_min=45, topic_id="t1"),
        Resource(id="r_t1_2", title="asyncio Deep Dive (ArjanCodes)", type="video", url="https://youtube.com/watch?v=example1", duration_min=30, topic_id="t1"),
        Resource(id="r_t1_3", title="Hands-On: Build an Async Web Scraper", type="project", url="https://github.com/example/async-scraper", duration_min=90, topic_id="t1"),
    ],
    "t2": [
        Resource(id="r_t2_1", title="Illustrated Transformer (Jay Alammar)", type="article", url="https://jalammar.github.io/illustrated-transformer/", duration_min=40, topic_id="t2"),
        Resource(id="r_t2_2", title="How GPT Works — Visually Explained", type="video", url="https://youtube.com/watch?v=example2", duration_min=25, topic_id="t2"),
        Resource(id="r_t2_3", title="Build a Tiny LLM from Scratch (Karpathy)", type="video", url="https://youtube.com/watch?v=kCc8FmEb1nY", duration_min=120, topic_id="t2"),
    ],
    "s1": [
        Resource(id="r_s1_1", title="Quantum Computing for Computer Scientists", type="video", url="https://youtube.com/watch?v=F_Riqjdh2oM", duration_min=60, topic_id="s1"),
        Resource(id="r_s1_2", title="IBM Quantum Learning (Free)", type="course", url="https://learning.quantum.ibm.com/", duration_min=120, topic_id="s1"),
    ],
    "a1": [
        Resource(id="r_a1_1", title="Photography Composition Rules — Broken Down", type="article", url="https://digital-photography-school.com/rules-of-composition/", duration_min=20, topic_id="a1"),
        Resource(id="r_a1_2", title="10 Composition Techniques (YouTube)", type="video", url="https://youtube.com/watch?v=example3", duration_min=18, topic_id="a1"),
    ],
    "h1": [
        Resource(id="r_h1_1", title="SPQR: A History of Ancient Rome (Book Summary)", type="article", url="https://booksum.example.com/spqr", duration_min=30, topic_id="h1"),
        Resource(id="r_h1_2", title="Fall of Civilizations Podcast: Rome", type="podcast", url="https://fallofcivilizationspodcast.com/", duration_min=75, topic_id="h1"),
    ],
}

# Fallback resources for any topic not explicitly mapped
_DEFAULT_RESOURCES = [
    Resource(id="def1", title="Wikipedia Deep Dive", type="article", url="https://wikipedia.org", duration_min=30, topic_id="default"),
    Resource(id="def2", title="YouTube Educational Search", type="video", url="https://youtube.com", duration_min=20, topic_id="default"),
    Resource(id="def3", title="Khan Academy", type="course", url="https://khanacademy.org", duration_min=60, topic_id="default"),
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "learning_api"}


@app.get("/topics", response_model=list[Topic])
def get_topics(category: str = Query(default="tech", enum=["tech", "science", "arts", "history"])):
    return _TOPICS.get(category, [])


@app.get("/resources", response_model=list[Resource])
def get_resources(topic_id: str = Query(...)):
    return _RESOURCES.get(topic_id, _DEFAULT_RESOURCES)


@app.get("/schedule", response_model=StudySchedule)
def get_study_schedule(topic: str = Query(...), available_hours: float = Query(default=4.0)):
    total_minutes = int(available_hours * 60)
    blocks = []

    # Block 1: overview/theory
    overview_min = min(40, total_minutes // 3)
    blocks.append(StudyBlock(
        time="Session 1",
        activity=f"Overview & Theory: {topic}",
        duration_min=overview_min,
        notes="Read an introductory article or watch an overview video. Take notes."
    ))

    # Block 2: deep dive
    remaining = total_minutes - overview_min
    deep_min = min(60, remaining // 2)
    blocks.append(StudyBlock(
        time="Session 2",
        activity=f"Deep Dive: {topic}",
        duration_min=deep_min,
        notes="Pick one resource and study it in depth. Pause and reflect every 20 minutes."
    ))

    # Block 3: practice / project
    practice_min = max(20, remaining - deep_min)
    blocks.append(StudyBlock(
        time="Session 3",
        activity=f"Practice & Apply: {topic}",
        duration_min=practice_min,
        notes="Try a hands-on exercise, coding challenge, or summarize what you learned."
    ))

    return StudySchedule(
        topic=topic,
        total_hours=round(sum(b.duration_min for b in blocks) / 60, 1),
        blocks=blocks,
    )
