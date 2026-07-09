from __future__ import annotations
import os
import re
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


# --- Tool Descriptions ---
TOOL_DESCRIPTIONS = """
You have access to the following tools:

1. log_interaction - Log a new HCP interaction from user notes
   Usage: {"tool": "log_interaction", "args": {"text": "user notes here"}}

2. edit_interaction - Update a single field in the form
   Usage: {"tool": "edit_interaction", "args": {"field": "field_name", "value": "new value"}}
   Valid fields: hcp_name, interaction_type, date, time, attendees, topics_discussed, sentiment, outcomes, follow_up_actions

3. add_material - Add a material shared with HCP
   Usage: {"tool": "add_material", "args": {"name": "material name"}}

4. add_sample - Add a sample distributed to HCP
   Usage: {"tool": "add_sample", "args": {"name": "sample name"}}

5. suggest_follow_ups - Generate follow-up suggestions
   Usage: {"tool": "suggest_follow_ups", "args": {}}

6. save_interaction_to_db - Save the interaction to database
   Usage: {"tool": "save_interaction_to_db", "args": {}}
"""


# ============================================================================
#  AGENT NODE (Prompt-based tool calling)
# ============================================================================

def agent_node(state: AgentState) -> dict:
    llm = get_llm()

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now   = datetime.datetime.now().strftime("%H:%M")

    # Check if last message is a ToolMessage - if so, just respond with confirmation
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg and isinstance(last_msg, ToolMessage):
        # Tool was just executed, return a friendly confirmation
        tool_result = last_msg.content
        confirmation = f"I've processed your request. {tool_result}"
        return {"messages": [AIMessage(content=confirmation)], "form_data": state["form_data"]}

    system_msg = SystemMessage(content=f"""You are an AI CRM assistant for pharmaceutical sales reps.
The rep CANNOT edit the form manually - you control it entirely through tools.

Current form state:
{json.dumps(state["form_data"], indent=2)}

Today: {today}  Now: {now}
{TOOL_DESCRIPTIONS}

RULES:
- If the user describes a new interaction, use log_interaction
- If the user corrects a field, use edit_interaction
- If the user mentions materials, use add_material
- If the user mentions samples, use add_sample
- If the user asks for suggestions, use suggest_follow_ups
- If the user says save/done, use save_interaction_to_db

To use a tool, respond with EXACTLY this JSON format (no other text):
{{"tool": "tool_name", "args": {{...}}}}

If no tool is needed, respond with a friendly message only (no JSON).
""")

    response = llm.invoke([system_msg] + state["messages"])
    content = response.content.strip()

    # Check if response contains a tool call (JSON format)
    tool_call = None
    try:
        # Try to extract JSON from response - handle nested objects
        # Find the first { and match the closing }
        start_idx = content.find('{')
        if start_idx != -1:
            depth = 0
            for i in range(start_idx, len(content)):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = content[start_idx:i+1]
                        try:
                            parsed = json.loads(json_str)
                            if "tool" in parsed:
                                tool_call = parsed
                        except:
                            pass
                        break
    except:
        pass

    if tool_call and "tool" in tool_call:
        # Create a tool call message
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})

        # Validate tool name
        valid_tools = ["log_interaction", "edit_interaction", "add_material", 
                       "add_sample", "suggest_follow_ups", "save_interaction_to_db"]
        if tool_name in valid_tools:
            # Create an AIMessage with tool_calls
            ai_msg = AIMessage(
                content="",
                tool_calls=[{
                    "id": f"call_{datetime.datetime.now().strftime('%H%M%S')}",
                    "name": tool_name,
                    "args": tool_args
                }]
            )
            return {"messages": [ai_msg], "form_data": state["form_data"]}

    # No tool call, just a regular response
    return {"messages": [response], "form_data": state["form_data"]}


# ============================================================================
#  ACTION NODE
# ============================================================================

def action_node(state: AgentState) -> dict:
    last  = state["messages"][-1]
    form  = dict(state["form_data"])
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    now   = datetime.datetime.now().strftime("%H:%M")
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

CRITICAL RULES:
1. For interaction_type, determine based on keywords:
   - "met", "meeting", "visited", "in-person" => "Meeting"
   - "called", "phone", "call", "telephonic" => "Call"
   - "emailed", "email", "sent mail" => "Email"
   - "presented", "presentation", "demo" => "Presentation"
   - "conference", "seminar", "webinar" => "Conference"

