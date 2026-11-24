import os
import re

COMMON_SKILLS = [
    "mason", "masonry", "construction", "painting", "painter", "plumbing",
    "plumber", "electrician", "electrical", "cleaning", "cleaner",
    "driving", "driver", "welding", "carpentry", "carpenter", "agriculture",
    "farming", "helper", "loading", "unloading", "tile", "tiling"
]

def tokens(value):
    return set(re.findall(r"[a-zA-Z]+", (value or "").lower()))

def score_job(worker_skills, job_text):
    worker = tokens(worker_skills)
    job = tokens(job_text)
    if not worker or not job:
        return 0
    overlap = worker & job
    # A simple transparent keyword score; Gemini can improve skill extraction,
    # but final matching remains deterministic and explainable.
    return min(100, round(100 * len(overlap) / max(1, len(worker))))

def extract_skills_with_gemini(text):
    key = os.getenv("GEMINI_API_KEY")
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=("Extract only job skills/trades from this worker description. "
                          "Return a short comma-separated list. Text: " + text)
            )
            return response.text.strip()
        except Exception:
            pass
    found = [skill for skill in COMMON_SKILLS if skill in text.lower()]
    return ", ".join(dict.fromkeys(found)) if found else text[:250]
