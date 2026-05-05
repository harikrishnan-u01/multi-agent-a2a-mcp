"""
Mock Wellness REST API — Layer 1 service on port 8001.
Returns realistic static data; no database needed.
Agents never call this directly — they always go through the MCP server.
"""
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Wellness API", version="1.0")


class Activity(BaseModel):
    id: str
    name: str
    duration_min: int
    intensity: str
    description: str
    time_of_day: str


class Meal(BaseModel):
    id: str
    name: str
    calories: int
    prep_min: int
    ingredients: list[str]
    tags: list[str]


class SleepTip(BaseModel):
    id: str
    tip: str
    category: str


_ACTIVITIES = {
    "relaxation": [
        Activity(id="r1", name="Guided Meditation", duration_min=20, intensity="low",
                 description="Follow a 20-minute mindfulness meditation to calm the nervous system.",
                 time_of_day="morning"),
        Activity(id="r2", name="Restorative Yoga", duration_min=45, intensity="low",
                 description="Gentle yoga poses held for 3-5 minutes each to release tension.",
                 time_of_day="morning"),
        Activity(id="r3", name="Nature Walk", duration_min=60, intensity="low",
                 description="A slow, mindful walk in a park or nature trail — no headphones.",
                 time_of_day="afternoon"),
        Activity(id="r4", name="Warm Bath with Epsom Salts", duration_min=30, intensity="low",
                 description="Soaking in Epsom salts reduces muscle soreness and promotes sleep.",
                 time_of_day="evening"),
        Activity(id="r5", name="Journaling", duration_min=20, intensity="low",
                 description="Free-write thoughts, gratitude, and intentions for the coming week.",
                 time_of_day="evening"),
    ],
    "fitness": [
        Activity(id="f1", name="Morning Jog", duration_min=30, intensity="medium",
                 description="Easy-paced 5K run to boost endorphins without over-exerting.",
                 time_of_day="morning"),
        Activity(id="f2", name="Bodyweight Circuit", duration_min=40, intensity="high",
                 description="Push-ups, squats, lunges, and planks — 3 rounds, no equipment needed.",
                 time_of_day="morning"),
        Activity(id="f3", name="Swimming", duration_min=45, intensity="medium",
                 description="Low-impact full-body workout; great for joints and cardiovascular health.",
                 time_of_day="afternoon"),
        Activity(id="f4", name="Cycling", duration_min=60, intensity="medium",
                 description="Outdoor bike ride on a scenic route — combines fitness with sightseeing.",
                 time_of_day="afternoon"),
        Activity(id="f5", name="Yoga Flow (Vinyasa)", duration_min=50, intensity="medium",
                 description="Dynamic yoga sequence linking breath and movement for strength + flexibility.",
                 time_of_day="morning"),
    ],
    "mindfulness": [
        Activity(id="m1", name="Breathwork (Box Breathing)", duration_min=15, intensity="low",
                 description="4-4-4-4 breathing pattern to activate the parasympathetic nervous system.",
                 time_of_day="morning"),
        Activity(id="m2", name="Body Scan Meditation", duration_min=25, intensity="low",
                 description="Systematically relax each body part from toes to crown.",
                 time_of_day="evening"),
        Activity(id="m3", name="Digital Detox Hour", duration_min=60, intensity="low",
                 description="One hour completely offline — read, draw, cook, or sit quietly.",
                 time_of_day="afternoon"),
        Activity(id="m4", name="Gratitude Practice", duration_min=10, intensity="low",
                 description="Write 5 specific things you're grateful for and why they matter.",
                 time_of_day="morning"),
        Activity(id="m5", name="Sound Bath / Binaural Beats", duration_min=30, intensity="low",
                 description="Listen to theta-wave audio to induce deep relaxation and mental clarity.",
                 time_of_day="evening"),
    ],
}

