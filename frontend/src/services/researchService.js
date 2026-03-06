import { api } from '../api/client';

export const researchService = {
    // Deep research — calls the correct /research/company endpoint
    deepResearch: async (companyName, aspects = ['interview', 'culture', 'tech_stack', 'salary']) => {
        // Map frontend aspect names to backend category names
        const categoryMap = { tech: 'tech_stack', culture: 'culture', interview: 'interview', salary: 'salary', news: 'news' };
        const categories = aspects.map(a => categoryMap[a] || a);

        const { data } = await api.post('/research/company', {
            company: companyName,
            categories,
            max_results: 5
        });

        // Backend returns { status, research: { company, categories:{interview:[],culture:[],...}, summary, key_insights } }
        // Adapt to shape that CompanyResearch.jsx expects
        const raw = data?.research || data || {};
        return adaptResearchShape(companyName, raw);
    },

    // Get interview questions for company
    getInterviewQuestions: async (companyName, role = null) => {
        const { data } = await api.post('/research/interview-questions', {
            company: companyName,
            role: role || 'Software Engineer'
        });
        return data;
    },

    // Get company trends
    getCompanyTrends: async (companyName) => {
        const { data } = await api.post('/research/trends', {
            company: companyName
        });
        return data;
    },

    // Clear research cache
    clearCache: async () => {
        const { data } = await api.post('/research/cache/clear');
        return data;
    }
};

/**
 * Adapts the backend nested {categories: {interview:[...], culture:[...]}} shape
 * into the flat shape that CompanyResearch.jsx renders.
 */
function adaptResearchShape(companyName, raw) {
    const cats = raw.categories || {};

    const joinSnippets = (items = []) =>
        items
            .slice(0, 4)
            .map(r => r.snippet || r.content || '')
            .filter(Boolean)
            .join('\n\n');

    const toLinks = (items = []) =>
        items
            .filter(r => r.url && r.title)
            .map(r => ({ title: r.title, url: r.url, source: r.source || '' }));

    // Extract interview tips from key_insights + interview snippets
    const interviewTips = [
        ...(raw.key_insights || []),
        ...(cats.interview || [])
            .slice(0, 2)
            .map(r => r.snippet || '')
            .filter(Boolean)
    ].slice(0, 6);

    // Tech stack — try to parse tech names from snippets
    const techSnippets = cats.tech_stack || [];
    const techStack = techSnippets.length
        ? techSnippets.flatMap(r =>
            (r.snippet || r.content || '').match(/\b(React|Python|Go|Java|Kotlin|Swift|Node\.js|TypeScript|Kubernetes|Docker|AWS|GCP|Azure|C\+\+|Rust|Scala|Ruby|PHP|Postgres|MySQL|MongoDB|Redis|Kafka|Spark|Terraform)\b/g) || []
        ).filter((v, i, a) => a.indexOf(v) === i).slice(0, 12)
        : [];

    return {
        company_name: raw.company || companyName,
        overview: raw.summary || `Research completed for ${companyName}. See the tabs below for details.`,
        culture: joinSnippets(cats.culture) || `Company culture information for ${companyName}.`,
        interview_process: joinSnippets(cats.interview) || `Interview details for ${companyName}.`,
        tech_overview: joinSnippets(cats.tech_stack) || `Technology stack used at ${companyName}.`,
        tech_stack: techStack,
        interview_tips: interviewTips,
        common_questions: [],
        values: [],
        key_facts: {
            'Researched At': new Date(raw.researched_at || Date.now()).toLocaleDateString(),
            'Sources': `${(cats.interview || []).length + (cats.culture || []).length + (cats.tech_stack || []).length} results`,
        },
        sources: {
            interview: toLinks(cats.interview),
            culture: toLinks(cats.culture),
            tech_stack: toLinks(cats.tech_stack),
            salary: toLinks(cats.salary),
        }
    };
}
