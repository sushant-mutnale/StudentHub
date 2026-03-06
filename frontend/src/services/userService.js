import { api } from '../api/client';

export const userService = {
  getMe: async () => {
    const { data } = await api.get('/users/me');
    return data;
  },
  updateMe: async (payload) => {
    const { data } = await api.put('/users/me', payload);
    return data;
  },
  getPublicProfile: async (userId) => {
    const { data } = await api.get(`/users/${userId}`);
    return data;
  },
  addConnection: async (userId) => {
    const { data } = await api.post(`/users/connections/${userId}`);
    return data;
  },
  removeConnection: async (userId) => {
    const { data } = await api.delete(`/users/connections/${userId}`);
    return data;
  },
  searchUsers: async (params = {}) => {
    const { data } = await api.get('/users/search', { params });
    return data;
  },
};
