import { api } from '../api/client';

export const jobService = {
  createJob: async (payload) => {
    const { data } = await api.post('/jobs', payload);
    return data;
  },
  getJob: async (jobId) => {
    const { data } = await api.get(`/jobs/${jobId}`);
    return data;
  },
  getJobs: async ({ q, skills, location, limit = 20, skip = 0 } = {}) => {
    const params = { limit, skip };
    if (q) params.q = q;
    if (skills) params.skills = skills;
    if (location) params.location = location;
    const { data } = await api.get('/jobs', { params });
    return data;
  },
  getMyJobs: async () => {
    const { data } = await api.get('/jobs/my');
    return data;
  },
  deleteJob: async (jobId) => {
    await api.delete(`/jobs/${jobId}`);
  },
  getJobMatches: async (jobId) => {
    const { data } = await api.get(`/jobs/${jobId}/matches`);
    return data;
  },
  applyToJob: async (jobId, payload) => {
    const { data } = await api.post(`/jobs/${jobId}/apply`, payload);
    return data;
  },
  getJobApplications: async (jobId) => {
    const { data } = await api.get(`/jobs/${jobId}/applications`);
    return data;
  },
};