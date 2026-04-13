from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn
from llm_agent import run_agent_loop
import os

app = FastAPI(title="WebConnect AI API")

# Setup templates
templates = Jinja2Templates(directory=".")

class SearchRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/search")
async def search(request: SearchRequest):
    if not request.query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # run_agent_loop now returns {"content": "...", "sources": [...]}
        result_data = run_agent_loop(request.query)
        return result_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
