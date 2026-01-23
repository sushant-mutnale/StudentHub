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
};
