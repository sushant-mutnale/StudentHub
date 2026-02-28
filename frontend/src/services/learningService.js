import { api } from '../api/client';

export const learningService = {
    // Get my learning paths
    getMyPaths: async () => {
        const { data } = await api.get('/learning/paths/my');
        return data;
    },

    // Normalize / correct misspelled skill name via LLM
    normalizeSkill: async (skill) => {
        try {
            const { data } = await api.post('/learning/normalize-skill', { skill });
            return data.normalized || skill;
        } catch {
            return skill;
        }
    },

    // Generate learning path for a skill
    generatePath: async (skill, availableTime = '4 weeks', goalLevel = 'Job-ready') => {
        const { data } = await api.post('/learning/generate-path', {
            student_id: 'auto',
            available_time: availableTime,
            goal_level: goalLevel,
            gaps: [{
                skill: skill,
                priority: 'HIGH',
                reason: 'User requested learning path',
                current_level: 0,
                target_level: goalLevel === 'Job-ready' ? 80 : goalLevel === 'Intermediate' ? 60 : 40,
                is_required: true
            }]
        });
        if (data.learning_paths && data.learning_paths.length > 0) {
            return data.learning_paths[0];
        }
        return data;
    },

    // Get specific path details
    getPath: async (pathId) => {
        const { data } = await api.get(`/learning/path/${pathId}`);
        return data;
    },

    // Generate MCQs for a stage (5 questions)
    generateMCQ: async (pathId, stageNumber) => {
        const { data } = await api.post('/learning/mcq/generate', {
            learning_path_id: pathId,
            stage_number: stageNumber
        });
        return data;
    },

    // Submit MCQ answers — returns evaluation + auto-marks stage if passed (>=3/5)
    submitMCQ: async (pathId, stageNumber, questions, answers) => {
        const { data } = await api.post('/learning/mcq/submit', {
            learning_path_id: pathId,
            stage_number: stageNumber,
            questions,
            answers
        });
        return data;
    },

    // Trigger profile evaluation when path reaches 100% complete
    completePath: async (pathId) => {
        const { data } = await api.post(`/learning/path/${pathId}/complete`);
        return data;
    },

    // Ask AI Learning Coach
    askCoach: async ({ context, question }) => {
        const { data } = await api.post('/learning/ask', { context, question });
        return data;
    },

    // Search courses
    searchCourses: async (query, platform = null) => {
        const { data } = await api.post('/courses/search', { query, providers: platform ? [platform] : null });
        return data;
    },

    // Get gap recommendations for a target role
    getRecommendedCourses: async (skill) => {
        const { data } = await api.get('/learning/gap-recommendations', { params: { target_role: skill } });
        return data;
    },
};
