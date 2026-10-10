"""App mínima para tests/build-fixtures.sh: andamio la arranca con uvicorn en $PORT."""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()


@app.get("/", response_class=PlainTextResponse)
def root() -> str:
    return "andamio-ok\n"
