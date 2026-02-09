import { api } from '../api/client';
import { mockResumeAnalysis } from './mockData';

export const resumeService = {
               // Upload and parse resume
               uploadResume: async (file) => {
                              try {
                                             const formData = new FormData();
                                             formData.append('file', file);
                                             const { data } = await api.post('/resume/upload', formData, {
                                                            headers: { 'Content-Type': 'multipart/form-data' }
                                             });
                                             return data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock resume analysis for demo.');
                                             return mockResumeAnalysis;
                              }
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
