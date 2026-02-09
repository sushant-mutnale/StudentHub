import { api } from '../api/client';

export const interviewAgentService = {
               // Start a new AI interview session for a job
               startSession: async (jobId) => {
                              const { data } = await api.post('/interviews/session/start', { job_id: jobId });
                              return data;
               },

               // Send a message to the AI interviewer
               chat: async (sessionId, message) => {
                              const { data } = await api.post(`/interviews/chat/${sessionId}`, { message });
                              return data;
               }
};
