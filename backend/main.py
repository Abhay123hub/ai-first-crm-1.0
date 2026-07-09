from __future__ import annotations
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from db import init_db, get_db, Interaction
from agent import compiled_agent

# Thread pool for running the synchronous LangGraph agent without blocking the async event loop
_executor = ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI-First CRM HCP Module", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---

class ChatMessage(BaseModel):
    role: str           # user | assistant | system | tool
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    isError: Optional[bool] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    form_data: Dict[str, Any]


class ChatResponse(BaseModel):
    messages: List[ChatMessage]
    form_data: Dict[str, Any]


# --- Helper ---

def lc_to_chat(msg) -> Optional[ChatMessage]:
    """Convert a LangChain message -> ChatMessage, skipping tool/system messages."""
    if isinstance(msg, HumanMessage):
        return ChatMessage(role="user", content=str(msg.content))
    if isinstance(msg, AIMessage):
        content = str(msg.content).strip()
        if not content:
            return None
        return ChatMessage(role="assistant", content=content)
    return None  # ToolMessage, SystemMessage -> skip


def run_agent_sync(lc_msgs: list, form_data: dict) -> dict:
    """
    Runs the compiled LangGraph agent synchronously.
    This is called in a thread pool executor so it doesn't block the async event loop.
    """
    return compiled_agent.invoke(
        {"messages": lc_msgs, "form_data": form_data},
        config={"recursion_limit": 10},   # prevent infinite tool-call loops
    )


# --- /api/chat ---

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # Convert frontend messages -> LangChain messages (user + assistant only)
    lc_msgs = []
    for m in req.messages:
        if m.role == "user":
            lc_msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_msgs.append(AIMessage(content=m.content))

    loop = asyncio.get_event_loop()
    try:
        # Run the blocking LangGraph agent in a thread pool so FastAPI stays responsive
        result = await loop.run_in_executor(
            _executor,
            run_agent_sync,
            lc_msgs,
            req.form_data,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Convert back -> ChatMessage (user/assistant only)
    out_msgs: List[ChatMessage] = []
    for m in result["messages"]:
        cm = lc_to_chat(m)
        if cm:
            out_msgs.append(cm)

    if not out_msgs:
        out_msgs.append(
            ChatMessage(
                role="assistant",
                content="Done! The form has been updated. Let me know if you'd like any changes.",
            )
        )

    # Debug: print form_data
    print(f"DEBUG: form_data being returned: {result.get('form_data', {})}")

    return ChatResponse(messages=out_msgs, form_data=result["form_data"])


# --- /api/interactions ---

@app.get("/api/interactions")
def list_interactions(db: Session = Depends(get_db)):
    try:
        rows = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
        return [
            {
                "id": r.id,
                "hcp_name": r.hcp_name,
                "interaction_type": r.interaction_type,
                "date": r.date.strftime("%Y-%m-%d") if r.date else None,
                "time": r.time.strftime("%H:%M") if r.time else None,
                "attendees": r.attendees,
                "topics_discussed": r.topics_discussed,
                "sentiment": r.sentiment,
                "outcomes": r.outcomes,
                "follow_up_actions": r.follow_up_actions,
                "materials_shared": [m.material_name for m in r.materials],
                "samples_distributed": [s.sample_name for s in r.samples],
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- /api/health ---

@app.get("/api/health")
def health():
    api_key = os.getenv("GROQ_API_KEY", "")
    groq_ok = bool(api_key and api_key != "your_groq_api_key_here")
    return {
        "status": "ok",
        "groq_configured": groq_ok,
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        timeout_keep_alive=120,   # keep connections alive for up to 2 min
    )
