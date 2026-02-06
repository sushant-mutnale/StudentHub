import axios from 'axios';

// Get base URL from environment or default to localhost
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthHeader = () => {
               const token = localStorage.getItem('token');
               return { headers: { Authorization: `Bearer ${token}` } };
};

export const pipelineService = {
               // Get all pipelines
               getAllPipelines: async () => {
                              const response = await axios.get(`${API_URL}/pipelines`, getAuthHeader());
                              return response.data;
               },

               // Get active pipeline
               getActivePipeline: async () => {
                              const response = await axios.get(`${API_URL}/pipelines/active`, getAuthHeader());
                              return response.data;
               },

               // Get pipeline board (Kanban view)
               getPipelineBoard: async (pipelineId) => {
                              const response = await axios.get(`${API_URL}/pipelines/${pipelineId}/board`, getAuthHeader());
                              return response.data;
               },

               // Create new pipeline
               createPipeline: async (pipelineData) => {
                              const response = await axios.post(`${API_URL}/pipelines`, pipelineData, getAuthHeader());
                              return response.data;
               },

               // Update pipeline
               updatePipeline: async (pipelineId, pipelineData) => {
                              const response = await axios.put(`${API_URL}/pipelines/${pipelineId}`, pipelineData, getAuthHeader());
                              return response.data;
               },

               // Set active pipeline
               setActivePipeline: async (pipelineId) => {
                              const response = await axios.post(`${API_URL}/pipelines/${pipelineId}/activate`, {}, getAuthHeader());
                              return response.data;
               }
};
