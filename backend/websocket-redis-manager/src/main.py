from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import ws_router, redis_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(redis_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the WebSocket and Redis Manager API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)