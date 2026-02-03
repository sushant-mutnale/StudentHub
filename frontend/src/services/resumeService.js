import { api } from '../api/client';

export const resumeService = {
               // Upload and parse resume
               uploadResume: async (file) => {
                              const formData = new FormData();
                              formData.append('file', file);
                              const { data } = await api.post('/resume/upload', formData, {
                                             headers: { 'Content-Type': 'multipart/form-data' }
                              });
                              return data;
               },

               // Parse resume from URL
               parseFromUrl: async (url) => {
                              const { data } = await api.post('/resume/parse-url', { url });
                              return data;
               },

               // Get my parsed resume
               getMyResume: async () => {
                              const { data } = await api.get('/resume/my');
                              return data;
               },

               // Get parsing history
               getHistory: async () => {
                              const { data } = await api.get('/resume/history');
                              return data;
               },

               // Recalculate AI profile from resume
               recalculate: async () => {
                              const { data } = await api.post('/resume/recalculate');
                              return data;
               }
};
