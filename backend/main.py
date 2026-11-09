from fastapi import FastAPI
app = FastAPI(title="Guidly")

@app.get("/health")
def health():
    return {"status": "ok"}

