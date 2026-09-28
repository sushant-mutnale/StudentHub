import { api } from '../api/client';

export const nextActionService = {
  getNextBestAction: async () => {
    const { data } = await api.get('/next-action');
    return data;
  },
};
