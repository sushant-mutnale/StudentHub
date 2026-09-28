import { api } from '../api/client';

export const calendarService = {
  getDeadlines: async (limit = 100) => {
    const { data } = await api.get('/calendar/deadlines', { params: { limit } });
    return data;
  },
  getICalDownloadUrl: () => {
    const base = import.meta.env.VITE_API_URL || '';
    return `${base}/calendar/deadlines/ical`;
  },
};
