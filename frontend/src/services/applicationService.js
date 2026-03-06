import { api } from '../api/client';

export const applicationService = {
    // Get application details
    getApplication: async (applicationId) => {
        const response = await api.get(`/applications/${applicationId}`);
        return response.data;
    },

    // Get recruiter's applications (optional filters)
    getRecruiterApplications: async (filters = {}) => {
        const params = new URLSearchParams(filters).toString();
        const response = await api.get(`/applications/recruiter?${params}`);
        return response.data;
    },

    // Get student's applications
    getStudentApplications: async () => {
        const response = await api.get(`/applications/my`);
        return response.data;
    },

    // Move application stage
    moveStage: async (applicationId, stageId, note = "") => {
        const response = await api.put(
            `/applications/${applicationId}/stage`,
            { new_stage_id: stageId, note }
        );
        return response.data;
    },

    // Add note
    addNote: async (applicationId, content, visibility = "internal") => {
        const response = await api.post(
            `/applications/${applicationId}/notes`,
            { content, visibility }
        );
        return response.data;
    },

    // Get activity timeline
    getTimeline: async (applicationId) => {
        const response = await api.get(`/applications/${applicationId}/timeline`);
        return response.data;
    }
};
