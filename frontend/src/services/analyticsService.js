import { api } from '../api/client';

export const analyticsService = {
               // Get Student Analytics Overview
               getStudentOverview: async () => {
                              const { data } = await api.get('/analytics/student/overview');
                              return data;
               },

               // Get Recruiter Analytics Overview
               getRecruiterOverview: async () => {
                              const { data } = await api.get('/analytics/recruiter/overview');
                              return data;
               },

               // Get Job Funnel Metrics
               getJobFunnel: async (jobId) => {
                              const { data } = await api.get(`/analytics/recruiter/job/${jobId}/funnel`);
                              return data;
               }
};
