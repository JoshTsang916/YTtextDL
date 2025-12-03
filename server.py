from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import run

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class VideoRequest(BaseModel):
    url: str

# API Endpoint
@app.post("/api/process")
async def process_video_endpoint(request: VideoRequest):
    try:
        result = run.process_video(request.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Serve static files (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
