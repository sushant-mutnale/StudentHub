import { api } from '../api/client';
import { mockThreads, mockMessages } from './mockData';

export const messageService = {
  listThreads: async () => {
    try {
      const { data } = await api.get('/threads');
      return data;
    } catch (error) {
      console.warn('Backend unavailable, using mock threads for demo.');
      return mockThreads;
    }
  },
  createThread: async (payload) => {
    const { data } = await api.post('/threads', payload);
    return data;
  },
  getThread: async (threadId, params = {}) => {
    try {
      const { data } = await api.get(`/threads/${threadId}`, { params });
      return data;
    } catch (error) {
      console.warn('Backend unavailable, using mock messages for demo.');
      return mockMessages;
    }
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


