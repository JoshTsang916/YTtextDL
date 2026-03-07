from fastapi import FastAPI, HTTPException, BackgroundTasks
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
async def process_video_endpoint(request: VideoRequest, background_tasks: BackgroundTasks):
    try:
        # 將耗時任務扔到背景執行！
        background_tasks.add_task(run.process_video, request.url)
        # 0 秒火速回傳給 n8n，讓工作流 1 順利結案
        return {"status": "processing", "message": "影片已加入背景處理列隊"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/qrcode")
async def qrcode_endpoint(request: VideoRequest):
    try:
        result = run.process_qr(request.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Serve static files (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
