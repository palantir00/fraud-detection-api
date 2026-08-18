"""Etap 0: minimalna aplikacja, żeby dało się sprawdzić, że rusztowanie działa.

Prawdziwe endpointy dochodzą w Etapie 4.
"""

from fastapi import FastAPI

app = FastAPI(title="Fraud Detection API")


@app.get("/health")
def health() -> dict[str, str]:
    """Czy serwis żyje. Nie sprawdza jeszcze bazy."""
    return {"status": "ok"}
