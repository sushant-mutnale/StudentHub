import { api } from '../api/client';

export const interviewService = {
  create: async (payload) => {
    const { data } = await api.post('/interviews', payload);
    return data;
  },
  listMine: async (params = {}) => {
    const { data } = await api.get('/interviews/my', { params });
    return data;
  },
  getById: async (id) => {
    const { data } = await api.get(`/interviews/${id}`);
    return data;
  },
  accept: async (id, payload) => {
    const { data } = await api.post(`/interviews/${id}/accept`, payload);
    return data;
  },
  decline: async (id, payload) => {
    const { data } = await api.post(`/interviews/${id}/decline`, payload);
    return data;
  },
  reschedule: async (id, payload) => {
    const { data } = await api.post(`/interviews/${id}/reschedule`, payload);
    return data;
  },
  cancel: async (id, payload) => {
    const { data } = await api.post(`/interviews/${id}/cancel`, payload);
    return data;
  },
  feedback: async (id, payload) => {
    const { data } = await api.post(`/interviews/${id}/feedback`, payload);
    return data;
  },
};


