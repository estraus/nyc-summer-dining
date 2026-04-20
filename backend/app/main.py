from fastapi import FastAPI

app = FastAPI(title="NYC Dining")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
