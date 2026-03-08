from fastapi import FastAPI
from app.api.routes_vrp import router as vrp_router

app = FastAPI(
    title="VRP Logistics API",
    version="1.0"
)

app.include_router(vrp_router, prefix="/vrp")
@app.get("/")
def root():
    return {"message": "VRP API Running"}