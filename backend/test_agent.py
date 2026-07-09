import os
import datetime
from langchain_core.messages import HumanMessage, AIMessage
from db import init_db, SessionLocal, Interaction
from agent import compiled_agent

def test_agent_flow():
    # Make sure we have a mock key or we run with SQLite
    os.environ["DATABASE_URL"] = "sqlite:///./test_crm.db"
    
    # 1. Initialize DB
    print("Initializing test database...")
    init_db()
    
    # 2. Setup initial state
    initial_form = {
        "hcp_name": "",
        "interaction_type": "",
        "date": "",
        "time": "",
        "attendees": "",
        "topics_discussed": "",
        "materials_shared": [],
        "samples_distributed": [],
        "sentiment": "",
        "outcomes": "",
        "follow_up_actions": "",
        "ai_suggestions": [],
        "is_saved": False
    }
    
    state = {
        "messages": [],
        "form_data": initial_form
    }
    
    # 3. Test Log Interaction
    user_message = "I had a meeting with Dr. Smith today at 14:30. We discussed the new oncology study. Sentiment was positive."
    print(f"\nUser: {user_message}")
    state["messages"].append(HumanMessage(content=user_message))
    
    # Verify if GROQ_API_KEY is present
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key_here":
        print("Skipping LLM execution since GROQ_API_KEY is not set.")
        print("Note: In a real run, the LangGraph agent will call log_interaction to parse and populate the form.")
        return
        
    result = compiled_agent.invoke(state)
    state = result
    
    print("\nForm Data after first prompt:")
    for k, v in state["form_data"].items():
        print(f"  {k}: {v}")
        
    # Check if AI responded
    last_msg = state["messages"][-1]
    print(f"\nAI response: {last_msg.content}")
    
    # 4. Test Edit Interaction
    edit_message = "Sorry, the name is actually Dr. John Smith, and we also shared the oncology brochure."
    print(f"\nUser: {edit_message}")
    state["messages"].append(HumanMessage(content=edit_message))
    
    result = compiled_agent.invoke(state)
    state = result
    
    print("\nForm Data after edit prompt:")
    for k, v in state["form_data"].items():
        print(f"  {k}: {v}")
        
    print(f"\nAI response: {state['messages'][-1].content}")

    # 5. Test Save Interaction
    save_message = "Okay, please save this interaction."
    print(f"\nUser: {save_message}")
    state["messages"].append(HumanMessage(content=save_message))
    
    result = compiled_agent.invoke(state)
    state = result
    
    print("\nForm Data after save prompt:")
    for k, v in state["form_data"].items():
        print(f"  {k}: {v}")
        
    print(f"\nAI response: {state['messages'][-1].content}")
    
    # 6. Query DB to confirm
    db = SessionLocal()
    try:
        interactions = db.query(Interaction).all()
        print(f"\nSaved Interactions count in DB: {len(interactions)}")
        for idx, inter in enumerate(interactions):
            print(f"[{idx+1}] HCP Name: {inter.hcp_name}, Type: {inter.interaction_type}, Date: {inter.date}, Sentiment: {inter.sentiment}")
    finally:
        db.close()

if __name__ == "__main__":
    test_agent_flow()
