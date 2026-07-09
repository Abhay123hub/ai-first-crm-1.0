# AI First CRM 1.0 - Video Recording Script & Outline

## Total Duration: 10-15 minutes

---

## SECTION 1: Introduction (1-2 minutes)

### What to Show:
- Your face (optional) or the project landing page
- The GitHub repository page

### Script:
"Hello, my name is [Your Name] and this is my submission for the AI-First CRM HCP Module assignment.

This project is a Log Interaction Screen for Healthcare Professional interactions, designed for pharmaceutical sales representatives. The system uses an AI-first approach where all form interactions are handled through a conversational chat interface powered by LangGraph and Groq's gemma2-9b-it model.

Let me walk you through the project structure, demo all the tools, and explain the technical implementation."

---

## SECTION 2: Project Structure Overview (2 minutes)

### What to Show:
- VS Code or your code editor with the project folder open
- Terminal showing the folder structure

### Script:
"The project is organized into two main parts:

**Frontend** (React + Redux):
- `App.jsx` - Main component with split-screen layout
- `store/interactionSlice.js` - Redux state management
- `index.css` - Styling with Google Inter font

**Backend** (Python + FastAPI):
- `main.py` - FastAPI server with API endpoints
- `agent.py` - LangGraph agent with 6 custom tools
- `db.py` - SQLAlchemy database models
- `requirements.txt` - Python dependencies

The tech stack follows the PDF requirements exactly:
- Frontend: React UI with Redux
- Backend: Python with FastAPI
- AI Agent: LangGraph
- LLM: Groq with gemma2-9b-it model
- Database: MySQL/PostgreSQL with SQLite fallback"

---

## SECTION 3: Frontend Walkthrough (2 minutes)

### What to Show:
- Start the frontend: `cd frontend && npm run dev`
- Open browser to `http://localhost:5173`
- Show the split-screen layout

### Script:
"The frontend features a split-screen dashboard layout:

**Left Panel - Interaction Form:**
- HCP Name field
- Interaction Type dropdown (Meeting, Call, Email, Presentation, Conference)
- Date and Time fields
- Attendees field
- Topics Discussed textarea
- Materials Shared section with tags
- Samples Distributed section with tags
- Sentiment radio buttons (Positive, Neutral, Negative)
- Outcomes textarea
- Follow-up Actions textarea
- AI Suggested Follow-ups section

All form fields are read-only because this is an AI-First system - the AI agent controls all form updates.

**Right Panel - AI Assistant:**
- Chat interface with message history
- Quick action chips for common tasks
- Input field with 'Log' button
- Real-time status indicator

Notice the Google Inter font is used throughout for consistency with the design requirements."

---

## SECTION 4: Backend Demo (2 minutes)

### What to Show:
- Start the backend: `cd backend && python main.py`
- Show terminal with server running on `http://127.0.0.1:8000`
- Open browser to `http://127.0.0.1:8000/docs` to show FastAPI docs

### Script:
"The backend is built with FastAPI and runs on port 8000.

Key API endpoints:
- `POST /api/chat` - Main endpoint for AI agent interactions
- `GET /api/interactions` - List saved interactions
- `GET /api/health` - Health check endpoint

The LangGraph agent is compiled and ready to process requests. The agent uses a StateGraph with conditional routing to handle multi-step tool-calling loops.

Let me show you the FastAPI documentation..." [Show /docs endpoint]

---

## SECTION 5: Demo All 6 LangGraph Tools (4-5 minutes)

### What to Show:
- The frontend chat interface
- Type messages and show the AI responses
- Show form fields being populated

### Script:

#### Tool 1: Log Interaction (1 minute)
[Type in chat]: "I had a meeting with Dr. Sarah Johnson today at 10:00 AM. We discussed the new oncology drug trials. The sentiment was positive."

[Show result]: "As you can see, the AI extracted all the details from my natural language input:
- HCP Name: Dr. Sarah Johnson
- Interaction Type: Meeting
- Date: Today's date
- Time: 10:00 AM
- Topics: New oncology drug trials
- Sentiment: Positive

This demonstrates the `log_interaction` tool which uses the LLM for entity extraction and summarization."

#### Tool 2: Edit Interaction (30 seconds)
[Type in chat]: "Sorry, the name was actually Dr. James Williams."

[Show result]: "The `edit_interaction` tool updated only the HCP Name field while preserving all other data. This allows reps to make corrections without re-entering everything."

