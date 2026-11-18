
"""
Research Studio - FastAPI Backend
Connects the React frontend to the existing Python research pipeline.
"""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

# Import your existing research pipeline.
from pipeline import run_research_pipeline


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Research Studio API",
    description="React + Python AI Research Application",
    version="1.0.0"
)


# --------------------------------------------------
# CORS CONFIGURATION
# Allows React to communicate with Python.
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class ResearchRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500
    )


# --------------------------------------------------
# CONVERT RESULTS TO JSON-SAFE VALUES
# --------------------------------------------------

def make_json_safe(value: Any):

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            make_json_safe(item)
            for item in value
        ]

    if value is None or isinstance(
        value, (str, int, float, bool)
    ):
        return value

    return str(value)


# --------------------------------------------------
# HOME ROUTE
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Research Studio Backend Running",
        "status": "success",
        "docs": "/docs"
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health_check():

    return {
        "status": "ok",
        "message": "Backend connected successfully"
    }


# --------------------------------------------------
# START RESEARCH
# --------------------------------------------------

@app.post("/api/research")
async def start_research(request: ResearchRequest):

    topic = request.topic.strip()

    if not topic:
        raise HTTPException(
            status_code=400,
            detail="Please enter a research topic."
        )

    try:

        print("\n" + "=" * 60)
        print("NEW RESEARCH REQUEST")
        print("Topic:", topic)
        print("=" * 60)

        # Call your existing Python pipeline.
        # Do not duplicate the research logic here.

        result = await run_in_threadpool(
            run_research_pipeline,
            topic
        )

        print("\nResearch completed successfully.")

        return {
            "success": True,
            "topic": topic,
            "result": make_json_safe(result)
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        print("[RESEARCH ERROR]", str(error))

        raise HTTPException(
            status_code=500,
            detail=f"Research failed: {str(error)}"
        )


# --------------------------------------------------
# DOWNLOAD REPORT
# --------------------------------------------------

@app.get("/api/download/{file_format}")
def download_report(
    file_format: str,
    path: str
):

    if file_format not in ["pdf", "markdown"]:
        raise HTTPException(
            status_code=400,
            detail="Supported formats: pdf and markdown"
        )

    file_path = Path(path).expanduser().resolve()

    backend_folder = Path(__file__).resolve().parent

    # Prevent downloading files outside backend.
    try:
        file_path.relative_to(backend_folder)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Invalid file location."
        )

    expected_extension = (
        ".pdf" if file_format == "pdf" else ".md"
    )

    if (
        not file_path.is_file()
        or file_path.suffix.lower() != expected_extension
    ):
        raise HTTPException(
            status_code=404,
            detail="Report file not found."
        )

    media_type = (
        "application/pdf"
        if file_format == "pdf"
        else "text/markdown"
    )

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=media_type
    )
