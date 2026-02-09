import { api } from '../api/client';
import { mockInterviews } from './mockData';

export const mockInterviewService = {
               // Start new interview session
               startSession: async (config) => {
                              try {
                                             const { data } = await api.post('/sessions/start', config);
                                             return data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock interview session for demo.');
                                             return { session_id: "mock-session-123", ...config };
                              }
               },

               // Get session details
               getSession: async (sessionId) => {
                              try {
                                             const { data } = await api.get(`/sessions/${sessionId}`);
                                             return data;
                              } catch (error) {
                                             return { id: sessionId, status: "active", type: "coding" };
                              }
               },

               // Get next question
               getNextQuestion: async (sessionId) => {
                              try {
                                             const { data } = await api.post(`/sessions/${sessionId}/next-question`);
                                             return data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock question for demo.');
                                             return {
                                                            question_id: "q1",
                                                            content: "Design a scalable URL shortener like Bit.ly.",
                                                            type: "system_design",
                                                            code_template: "class URLShortener:\n    def __init__(self):\n        pass"
                                             };
                              }
               },

               // Submit answer
               submitAnswer: async (sessionId, questionId, answer, code = null) => {
                              try {
                                             const payload = { question_id: questionId, answer };
                                             if (code) payload.code = code;
                                             const { data } = await api.post(`/sessions/${sessionId}/submit-answer`, payload);
                                             return data;
                              } catch (error) {
                                             console.warn('Backend unavailable, casting mock answer verdict.');
                                             return {
                                                            status: "success",
                                                            feedback: "Excellent solution! You verified constraints and handled edge cases well.",
                                                            score: 90
                                             };
                              }
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
