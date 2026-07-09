from __future__ import annotations
import os
import json
import datetime
from typing import TypedDict, List, Optional, Annotated

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from db import save_interaction


# --- Form State Schema ---
class FormState(TypedDict):
    hcp_name: str
    interaction_type: str
    date: str
    time: str
    attendees: str
    topics_discussed: str
    materials_shared: List[str]
    samples_distributed: List[str]
    sentiment: str
    outcomes: str
    follow_up_actions: str
    ai_suggestions: List[str]
    is_saved: bool


# --- LangGraph State ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    form_data: FormState


# --- LLM Factory ---
def get_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY", "")
    model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(api_key=api_key or None, model=model, temperature=0)


# ============================================================================
#  TOOL DEFINITIONS  (kept minimal for reliable tool calling)
# ============================================================================

@tool
def log_interaction(text: str) -> str:
    """Log a new HCP interaction. Pass the user's raw notes as 'text'."""
    return f"[log_interaction] text={text!r}"


@tool
def edit_interaction(field: str, value: str) -> str:
    """Update a single field in the interaction form.
    field must be one of: hcp_name, interaction_type, date, time, attendees,
    topics_discussed, sentiment, outcomes, follow_up_actions.
    For sentiment, value must be exactly: Positive, Neutral, or Negative.
    Call this once per field that needs updating."""
    return f"[edit_interaction] {field}={value!r}"


@tool
def add_material(name: str) -> str:
    """Add a promotional material or brochure that was shared with the HCP."""
    return f"[add_material] name={name!r}"


@tool
def add_sample(name: str) -> str:
    """Add a drug sample that was distributed to the HCP."""
    return f"[add_sample] name={name!r}"


@tool
def suggest_follow_ups() -> str:
    """Generate AI-powered follow-up action suggestions based on the current interaction."""
    return "[suggest_follow_ups]"


@tool
def save_interaction_to_db() -> str:
    """Validate and save the completed interaction form to the database."""
    return "[save_interaction_to_db]"


TOOLS = [log_interaction, edit_interaction, add_material, add_sample, suggest_follow_ups, save_interaction_to_db]


# ============================================================================
#  AGENT NODE
# ============================================================================

def agent_node(state: AgentState) -> dict:
    llm = get_llm().bind_tools(TOOLS)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now   = datetime.datetime.now().strftime("%H:%M")

    system_msg = SystemMessage(content=f"""You are an AI CRM assistant for pharmaceutical sales reps. 
The rep CANNOT edit the form manually — you control it entirely through tools.

Current form state:
{json.dumps(state["form_data"], indent=2)}

Today: {today}  Now: {now}

Based on user input, choose the appropriate tool:
- If the user describes a new interaction (e.g., meeting notes, phone call notes), you MUST use `log_interaction` to process the notes. Do NOT use `edit_interaction` multiple times to populate a new form.
- If the user corrects or edits a specific field in the current form, use `edit_interaction`.
- If the user mentions materials shared, use `add_material`.
- If the user mentions samples distributed, use `add_sample`.
- If the user asks for follow-up suggestions, use `suggest_follow_ups`.
- If the user says they are done or to save/log the interaction, use `save_interaction_to_db`.

Always confirm what actions were taken in a friendly message. Do not call multiple conflicting tools at once.
""")

    response = llm.invoke([system_msg] + state["messages"])
    return {"messages": [response]}


# ============================================================================
#  ACTION NODE
# ============================================================================

def action_node(state: AgentState) -> dict:
    last  = state["messages"][-1]
    form  = dict(state["form_data"])
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    tool_messages: List[ToolMessage] = []

    for call in last.tool_calls:
        name    = call["name"]
        args    = call.get("args", {})
        call_id = call["id"]
        result  = ""

        try:
            # -- log_interaction --
            if name == "log_interaction":
                text = args.get("text", "")
                llm  = get_llm()
                prompt = f"""Extract interaction details from these sales notes and return ONLY valid JSON.
Required fields (use null if not found):
  hcp_name, interaction_type (Meeting/Call/Email/Presentation/Conference),
  date (YYYY-MM-DD, today={today}), time (HH:MM 24hr),
  attendees, topics_discussed, sentiment (Positive/Neutral/Negative),
  outcomes, follow_up_actions

Notes: {text}

Return ONLY the JSON object, no markdown, no explanation."""
                raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                # Strip markdown fences if present
                for fence in ["```json", "```"]:
                    if raw.startswith(fence):
                        raw = raw[len(fence):]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()

                extracted = json.loads(raw)
                filled = []
                valid_fields = {"hcp_name","interaction_type","date","time","attendees",
                               "topics_discussed","sentiment","outcomes","follow_up_actions"}
                for k, v in extracted.items():
                    if k in valid_fields and v not in (None, "", [], {}):
                        form[k] = v
                        filled.append(k)
                result = f"Logged interaction. Fields populated: {', '.join(filled) or 'none'}."

            # -- edit_interaction --
            elif name == "edit_interaction":
                field = args.get("field", "")
                value = args.get("value", "")
                valid = {"hcp_name","interaction_type","date","time","attendees",
                         "topics_discussed","sentiment","outcomes","follow_up_actions"}
                if field in valid:
                    form[field] = value
                    result = f"Updated {field} -> {value!r}."
                else:
                    result = f"Unknown field: {field!r}."

            # -- add_material --
            elif name == "add_material":
                name_val = args.get("name", "")
                if name_val:
                    mats = list(form.get("materials_shared", []))
                    if name_val not in mats:
                        mats.append(name_val)
                    form["materials_shared"] = mats
                    result = f"Added material: {name_val!r}."
                else:
                    result = "No material name provided."

            # -- add_sample --
            elif name == "add_sample":
                name_val = args.get("name", "")
                if name_val:
                    sams = list(form.get("samples_distributed", []))
                    if name_val not in sams:
                        sams.append(name_val)
                    form["samples_distributed"] = sams
                    result = f"Added sample: {name_val!r}."
                else:
                    result = "No sample name provided."

            # -- suggest_follow_ups --
            elif name == "suggest_follow_ups":
                llm = get_llm()
                topics   = form.get("topics_discussed", "") or "not specified"
                outcomes = form.get("outcomes", "")         or "not specified"
                prompt = f"""Give exactly 3 concise follow-up actions for a pharma sales rep.
Topics discussed: {topics}
Outcomes: {outcomes}
Return ONLY a JSON array of 3 strings."""
                raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
                for fence in ["```json", "```"]:
                    if raw.startswith(fence):
                        raw = raw[len(fence):]
                if raw.endswith("```"):
                    raw = raw[:-3]
                raw = raw.strip()
                suggestions = json.loads(raw)
                if isinstance(suggestions, list):
                    form["ai_suggestions"] = suggestions[:3]
                result = f"Generated {len(form['ai_suggestions'])} follow-up suggestions."

            # -- save_interaction_to_db --
            elif name == "save_interaction_to_db":
                ok, msg = save_interaction(form)
                if ok:
                    form["is_saved"] = True
                result = f"{msg}"

            else:
                result = f"[Unknown tool: {name}]"

        except Exception as exc:
            result = f"Error in {name}: {exc}"

        tool_messages.append(
            ToolMessage(content=result, name=name, tool_call_id=call_id)
        )

    return {"messages": tool_messages, "form_data": form}


# ============================================================================
#  ROUTING
# ============================================================================

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "action"
    return END


# ============================================================================
#  GRAPH
# ============================================================================

workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("action", action_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", should_continue, {"action": "action", END: END})
workflow.add_edge("action", "agent")

compiled_agent = workflow.compile()
