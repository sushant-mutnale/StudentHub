import axios from 'axios';

import API_URL from '../config/api';

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
    getPipelineBoard: async (pipelineId, jobId) => {
        const response = await axios.get(`${API_URL}/pipelines/${pipelineId}/board/${jobId}`, getAuthHeader());
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
        // Backend doesn't have explicit activate endpoint, so we default to init or update
        // For now, we assume getActivePipeline handles it.
        // Only use this if we really need to Switch active pipelines.
        // const response = await axios.put(`${API_URL}/pipelines/${pipelineId}`, { active: true }, getAuthHeader());
        // return response.data;
        console.warn("setActivePipeline not fully implemented in backend");
        return { status: "success" };
    }
};
