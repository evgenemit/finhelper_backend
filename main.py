from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth.endpoints import router as auth_router
from finances.endpoints import router as fin_router


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)
app.include_router(auth_router)
app.include_router(fin_router)
