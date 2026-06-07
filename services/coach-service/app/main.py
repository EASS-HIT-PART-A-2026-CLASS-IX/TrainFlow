from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="TrainFlow Coach Service")
app.include_router(router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "TrainFlow Coach Service"}
