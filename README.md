# AI First CRM 1.0 - HCP Module

This project is a high-fidelity implementation of the **AI-First CRM HCP Module - Log Interaction Screen**, featuring a split-screen dashboard layout.
- **Left Panel (Interaction Form)**: A structured form that is read-only for manual inputs, making this an *AI-First* experience.
- **Right Panel (AI Assistant)**: A conversational chat interface driven by **LangGraph** and **Groq (gemma2-9b-it)**. All updates, form filling, edits, and saving operations are handled dynamically through chat commands using AI agent tools.

---

## Tech Stack
* **Frontend**: React UI with Redux Toolkit for state management, Google Inter font.
* **Backend**: Python 3.14 with FastAPI.
* **AI Agent**: LangGraph with LangChain-Groq using the `gemma2-9b-it` model.
* **Database**: MySQL/PostgreSQL (configured via `DATABASE_URL`, falls back to local SQLite `crm.db` if not set).

---

## Folder Structure
```
ai_first_crm/
├── frontend/             # React (Vite) Application
│   ├── src/
│   │   ├── store/        # Redux Toolkit setup
│   │   │   ├── index.js
│   │   │   └── interactionSlice.js
│   │   ├── App.jsx       # Main Dashboard view
│   │   ├── index.css     # Layout styles
│   │   └── main.jsx
│   └── package.json
├── backend/              # Python FastAPI Application
│   ├── .env              # Environment variables (API keys)
│   ├── .env.example      # Example configuration
│   ├── agent.py          # LangGraph state machine & custom tools
│   ├── db.py             # SQLAlchemy models and connection
│   ├── main.py           # FastAPI server & API endpoints
│   ├── test_agent.py     # End-to-end integration test
│   └── requirements.txt  # Python packages
├── schema.sql            # Standard PostgreSQL/MySQL Schema
└── README.md             # Project documentation
```

---

## LangGraph AI Agent & Tools

### Role of the LangGraph Agent
The LangGraph agent serves as the central intelligence of the CRM system, managing all HCP (Healthcare Professional) interactions. It acts as an AI-powered assistant that:
1. **Processes natural language input** from sales representatives and converts structured data
2. **Populates form fields automatically** using LLM-powered entity extraction
3. **Manages the conversation state** through a stateful graph architecture
4. **Executes tool calls** to perform actions on the CRM data
5. **Maintains context** across multiple interactions within a session

The agent uses a `StateGraph` with conditional routing to handle multi-step tool-calling loops, ensuring reliable execution and proper error handling.

### Tools Implemented (6 total)
The agent uses **6 custom tools** for sales-related activities:

1. **`log_interaction`** (Mandatory): Captures interaction data from natural language notes. The LLM extracts HCP name, interaction type, date, time, attendees, topics discussed, sentiment, outcomes, and follow-up actions. Uses entity extraction and summarization to populate form fields in real-time.

2. **`edit_interaction`** (Mandatory): Allows modification of logged data. Users can correct specific fields (e.g., "Sorry, the name was actually Dr. James") while preserving all other fields. Supports updating: hcp_name, interaction_type, date, time, attendees, topics_discussed, sentiment, outcomes, and follow_up_actions.

3. **`add_material`**: Adds promotional materials or brochures shared with the HCP to the form's Materials Shared section (e.g., "OncoBoost brochure", "clinical study paper").

4. **`add_sample`**: Adds drug samples distributed to the HCP to the form's Samples Distributed section (e.g., "3 packs of pill-packs").

5. **`suggest_follow_ups`**: Analyzes discussion topics and outcomes to generate 3 custom follow-up action suggestions, populating the "AI Suggested Follow-ups" container.

6. **`save_interaction_to_db`**: Validates and saves the completed interaction form along with associated materials and samples to the PostgreSQL/MySQL database.

---

## Installation & Setup

### 1. Prerequisites
- Python (>= 3.10)
- Node.js (>= 18)
- Groq API Key (from [Groq Console](https://console.groq.com/))
- PostgreSQL or MySQL server (optional; local SQLite is used by default)

### 2. Configure Environment Variables
Inside the `backend/` directory, create a `.env` file (copied from `.env.example`):
```bash
# In backend/.env
DATABASE_URL=sqlite:///./crm.db
GROQ_API_KEY=your_actual_groq_api_key_here
GROQ_MODEL=gemma2-9b-it
```

### 3. Run the Backend Server
From the project root:
```bash
# Navigate to backend
cd backend

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
python main.py
```
The backend server will run on `http://127.0.0.1:8000`.

### 4. Run the Frontend App
From the project root, open a new terminal window:
```bash
# Navigate to frontend
cd frontend

# Install Node modules
npm install

# Start Vite dev server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## How to Test and Interact

### Demo of All 5 LangGraph Tools

**1. Log Interaction Tool:**
Enter a message in the chat box:
> *"I had a meeting with Dr. Sarah Johnson today at 10:00 AM. We discussed the new oncology drug trials. The sentiment was positive and I shared the clinical brochure."*

Verify that HCP Name, Interaction Type, Date, Time, Topics, and Sentiment fields are populated automatically.

**2. Edit Interaction Tool:**
Correct a field using the chat box:
> *"Sorry, the name was actually Dr. James Williams."*

Verify that only the HCP Name field updates while other fields remain unchanged.

**3. Add Material Tool:**
Instruct the AI to add materials:
> *"I also shared the OncoBoost Phase III brochure."*

Verify the material appears in the "Materials Shared" tag container.

**4. Add Sample Tool:**
Instruct the AI to add samples:
> *"I gave him 2 sample packs of OncoBoost."*

Verify the sample appears in the "Samples Distributed" tag container.

**5. Suggest Follow-ups Tool:**
Ask the AI to suggest tasks:
> *"Suggest follow-up actions based on our discussion."*

Verify that 3 suggested follow-up items appear in the "AI Suggested Follow-ups" section.

**6. Save to Database Tool:**
Submit a final message to persist the data:
> *"Everything looks good, please save this log."*

Verify that the form displays the translucent overlay indicating the interaction has been saved to the database. Click "New Interaction" to start a new record.

---

## Project Structure Explanation

### Frontend (React + Redux)
- **`App.jsx`**: Main component with split-screen layout (Form Panel + AI Assistant Panel)
- **`store/interactionSlice.js`**: Redux slice managing form state, chat messages, loading state
- **`index.css`**: Complete styling with Inter font, responsive layout

### Backend (FastAPI + LangGraph)
- **`main.py`**: FastAPI server with `/api/chat`, `/api/interactions`, and `/api/health` endpoints
- **`agent.py`**: LangGraph StateGraph with 6 custom tools and conditional routing
- **`db.py`**: SQLAlchemy models for Interaction, MaterialShared, and SampleDistributed tables

### AI Agent Flow
1. User sends message via chat interface
2. Frontend sends request to `/api/chat` with message history and current form data
3. Backend converts messages to LangChain format and invokes the compiled agent
4. Agent processes through `agent_node` (LLM call with tool binding)
5. If tools are called, `action_node` executes them and updates form state
6. Agent loops until no more tool calls, then returns final response
7. Frontend updates UI with new messages and form data
