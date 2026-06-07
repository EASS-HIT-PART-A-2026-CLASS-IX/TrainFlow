import logging
import os

from fastapi import FastAPI

from app.routes import router

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Ensure our app loggers emit at the configured level even under uvicorn.
logging.getLogger("trainflow.coach").setLevel(os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="TrainFlow Coach Service")
app.include_router(router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "TrainFlow Coach Service"}
