from fastapi import FastAPI

app = FastAPI(title="Fuel Tracker API")


@app.get("/")
def read_root():
    return {"message": "Fuel Tracker API"}


@app.get("/health")
def health():
    return {"status": "ok"}
