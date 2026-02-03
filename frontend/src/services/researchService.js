import { api } from '../api/client';

export const researchService = {
               // Quick company research
               researchCompany: async (companyName) => {
                              const { data } = await api.get('/research/company', {
                                             params: { company_name: companyName }
                              });
                              return data;
               },

               // Deep research with multiple aspects
               deepResearch: async (companyName, aspects = ['culture', 'interview', 'tech']) => {
                              const { data } = await api.post('/research/deep', {
                                             company_name: companyName,
                                             aspects
                              });
                              return data;
               },

               // Get interview questions for company
               getInterviewQuestions: async (companyName, role = null) => {
                              const params = { company_name: companyName };
                              if (role) params.role = role;
                              const { data } = await api.get('/research/interview-questions', { params });
                              return data;
               },

               // Search topics
               searchTopics: async (query) => {
                              const { data } = await api.get('/research/search', { params: { q: query } });
                              return data;
               },

               // Get cached research
               getCached: async (companyName) => {
                              const { data } = await api.get('/research/cached', {
                                             params: { company_name: companyName }
                              });
                              return data;
               }
};
