import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthHeader = () => {
               const token = localStorage.getItem('token');
               return { headers: { Authorization: `Bearer ${token}` } };
};

export const applicationService = {
               // Get application details
               getApplication: async (applicationId) => {
                              const response = await axios.get(`${API_URL}/applications/${applicationId}`, getAuthHeader());
                              return response.data;
               },

               // Get recruiter's applications (optional filters)
               getRecruiterApplications: async (filters = {}) => {
                              const params = new URLSearchParams(filters).toString();
                              const response = await axios.get(`${API_URL}/applications/recruiter?${params}`, getAuthHeader());
                              return response.data;
               },

               // Get student's applications
               getStudentApplications: async () => {
                              const response = await axios.get(`${API_URL}/applications/my`, getAuthHeader());
                              return response.data;
               },

               // Move application stage
               moveStage: async (applicationId, stageId, note = "") => {
                              const response = await axios.post(
                                             `${API_URL}/applications/${applicationId}/move`,
                                             { new_stage_id: stageId, note },
                                             getAuthHeader()
                              );
                              return response.data;
               },

               // Add note
               addNote: async (applicationId, content, visibility = "internal") => {
                              const response = await axios.post(
                                             `${API_URL}/applications/${applicationId}/notes`,
                                             { content, visibility },
                                             getAuthHeader()
                              );
                              return response.data;
               },

               // Get activity timeline
               getTimeline: async (applicationId) => {
                              const response = await axios.get(`${API_URL}/applications/${applicationId}/timeline`, getAuthHeader());
                              return response.data;
               }
};
