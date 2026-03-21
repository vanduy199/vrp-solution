from fastapi import FastAPI
from app.api.router import api_router
from app.database.connection import engine, Base
import app.database.models

app = FastAPI()

# tạo bảng database
Base.metadata.create_all(bind=engine)

# đăng ký router
app.include_router(api_router, prefix="/api")