2. For time, extract the EXACT time mentioned. Examples:
   - "10:00 AM" => "10:00"
   - "2:30 PM" => "14:30"
   - "morning" => "09:00"
   - "afternoon" => "14:00"
   - "evening" => "18:00"
   - "2pm" => "14:00"
   - "10am" => "10:00"
   If no time mentioned, use current time: {now}

3. For date, use today's date if not specified: {today}

Required fields:
  hcp_name, interaction_type, date (YYYY-MM-DD), time (HH:MM 24hr format),
  attendees, topics_discussed, sentiment, outcomes, follow_up_actions

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
                valid_interaction_types = {"Meeting", "Call", "Email", "Presentation", "Conference"}
                for k, v in extracted.items():
                    if k in valid_fields and v not in (None, "", [], {}):
                        # Validate interaction_type
                        if k == "interaction_type":
                            v_normalized = v.strip().capitalize()
                            if v_normalized in valid_interaction_types:
                                form[k] = v_normalized
                            elif v.lower() in ["meeting", "met", "visited"]:
                                form[k] = "Meeting"
                            elif v.lower() in ["call", "phone", "called", "telephonic"]:
                                form[k] = "Call"
                            elif v.lower() in ["email", "emailed", "mail"]:
                                form[k] = "Email"
                            elif v.lower() in ["presentation", "presented", "demo"]:
                                form[k] = "Presentation"
                            elif v.lower() in ["conference", "seminar", "webinar"]:
                                form[k] = "Conference"
                            else:
                                form[k] = "Meeting"
                        # Validate and normalize time
                        elif k == "time":
                            time_str = str(v).strip()
                            time_str = time_str.replace(" ", "")
                            match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
                            if match:
                                hour, minute = int(match.group(1)), int(match.group(2))
                                if 0 <= hour <= 23 and 0 <= minute <= 59:
                                    form[k] = f"{hour:02d}:{minute:02d}"
                                else:
                                    form[k] = now
                            else:
                                match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$', time_str.lower())
                                if match:
                                    hour = int(match.group(1))
                                    minute = int(match.group(2)) if match.group(2) else 0
                                    ampm = match.group(3)
                                    if ampm == 'pm' and hour < 12:
                                        hour += 12
                                    elif ampm == 'am' and hour == 12:
                                        hour = 0
                                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                                        form[k] = f"{hour:02d}:{minute:02d}"
                                    else:
                                        form[k] = now
                                else:
                                    time_lower = time_str.lower()
                                    if "morning" in time_lower:
                                        form[k] = "09:00"
                                    elif "afternoon" in time_lower:
                                        form[k] = "14:00"
                                    elif "evening" in time_lower:
                                        form[k] = "18:00"
                                    elif "night" in time_lower:
                                        form[k] = "20:00"
                                    else:
                                        form[k] = now
                        else:
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
                    if field == "interaction_type":
                        valid_interaction_types = {"Meeting", "Call", "Email", "Presentation", "Conference"}
                        v_normalized = value.strip().capitalize()
                        if v_normalized in valid_interaction_types:
                            form[field] = v_normalized
                        elif value.lower() in ["meeting", "met", "visited"]:
                            form[field] = "Meeting"
                        elif value.lower() in ["call", "phone", "called", "telephonic"]:
                            form[field] = "Call"
                        elif value.lower() in ["email", "emailed", "mail"]:
                            form[field] = "Email"
                        elif value.lower() in ["presentation", "presented", "demo"]:
                            form[field] = "Presentation"
                        elif value.lower() in ["conference", "seminar", "webinar"]:
                            form[field] = "Conference"
                        else:
                            form[field] = value
                    elif field == "sentiment":
                        valid_sentiments = {"Positive", "Neutral", "Negative"}
                        v_normalized = value.strip().capitalize()
                        if v_normalized in valid_sentiments:
                            form[field] = v_normalized
                        elif value.lower() in ["positive", "good", "happy"]:
                            form[field] = "Positive"
                        elif value.lower() in ["neutral", "okay", "ok"]:
                            form[field] = "Neutral"
                        elif value.lower() in ["negative", "bad", "unhappy"]:
                            form[field] = "Negative"
                        else:
                            form[field] = value
                    else:
                        form[field] = value
                    result = f"Updated {field} -> {form[field]!r}."
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
