
export const mockPosts = [
               {
                              id: 'mock-post-1',
                              author_id: 'mock-user-1',
                              author_name: 'Sarah Engineer',
                              author_username: 'sarah_codes',
                              author_avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
                              content: 'Just finished building a full-stack app with React and FastAPI! check it out on my GitHub.',
                              tags: ['react', 'fastapi', 'project'],
                              likes: ['user-2', 'user-3'],
                              comments: [
                                             { id: 'c1', text: 'Great work!', created_at: new Date().toISOString() }
                              ],
                              created_at: new Date(Date.now() - 3600000).toISOString()
               },
               {
                              id: 'mock-post-2',
                              author_id: 'mock-user-2',
                              author_name: 'David Data',
                              author_username: 'david_ai',
                              author_avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=david',
                              content: 'Exploring the new features in Python 3.14. The performance improvements are impressive.',
                              tags: ['python', 'news', 'tech'],
                              likes: [],
                              comments: [],
                              created_at: new Date(Date.now() - 86400000).toISOString()
               },
               {
                              id: 'mock-post-3',
                              author_id: 'mock-user-3',
                              author_name: 'Tech Recruiter',
                              author_username: 'tech_hiring',
                              author_avatar_url: 'https://api.dicebear.com/7.x/initials/svg?seed=TR',
                              content: 'We are hiring Junior Python Developers! Apply now via the Jobs tab.',
                              tags: ['hiring', 'job', 'python'],
                              likes: ['user-1'],
                              comments: [],
                              created_at: new Date(Date.now() - 172800000).toISOString()
               }
];

export const mockJobs = [
               {
                              _id: "mock-job-1",
                              title: "Junior Python Developer",
                              company: "TechCorp Solutions",
                              location: "Remote",
                              type: "Full-time",
                              description: "We are looking for a passionate Junior Python Developer to join our team...",
                              skills_required: ["Python", "Django", "SQL"],
                              posted_at: new Date().toISOString()
               },
               {
                              _id: "mock-job-2",
                              title: "React Frontend Intern",
                              company: "Creative Studio",
                              location: "Bangalore",
                              type: "Internship",
                              description: "Join our creative team to build beautiful user interfaces with React...",
                              skills_required: ["React", "JavaScript", "CSS"],
                              posted_at: new Date(Date.now() - 86400000).toISOString()
               },
               {
                              _id: "mock-job-3",
                              title: "Machine Learning Engineer",
                              company: "AI Innovations",
                              location: "Hyderabad",
                              type: "Full-time",
                              description: "Work on cutting-edge AI models for healthcare applications.",
                              skills_required: ["Python", "TensorFlow", "PyTorch"],
                              posted_at: new Date(Date.now() - 172800000).toISOString()
               },
               {
                              _id: "mock-job-4",
                              title: "Backend Developer",
                              company: "FinTech Global",
                              location: "Mumbai",
                              type: "Full-time",
                              description: "Build scalable financial systems using Go and Microservices.",
                              skills_required: ["Go", "Distributed Systems", "SQL"],
                              posted_at: new Date(Date.now() - 259200000).toISOString()
               }
];

export const mockProfile = {
               id: "mock-user-1",
               role: "student",
               username: "sarah_codes",
               full_name: "Sarah Engineer",
               email: "sarah@example.com",
               college: "Tech University",
               branch: "Computer Science",
               year: "3rd Year",
               bio: "Full Stack Developer | Python Enthusiast",
               skills: ["Python", "React", "FastAPI", "MongoDB"],
               avatar_url: "https://api.dicebear.com/7.x/avataaars/svg?seed=sarah",
               created_at: new Date().toISOString()
};

export const mockThreads = [
               {
                              id: "mock-thread-1",
                              participants: [
                                             { id: "mock-user-1", name: "Sarah Engineer", avatar_url: "https://api.dicebear.com/7.x/avataaars/svg?seed=sarah" },
                                             { id: "user-1", name: "You", avatar_url: "" }
                              ],
                              last_message: {
                                             content: "Hey, are you interested in the hackathon?",
                                             created_at: new Date(Date.now() - 300000).toISOString(),
                                             sender_id: "mock-user-1"
                              },
                              unread_count: 1
               },
               {
                              id: "mock-thread-2",
                              participants: [
                                             { id: "mock-user-2", name: "David Data", avatar_url: "https://api.dicebear.com/7.x/avataaars/svg?seed=david" },
                                             { id: "user-1", name: "You", avatar_url: "" }
                              ],
                              last_message: {
                                             content: "Thanks for sharing that resource!",
                                             created_at: new Date(Date.now() - 86400000).toISOString(),
                                             sender_id: "user-1"
                              },
                              unread_count: 0
               }
];

