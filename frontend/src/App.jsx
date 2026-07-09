import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  updateFormData,
  addMessage,
  setMessages,
  setLoading,
  setError,
  resetForm,
} from './store/interactionSlice';
import { Mic, Search, Plus, CheckCircle, Sparkles, Bot } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const dispatch = useDispatch();
  const { formData, messages, loading, error } = useSelector((s) => s.interaction);
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  /* --- send --- */
  const sendMessage = async (text) => {
    text = text.trim();
    if (!text || loading || formData.is_saved) return;

    const userMsg = { role: 'user', content: text };
    dispatch(addMessage(userMsg));
    setInput('');
    dispatch(setLoading(true));
    dispatch(setError(null));

    const history = [...messages, userMsg];

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: history, form_data: formData }),
      });

      if (!res.ok) throw new Error(`Server error ${res.status}: ${await res.text()}`);
      const data = await res.json();

      // Backend returns only the new messages for this turn (not the full history)
      // Filter to only show user/assistant messages
      const newMessages = (data.messages || []).filter(
        (m) => m.role === 'user' || m.role === 'assistant'
      );
      newMessages.forEach((m) => dispatch(addMessage(m)));
      dispatch(updateFormData(data.form_data));
    } catch (err) {
      dispatch(
        addMessage({
          role: 'assistant',
          content: `Error: ${err.message}. Please ensure the backend server is running at ${API_BASE}.`,
          isError: true,
        })
      );
    } finally {
      dispatch(setLoading(false));
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleNewLog = () => {
    dispatch(resetForm());
    dispatch(
      setMessages([
        {
          role: 'assistant',
          content:
            "Hello! I'm your AI Assistant. Describe the HCP interaction in the chat and I'll populate the form automatically. Try: \"Today I met with Dr. Smith and discussed Product X efficacy. Sentiment was positive, shared brochures.\"",
        },
      ])
    );
  };

  const CHIPS = [
    { label: 'Log New Interaction', text: 'Today I met with Dr. Sarah Johnson and discussed Product X efficacy. The sentiment was positive and I shared the clinical brochure.' },
    { label: 'Edit HCP Name', text: 'Sorry, the name was actually Dr. James Williams.' },
    { label: 'Add Materials & Samples', text: 'I shared the OncoBoost Phase III brochure and gave 2 sample packs.' },
    { label: 'Suggest Follow-Ups', text: 'Please suggest follow-up actions for this interaction.' },
    { label: 'Save Interaction', text: 'Please save this interaction to the database.' },
  ];

  return (
    <div className="app-shell">
      {/* -- NAVBAR -- */}
      <nav className="top-navbar">
        <div className="navbar-brand">
          <div className="brand-icon">
            <Bot size={16} />
          </div>
          <span className="brand-name">AI First CRM 1.0</span>
          <span className="brand-badge">HCP Module</span>
        </div>
        <div className="navbar-right">
          {formData.is_saved && (
            <button className="btn-new-log" onClick={handleNewLog}>
              <Plus size={14} />
              New Interaction
            </button>
          )}
        </div>
      </nav>

      {/* -- MAIN GRID -- */}
      <div className="main-content">
        {/* ===== LEFT -- FORM PANEL ===== */}
        <section className="form-panel">
          {formData.is_saved && (
            <div className="saved-overlay">
              <div className="saved-badge">
                <CheckCircle size={22} />
                Interaction Saved Successfully!
              </div>
            </div>
          )}

          <h1 className="form-panel-title">Log HCP Interaction</h1>

          {/* -- Section: Interaction Details -- */}
          <div>
            <p className="form-section-label">Interaction Details</p>

            <div className="form-row">
              {/* HCP Name */}
              <div className="form-group">
                <label className="field-label">HCP Name</label>
                <input
                  className="field-input"
                  type="text"
                  placeholder="Search or select HCP..."
                  value={formData.hcp_name || ''}
                  readOnly
                />
              </div>

              {/* Interaction Type */}
              <div className="form-group">
                <label className="field-label">Interaction Type</label>
                <select
                  className="field-select"
                  value={formData.interaction_type || 'Meeting'}
                  disabled
                >
                  <option value="Meeting">Meeting</option>
                  <option value="Call">Call</option>
                  <option value="Email">Email</option>
                  <option value="Presentation">Presentation</option>
                  <option value="Conference">Conference</option>
                </select>
                {formData.interaction_type && (
                  <span className="field-hint">AI-determined type</span>
                )}
              </div>
            </div>

            <div className="form-row" style={{ marginTop: 12 }}>
              {/* Date */}
              <div className="form-group">
                <label className="field-label">Date</label>
                <input
                  className="field-input"
                  type="date"
                  value={formData.date || ''}
                  readOnly
                />
              </div>

              {/* Time */}
              <div className="form-group">
                <label className="field-label">Time</label>
                <input
                  className="field-input"
                  type="time"
                  value={formData.time || ''}
                  readOnly
                />
              </div>
            </div>

            {/* Attendees */}
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="field-label">Attendees</label>
              <input
                className="field-input"
                type="text"
                placeholder="Enter names or search..."
                value={formData.attendees || ''}
                readOnly
              />
            </div>

            {/* Topics Discussed */}
            <div className="form-group" style={{ marginTop: 12 }}>
              <label className="field-label">Topics Discussed</label>
              <textarea
                className="field-textarea"
                placeholder="Enter key discussion points..."
                value={formData.topics_discussed || ''}
                readOnly
                rows={3}
              />
            </div>

            {/* Summarize from Voice Note */}
            <button className="voice-note-btn" type="button" disabled>
              <Mic size={13} />
              Summarize from Voice Note (Requires Consent)
            </button>
          </div>

          {/* -- Section: Materials / Samples -- */}
          <div className="mat-sam-section">
            <p className="mat-sam-title">Materials Shared / Samples Distributed</p>

            {/* Materials Shared */}
            <div>
              <p className="mat-sub-label">Materials Shared</p>
              <div className="mat-row">
                <div className={`mat-items ${formData.materials_shared?.length ? 'has-items' : ''}`}>
                  {formData.materials_shared?.length
                    ? formData.materials_shared.map((m, i) => (
                        <span key={i} className="mat-tag">{m}</span>
                      ))
                    : 'No materials added.'}
                </div>
                <button className="btn-search-add" type="button" disabled>
                  <Search size={11} />
                  Search/Add
                </button>
              </div>
            </div>

            {/* Samples Distributed */}
            <div>
              <p className="mat-sub-label">Samples Distributed</p>
              <div className="mat-row">
                <div className={`mat-items ${formData.samples_distributed?.length ? 'has-items' : ''}`}>
                  {formData.samples_distributed?.length
                    ? formData.samples_distributed.map((s, i) => (
                        <span key={i} className="mat-tag">{s}</span>
                      ))
                    : 'No samples added.'}
                </div>
                <button className="btn-add-sample" type="button" disabled>
                  <Plus size={11} />
                  Add Sample
                </button>
              </div>
            </div>
          </div>

          {/* -- Section: Sentiment -- */}
          <div className="sentiment-section">
            <label className="field-label">Observed/Inferred HCP Sentiment</label>
            <div className="sentiment-row">
              {['Positive', 'Neutral', 'Negative'].map((s) => (
                <label
                  key={s}
                  className={`sentiment-option ${s.toLowerCase()}`}
                >
                  <input
                    className="sentiment-radio"
                    type="radio"
                    name="sentiment"
                    value={s}
                    checked={formData.sentiment === s}
                    onChange={() => {}}
                    disabled
                  />
                  {s}
                </label>
              ))}
            </div>
          </div>

          {/* -- Section: Outcomes -- */}
          <div className="form-group">
            <label className="field-label">Outcomes</label>
            <textarea
              className="field-textarea"
              placeholder="Key outcomes or agreements..."
              value={formData.outcomes || ''}
              readOnly
              rows={2}
            />
          </div>

          {/* -- Section: Follow-up Actions -- */}
          <div className="form-group">
            <label className="field-label">Follow-up Actions</label>
            <textarea
              className="field-textarea"
              placeholder="Enter next steps or follow-up actions..."
              value={formData.follow_up_actions || ''}
              readOnly
              rows={2}
            />
          </div>

          {/* -- AI Suggestions -- */}
          {formData.ai_suggestions?.length > 0 && (
            <div className="ai-suggestions-box">
              <div className="ai-suggestions-title">
                <Sparkles size={13} />
                AI Suggested Follow-ups
              </div>
              {formData.ai_suggestions.map((s, i) => (
                <div key={i} className="ai-suggestion-item">
                  <CheckCircle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{s}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ===== RIGHT -- AI ASSISTANT PANEL ===== */}
        <section className="ai-panel">
          {/* Header */}
          <div className="ai-panel-header">
            <div className="ai-header-left">
              <div className="ai-avatar">
                <Bot size={16} color="white" />
              </div>
              <div>
                <div className="ai-panel-title">AI Assistant</div>
                <div className="ai-panel-subtitle">Log interaction details here via chat</div>
              </div>
            </div>
            <div className="ai-status">
              <div className={`status-dot ${loading ? 'thinking' : ''}`} />
              <span>{loading ? 'Thinking...' : 'Ready'}</span>
            </div>
          </div>

          {/* Messages */}
          <div className="chat-messages">
            {messages.map((msg, idx) => {
              if (msg.role !== 'user' && msg.role !== 'assistant') return null;
              const isFirst = idx === 0 && msg.role === 'assistant';
              return (
                <div key={idx} className={`msg-row ${msg.role}`}>
                  <div
                    className={`chat-bubble ${
                      isFirst ? 'welcome' : msg.isError ? 'error' : ''
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="msg-row assistant">
                <div className="typing-bubble">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input area */}
          <div className="chat-input-section">
            {/* Quick-action chips */}
            {!formData.is_saved && (
              <div className="prompt-chips">
                {CHIPS.map((chip, i) => (
                  <button
                    key={i}
                    className="chip"
                    disabled={loading}
                    onClick={() => sendMessage(chip.text)}
                  >
                    {chip.label}
                  </button>
                ))}
              </div>
            )}

            <div className="chat-input-row">
              <textarea
                className="chat-input-box"
                rows={1}
                placeholder={
                  formData.is_saved
                    ? 'Interaction saved. Click "New Interaction" to start again.'
                    : 'Describe Interaction...'
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading || formData.is_saved}
              />
              <button
                className="btn-log"
                onClick={() => sendMessage(input)}
                disabled={loading || !input.trim() || formData.is_saved}
                title="Log"
              >
                Log
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
