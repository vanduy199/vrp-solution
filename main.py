from fastapi import FastAPI

from app.api.optimization_api import router as optimize_router
from app.api.router_api import router

from app.database.connection import engine, Base

import app.database.models

app = FastAPI()

# tạo bảng database
Base.metadata.create_all(bind=engine)

# đăng ký router
app.include_router(router, prefix="/api")
app.include_router(optimize_router, prefix="/api")