export const mockMessages = [
               {
                              id: "m1",
                              content: "Hey, are you interested in the hackathon?",
                              sender_id: "mock-user-1",
                              created_at: new Date(Date.now() - 300000).toISOString()
               },
               {
                              id: "m2",
                              content: "I saw your post about React, looks cool!",
                              sender_id: "mock-user-1",
                              created_at: new Date(Date.now() - 360000).toISOString()
               }
];

export const mockSkillAnalysis = {
               id: "mock-analysis-1",
               missing_skills: [
                              { name: "Docker", priority: "High", reason: "Required for deployment" },
                              { name: "Kubernetes", priority: "Medium", reason: "Good to have for scaling" }
               ],
               roadmap: [
                              { week: 1, topic: "Docker Basics", resources: ["Official Docs", "Youtube Tutorial"] },
                              { week: 2, topic: "Container Orchestration", resources: ["K8s Handbook"] }
               ],
               score: 75
};

export const mockApplications = [
               {
                              id: "app-1",
                              job: { title: "Junior Python Developer", company: "TechCorp Solutions" },
                              status: "applied",
                              applied_at: new Date(Date.now() - 86400000).toISOString()
               },
               {
                              id: "app-2",
                              job: { title: "React Frontend Intern", company: "Creative Studio" },
                              status: "interview",
                              applied_at: new Date(Date.now() - 604800000).toISOString()
               }
];


export const mockNotifications = [
               {
                              id: "n1",
                              title: "Application Update",
                              message: "Your application for React Frontend Intern has moved to Interview stage.",
                              type: "success",
                              read: false,
                              created_at: new Date(Date.now() - 3600000).toISOString()
               },
               {
                              id: "n2",
                              title: "New Job Alert",
                              message: "A new job matching your profile was posted: Machine Learning Engineer",
                              type: "info",
                              read: true,
                              created_at: new Date(Date.now() - 172800000).toISOString()
               }
];

export const mockResumeAnalysis = {
               extracted_data: {
                              name: "Sanket Mutnale",
                              email: "sanket@example.com",
                              phone: "+91 9876543210",
                              skills: ["Python", "FastAPI", "Docker", "Redis", "AWS", "YOLO", "RAG", "LLM", "React"],
                              experience: [
                                             { title: "AI/ML Intern", company: "TechCorp", duration: "6 months" },
                                             { title: "Backend Developer Intern", company: "StartupInc", duration: "3 months" }
                              ],
                              education: [
                                             { degree: "B.Tech Computer Science", institution: "Tech University", year: "2026" }
                              ]
               },
               feedback: {
                              summary: "Your resume is already very strong for a 2026 student. Technically it looks like an early-career AI/Backend engineer resume rather than a fresher resume. You are 80-85% there.",
                              rating: {
                                             overall: 8.5,
                                             breakdown: [
                                                            { aspect: "ATS Friendliness", score: 8.5, max: 10 },
                                                            { aspect: "Technical Depth", score: 9, max: 10 },
                                                            { aspect: "Clarity", score: 7.5, max: 10 },
                                                            { aspect: "Impact Quantification", score: 8, max: 10 },
                                                            { aspect: "Recruiter Readability", score: 7, max: 10 },
                                                            { aspect: "Industry Alignment", score: 9, max: 10 }
                                             ]
                              },
                              strengths: [
                                             { title: "Very Good Technical Coverage", description: "Backend + AI/ML + DevOps combo (FastAPI, Docker, Redis, AWS, YOLO, RAG). This is exactly what modern recruiters look for." },
                                             { title: "Quantified Achievements", description: "Examples like '>85% accuracy', 'Latency reduced from 3.5s to 1.2s', '100+ concurrent users' make your resume impact-driven." },
                                             { title: "Real Industry Internships", description: "Two internships with meaningful contributions (Dockerized systems, RAG pipelines) are a BIG PLUS." }
                              ],
                              issues: [
                                             { title: "Summary is Generic", description: "Current summary sounds like 1000 other resumes. Needs to be more specific and impact-oriented." },
                                             { title: "Skills Section Needs Reordering", description: "Too many buzzwords. Group by category (Languages, Backend, AI/ML, Cloud) for better readability." },
                                             { title: "Experience Bullets Lack Business Context", description: "Connect tech to impact. E.g., 'Built chatbot' -> 'Built chatbot improving response reliability'." },
                                             { title: "Project Section Needs Product Angle", description: "Describe what problem it solved and who used it, not just the tech stack." },
                                             { title: "Contact Section Formatting", description: "Make links clickable and clean." },
                                             { title: "Missing Sections", description: "Add Achievements, Hackathon ratings, and relevant coursework." }
                              ],
                              action_plan: [
                                             "Rewrite summary with impact focus",
                                             "Reorder technical skills by priority",
                                             "Add business impact in experience bullets",
                                             "Standardize project descriptions",
                                             "Add links properly",
                                             "Add a small 'Achievements' subsection",
                                             "Keep bullets consistent (all 2 lines max)"
                              ]
               }
};

