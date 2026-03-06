import { mockJobs } from './mockData';

export const opportunityService = {
               // Get jobs with filters
               getJobs: async (filters = {}) => {
                              try {
                                             const { data } = await api.get('/opportunities/jobs', { params: filters });
                                             return data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock jobs for demo.');
                                             return mockJobs;
                              }
               },

               // Get hackathons
               getHackathons: async (filters = {}) => {
                              try {
                                             const { data } = await api.get('/opportunities/hackathons', { params: filters });
                                             return data;
                              } catch (error) {
                                             return [];
                              }
               },

               // Get trending content
               getContent: async (filters = {}) => {
                              try {
                                             const { data } = await api.get('/opportunities/content', { params: filters });
                                             return data;
                              } catch (error) {
                                             return [];
                              }
               },

               // Get single job details
               getJob: async (jobId) => {
                              const { data } = await api.get(`/opportunities/jobs/${jobId}`);
                              return data;
               },

               // Trigger ingestion (admin)
               triggerIngestion: async (type = 'all') => {
                              const { data } = await api.post(`/opportunities/ingest/${type}`);
                              return data;
               },

               // Demo endpoints
               getDemoJobs: async () => {
                              const { data } = await api.get('/opportunities/demo/jobs');
                              return data;
               },

               getDemoHackathons: async () => {
                              const { data } = await api.get('/opportunities/demo/hackathons');
                              return data;
               }
};