_MEALS = {
    "healthy": [
        Meal(id="h1", name="Overnight Oats with Berries", calories=380, prep_min=5,
             ingredients=["rolled oats", "almond milk", "chia seeds", "blueberries", "honey"],
             tags=["breakfast", "high-fiber", "no-cook"]),
        Meal(id="h2", name="Grilled Salmon & Quinoa Bowl", calories=520, prep_min=25,
             ingredients=["salmon fillet", "quinoa", "spinach", "cherry tomatoes", "lemon", "olive oil"],
             tags=["lunch", "high-protein", "omega-3"]),
        Meal(id="h3", name="Avocado Toast with Poached Egg", calories=420, prep_min=15,
             ingredients=["sourdough bread", "avocado", "egg", "chili flakes", "lemon juice"],
             tags=["breakfast", "healthy-fats"]),
        Meal(id="h4", name="Buddha Bowl", calories=490, prep_min=20,
             ingredients=["brown rice", "roasted chickpeas", "kale", "cucumber", "tahini", "turmeric"],
             tags=["lunch", "plant-based", "anti-inflammatory"]),
        Meal(id="h5", name="Veggie Stir-Fry with Tofu", calories=410, prep_min=20,
             ingredients=["firm tofu", "broccoli", "bell peppers", "snap peas", "ginger", "tamari"],
             tags=["dinner", "plant-based", "quick"]),
    ],
    "comfort": [
        Meal(id="c1", name="Homemade Tomato Soup & Grilled Cheese", calories=650, prep_min=30,
             ingredients=["canned tomatoes", "cream", "basil", "sourdough", "cheddar", "butter"],
             tags=["lunch", "warm", "comfort"]),
        Meal(id="c2", name="Chicken & Sweet Potato Curry", calories=580, prep_min=40,
             ingredients=["chicken thighs", "sweet potato", "coconut milk", "curry paste", "rice"],
             tags=["dinner", "warm", "hearty"]),
        Meal(id="c3", name="Banana Pancakes", calories=480, prep_min=20,
             ingredients=["bananas", "eggs", "oat flour", "vanilla", "maple syrup"],
             tags=["breakfast", "sweet", "comfort"]),
    ],
    "quick": [
        Meal(id="q1", name="Greek Yogurt Parfait", calories=320, prep_min=5,
             ingredients=["Greek yogurt", "granola", "strawberries", "honey"],
             tags=["breakfast", "no-cook", "5-minutes"]),
        Meal(id="q2", name="Tuna & Avocado Rice Cakes", calories=290, prep_min=5,
             ingredients=["tuna", "avocado", "rice cakes", "lemon", "salt"],
             tags=["snack", "high-protein", "5-minutes"]),
        Meal(id="q3", name="Smoothie Bowl", calories=360, prep_min=10,
             ingredients=["frozen mango", "banana", "coconut milk", "granola", "kiwi"],
             tags=["breakfast", "refreshing", "10-minutes"]),
    ],
}

_SLEEP_TIPS = [
    SleepTip(id="s1", tip="Keep your bedroom temperature between 60-67°F (15-19°C) for optimal sleep.", category="environment"),
    SleepTip(id="s2", tip="Avoid screens 1 hour before bed — blue light suppresses melatonin production.", category="habits"),
    SleepTip(id="s3", tip="Go to bed and wake up at the same time every day, even on weekends.", category="schedule"),
    SleepTip(id="s4", tip="A 10-minute wind-down routine (light stretching or reading) signals your body it's time to sleep.", category="habits"),
    SleepTip(id="s5", tip="Avoid caffeine after 2 PM — its half-life is ~6 hours.", category="nutrition"),
    SleepTip(id="s6", tip="Magnesium-rich foods (dark chocolate, almonds, spinach) support muscle relaxation and deep sleep.", category="nutrition"),
    SleepTip(id="s7", tip="Use blackout curtains or a sleep mask to block light that disrupts circadian rhythm.", category="environment"),
]


@app.get("/health")
def health():
    return {"status": "ok", "service": "wellness_api"}


@app.get("/activities", response_model=list[Activity])
def get_activities(type: str = Query(default="relaxation", enum=["relaxation", "fitness", "mindfulness"])):
    return _ACTIVITIES.get(type, [])


@app.get("/meals", response_model=list[Meal])
def get_meals(goal: str = Query(default="healthy", enum=["healthy", "comfort", "quick"])):
    return _MEALS.get(goal, [])


@app.get("/sleep-tips", response_model=list[SleepTip])
def get_sleep_tips():
    return _SLEEP_TIPS
