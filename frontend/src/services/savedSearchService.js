import { api } from '../api/client';

export const savedSearchService = {
  listSavedSearches: async () => {
    const { data } = await api.get('/recruiter/saved-searches');
    return data;
  },

  createSavedSearch: async (payload) => {
    const { data } = await api.post('/recruiter/saved-searches', payload);
    return data;
  },

  updateSavedSearch: async (id, payload) => {
    const { data } = await api.patch(`/recruiter/saved-searches/${id}`, payload);
    return data;
  },

  deleteSavedSearch: async (id) => {
    await api.delete(`/recruiter/saved-searches/${id}`);
    return true;
  },

  getSavedSearchCandidates: async (id, limit = 20) => {
    const { data } = await api.get(`/recruiter/saved-searches/${id}/candidates`, {
      params: { limit },
    });
    return data;
  },
};