#### Tool 3: Add Material (30 seconds)
[Type in chat]: "I also shared the OncoBoost Phase III clinical brochure."

[Show result]: "The `add_material` tool added the brochure to the Materials Shared section. You can see it appears as a tag."

#### Tool 4: Add Sample (30 seconds)
[Type in chat]: "I gave him 2 sample packs of OncoBoost."

[Show result]: "The `add_sample` tool added the samples to the Samples Distributed section."

#### Tool 5: Suggest Follow-ups (30 seconds)
[Type in chat]: "Please suggest follow-up actions for this interaction."

[Show result]: "The `suggest_follow_ups` tool analyzed the discussion topics and generated 3 relevant follow-up actions. You can see them in the AI Suggested Follow-ups section."

#### Tool 6: Save to Database (30 seconds)
[Type in chat]: "Everything looks good, please save this log."

[Show result]: "The `save_interaction_to_db` tool validated and saved all the data to the database. You can see the translucent overlay indicating successful save. The form is now locked and you can click 'New Interaction' to start fresh."

---

## SECTION 6: Code Explanation (2-3 minutes)

### What to Show:
- Open `agent.py` in VS Code
- Show the tool definitions
- Show the StateGraph structure

### Script:
"Let me explain the key technical components:

**LangGraph Agent (`agent.py`):**
The agent uses a StateGraph with two main nodes:
1. `agent_node` - Calls the LLM with tool bindings
2. `action_node` - Executes the tools and updates form state

The routing logic checks if the LLM response contains tool calls. If yes, it routes to the action node. If no more tools are needed, it ends the conversation.

**6 Custom Tools:**
```python
@tool
def log_interaction(text: str) -> str: ...
@tool
def edit_interaction(field: str, value: str) -> str: ...
@tool
def add_material(name: str) -> str: ...
@tool
def add_sample(name: str) -> str: ...
@tool
def suggest_follow_ups() -> str: ...
@tool
def save_interaction_to_db() -> str: ...
```

**Database Models (`db.py`):**
- `Interaction` - Main table with HCP details
- `MaterialShared` - Materials linked to interactions
- `SampleDistributed` - Samples linked to interactions

The system uses SQLAlchemy ORM with support for PostgreSQL, MySQL, and SQLite."

---

## SECTION 7: Summary & Closing (1 minute)

### What to Show:
- Return to the GitHub repository page
- Show the README

### Script:
"To summarize what I built:

1. **AI-First Approach**: All form interactions are handled through natural language chat, making it intuitive for field reps

2. **LangGraph Integration**: The agent uses a stateful graph with 6 custom tools for reliable tool-calling loops

3. **Complete Tech Stack**: React + Redux frontend, FastAPI backend, Groq LLM with gemma2-9b-it model

4. **Database Support**: Flexible configuration supporting PostgreSQL, MySQL, and SQLite

5. **Professional UI**: Clean split-screen layout with Google Inter font

The project is fully functional and ready for production use. Thank you for watching!"

---

## Quick Reference: What to Show in Each Section

| Section | Time | What to Show |
|---------|------|--------------|
| 1. Introduction | 1-2 min | GitHub repo, your face (optional) |
| 2. Project Structure | 2 min | VS Code, folder structure, README |
| 3. Frontend Walkthrough | 2 min | Browser with running app |
| 4. Backend Demo | 2 min | Terminal, FastAPI docs |
| 5. Tool Demo | 4-5 min | Chat interface, form updates |
| 6. Code Explanation | 2-3 min | agent.py, db.py in VS Code |
| 7. Summary | 1 min | GitHub repo, README |

---

## Recording Tips

1. **Screen Recording Software**: Use OBS Studio (free), Bandicam, or Windows Game Bar (Win+G)
2. **Resolution**: 1920x1080 (1080p) recommended
3. **Audio**: Use a good microphone, speak clearly
4. **Pacing**: Don't rush, pause between sections
5. **Practice**: Run through the demo 2-3 times before recording
6. **Have everything ready**: Start frontend and backend before recording

---

## Pre-Recording Checklist

- [ ] Frontend running on http://localhost:5173
- [ ] Backend running on http://127.0.0.1:8000
- [ ] Browser open to the app
- [ ] VS Code open with project files
- [ ] Terminal visible for showing commands
- [ ] Test all 6 tools work before recording
- [ ] Close unnecessary applications
- [ ] Silence notifications
