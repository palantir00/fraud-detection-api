# Obraz bazowy: Python 3.12 w wersji "slim" (bez zbędnych narzędzi systemowych).
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: nie zaśmiecaj kontenera plikami .pyc
# PYTHONUNBUFFERED: printy i logi lecą od razu na wyjście, nie siedzą w buforze
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

# Najpierw SAM plik z zależnościami, potem instalacja, a dopiero na końcu kod.
# Dzięki temu zmiana kodu nie unieważnia warstwy z zainstalowanymi paczkami
# i kolejny build trwa sekundy zamiast minut.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Aplikacja nie działa jako root — gdyby ktoś ją przejął, ma mniej uprawnień.
RUN useradd --create-home appuser && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

# 0.0.0.0, nie 127.0.0.1: kontener musi słuchać na wszystkich interfejsach,
# inaczej ruch z hosta do niego nie dotrze.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