export const mockGapAnalysis = {
               overall_score: 75,
               summary: "Strong in Backend and AI, but gaps in Container Orchestration and Advanced System Design.",
               recommendations: [
                              { skill: "Docker", priority: "High", reason: "Required for deployment efficiency", resources: ["Official Docs", "Docker Mastery Course"] },
                              { skill: "Kubernetes", priority: "Medium", reason: "Standard for scaling containerized apps", resources: ["K8s Handbook"] },
                              { skill: "System Design", priority: "High", reason: "Crucial for senior/architect roles", resources: ["System Design Primer"] },
                              { skill: "CI/CD Pipelines", priority: "Medium", reason: "Essential for modern DevOps workflows", resources: ["GitLab CI Guide"] }
               ],
               roadmap: [
                              { week: 1, topic: "Docker Deep Dive", resources: ["Containerization concepts"] },
                              { week: 2, topic: "Kubernetes Basics", resources: ["Pods, Services, Deployments"] },
                              { week: 3, topic: "CI/CD Implementation", resources: ["GitHub Actions"] },
                              { week: 4, topic: "System Design Patterns", resources: ["Load Balancing, Caching"] }
               ]
};

export const mockInterviews = [
               {
                              id: "mock-int-1",
                              title: "Coding Interview: Python DSA",
                              type: "coding",
                              status: "completed",
                              score: 85,
                              feedback: "Great problem-solving skills. Code was clean and optimized. Work on edge case handling.",
                              date: new Date(Date.now() - 86400000).toISOString()
               },
               {
                              id: "mock-int-2",
                              title: "System Design: URL Shortener",
                              type: "system_design",
                              status: "scheduled",
                              date: new Date(Date.now() + 86400000).toISOString()
               },
               {
                              id: "mock-int-3",
                              title: "Behavioral: Leadership",
                              type: "behavioral",
                              status: "pending_feedback",
                              date: new Date(Date.now() - 172800000).toISOString()
               }
];

export const mockPipeline = {
               id: "pipeline-1",
               stages: [
                              {
                                             id: "stage-1",
                                             name: "Applied",
                                             candidates: [
                                                            { id: "c1", name: "John Doe", role: "Frontend Dev", match_score: 88, applied_at: "2 days ago" },
                                                            { id: "c2", name: "Alice Smith", role: "Backend Dev", match_score: 92, applied_at: "1 day ago" }
                                             ]
                              },
                              {
                                             id: "stage-2",
                                             name: "Screening",
                                             candidates: [
                                                            { id: "c3", name: "Bob Johnson", role: "Full Stack", match_score: 75, applied_at: "5 days ago" }
                                             ]
                              },
                              {
                                             id: "stage-3",
                                             name: "Interview",
                                             candidates: [
                                                            { id: "c4", name: "Sanket Mutnale", role: "AI Engineer", match_score: 95, applied_at: "1 week ago" }
                                             ]
                              },
                              {
                                             id: "stage-4",
                                             name: "Offer",
                                             candidates: []
                              }
               ]
};
