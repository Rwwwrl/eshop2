import socket

from fastapi import FastAPI

app = FastAPI(title="Hello World Service")


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/host")
async def get_host():
    return {"host": socket.gethostname()}
