import { api } from '../api/client';

export const authService = {
  login: async ({ username, password, role }) => {
    const { data } = await api.post('/auth/login', { username, password, role });
    return data;
  },
  signupStudent: async (payload) => {
    const { data } = await api.post('/auth/signup/student', payload);
    return data;
  },
  signupRecruiter: async (payload) => {
    const { data } = await api.post('/auth/signup/recruiter', payload);
    return data;
  },
};
