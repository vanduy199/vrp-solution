import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.database.connection import engine, Base
import app.database.models

app = FastAPI()

allowed_origins = [
	origin.strip()
	for origin in os.getenv(
		"ALLOWED_ORIGINS",
		"http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
	).split(",")
	if origin.strip()
]

app.add_middleware(
	CORSMiddleware,
	allow_origins=allowed_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# tạo bảng database
Base.metadata.create_all(bind=engine)

# đăng ký router
app.include_router(api_router, prefix="/api")