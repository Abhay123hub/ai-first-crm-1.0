import { createSlice } from '@reduxjs/toolkit';

const initialFormState = {
  hcp_name: '',
  interaction_type: 'Meeting', // default interaction type
  date: '',
  time: '',
  attendees: '',
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  sentiment: '', // Positive, Neutral, Negative
  outcomes: '',
  follow_up_actions: '',
  ai_suggestions: [],
  is_saved: false
};

const initialState = {
  formData: initialFormState,
  messages: [
    {
      role: 'assistant',
      content: "Hello! I'm your CRM AI Assistant. Please describe your interaction with the Healthcare Professional (HCP), and I'll populate the fields for you. You can also tell me to make edits or save the log once ready!"
    }
  ],
  loading: false,
  error: null
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    updateFormData(state, action) {
      state.formData = { ...state.formData, ...action.payload };
    },
    addMessage(state, action) {
      state.messages.push(action.payload);
    },
    setMessages(state, action) {
      state.messages = action.payload;
    },
    setLoading(state, action) {
      state.loading = action.payload;
    },
    setError(state, action) {
      state.error = action.payload;
    },
    resetForm(state) {
      state.formData = initialFormState;
      state.error = null;
    }
  }
});

export const {
  updateFormData,
  addMessage,
  setMessages,
  setLoading,
  setError,
  resetForm
} = interactionSlice.actions;

export default interactionSlice.reducer;
