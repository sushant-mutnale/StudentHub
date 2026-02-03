import { api } from '../api/client';

export const mockInterviewService = {
               // Start new interview session
               startSession: async (config) => {
                              const { data } = await api.post('/sessions/start', config);
                              return data;
               },

               // Get session details
               getSession: async (sessionId) => {
                              const { data } = await api.get(`/sessions/${sessionId}`);
                              return data;
               },

               // Get next question
               getNextQuestion: async (sessionId) => {
                              const { data } = await api.post(`/sessions/${sessionId}/next-question`);
                              return data;
               },

               // Submit answer
               submitAnswer: async (sessionId, questionId, answer, code = null) => {
                              const payload = { question_id: questionId, answer };
                              if (code) payload.code = code;
                              const { data } = await api.post(`/sessions/${sessionId}/submit-answer`, payload);
                              return data;
               },

               // Get hint
               getHint: async (sessionId, questionId) => {
                              const { data } = await api.post(`/sessions/${sessionId}/hint`, {
                                             question_id: questionId
                              });
                              return data;
               },

               // End session
               endSession: async (sessionId) => {
                              const { data } = await api.post(`/sessions/${sessionId}/end`);
                              return data;
               },

               // Get session history
               getHistory: async (limit = 10) => {
                              const { data } = await api.get('/sessions/history', { params: { limit } });
                              return data;
               },

               // Get session summary
               getSummary: async (sessionId) => {
                              const { data } = await api.get(`/sessions/${sessionId}/summary`);
                              return data;
               },

               // Multi-agent interview
               startAgentInterview: async (config) => {
                              const { data } = await api.post('/agent/interview/start', config);
                              return data;
               },

               // Continue agent interview
               continueAgentInterview: async (sessionId, userMessage) => {
                              const { data } = await api.post(`/agent/interview/${sessionId}/continue`, {
                                             user_message: userMessage
                              });
                              return data;
               },

               // Get agent interview status
               getAgentStatus: async (sessionId) => {
                              const { data } = await api.get(`/agent/interview/${sessionId}/status`);
                              return data;
               }
};
