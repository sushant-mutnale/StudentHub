import { api } from '../api/client';

export const messageService = {
  listThreads: async () => {
    const { data } = await api.get('/threads');
    return data;
  },
  createThread: async (payload) => {
    const { data } = await api.post('/threads', payload);
    return data;
  },
  getThread: async (threadId, params = {}) => {
    const { data } = await api.get(`/threads/${threadId}`, { params });
    return data;
  },
  sendMessage: async (threadId, payload) => {
    const { data } = await api.post(`/threads/${threadId}/messages`, payload);
    return data;
  },
  markThreadRead: async (threadId) => {
    const { data } = await api.put(`/threads/${threadId}/read`);
    return data;
  },
};


