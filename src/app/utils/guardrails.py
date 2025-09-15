from typing import List, Tuple
from langchain.schema import Document

# Critical areas where hallucination is dangerous
CRITICAL_KEYWORDS = {
    "deadline": ["deadline", "due date", "closes", "cutoff", "round"],
    "tuition": ["fee", "tuition", "cost", "price"],
    "requirement": ["requirement", "criteria", "prerequisite", "gpa"]
}


def classify_guardrail(question: str, docs: List[Document]) -> Tuple[str, str]:
    """
    Decide if the bot should abstain, warn, or allow a normal answer.

    Returns:
        ("abstain" | "warn" | "pass", message)
    """
    q = question.lower()
    combined = " ".join([d.page_content.lower() for d in docs])

    # For each critical category, check if query mentions it
    for category, synonyms in CRITICAL_KEYWORDS.items():
        if any(kw in q for kw in synonyms):
            # If *none* of the synonyms appear in the retrieved docs → abstain
            if not any(kw in combined for kw in synonyms):
                return (
                    "abstain",
                    "I can’t verify that from official Applied Data Science pages. "
                    "Please contact admissions at adsadmissions@uchicago.edu."
                )
            else:
                # Docs exist but may not be explicit → soft warning
                return (
                    "warn",
                    f"⚠️ This answer is based on retrieved information about {category}, "
                    "but please confirm with admissions for the most up-to-date details."
                )

    # No critical keywords found → normal pass-through
    return ("pass", "")

