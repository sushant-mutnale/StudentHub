import axios from 'axios';

import { mockApplications } from './mockData';

const API_URL = 'http://127.0.0.1:8000';

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
                              try {
                                             const response = await axios.get(`${API_URL}/applications/my`, getAuthHeader());
                                             return response.data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock applications for demo.');
                                             return mockApplications;
                              }
               },

               // Move application stage
               moveStage: async (applicationId, stageId, note = "") => {
                              const response = await axios.put(
                                             `${API_URL}/applications/${applicationId}/stage`,
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
