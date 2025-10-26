import logging

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

load_dotenv('.env')

import uvicorn
from fastapi import FastAPI
from api.router import router

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)
app = FastAPI()
app.include_router(router, prefix='/api')
uvicorn.run(app, host="0.0.0.0", port=8000)
