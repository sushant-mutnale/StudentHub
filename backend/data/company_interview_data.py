"""
Company Interview Knowledge Base - Seed Data
Pre-populated interview patterns for major tech companies.
"""

COMPANY_INTERVIEW_DATA = [
    # ================== FAANG/MAANG ==================
    {
        "company": "Amazon",
        "company_aliases": ["amazon", "aws", "amazon web services"],
        "roles": ["SDE", "SDE-1", "SDE-2", "SDE-3", "Software Engineer"],
        "rounds": [
            {"round": 1, "type": "online_assessment", "name": "OA", "duration": 90, "description": "2 coding problems + work simulation"},
            {"round": 2, "type": "phone_screen", "name": "Phone Screen", "duration": 60, "description": "1-2 coding problems + behavioral"},
            {"round": 3, "type": "onsite", "name": "Loop Interview", "duration": 240, "description": "4 rounds: 2 coding + 1 system design + 1 bar raiser"},
        ],
        "total_rounds": 5,
        "dsa_topics": ["arrays", "strings", "trees", "graphs", "dynamic programming", "hashmaps", "two pointers", "bfs", "dfs"],
        "behavioral_themes": [
            "Customer Obsession", "Ownership", "Invent and Simplify", "Are Right, A Lot",
            "Learn and Be Curious", "Hire and Develop the Best", "Insist on the Highest Standards",
            "Think Big", "Bias for Action", "Frugality", "Earn Trust", "Dive Deep",
            "Have Backbone; Disagree and Commit", "Deliver Results"
        ],
        "system_design_topics": ["distributed systems", "scalability", "caching", "load balancing", "microservices"],
        "difficulty": "hard",
        "tips": [
            "Master the 16 Leadership Principles - every behavioral question maps to them",
            "Use STAR method for behavioral answers",
            "Practice explaining your thought process while coding",
            "Focus on trees, graphs, and DP - most common topics",
            "Prepare 8-10 detailed stories from your experience"
        ],
        "example_questions": [
            "Tell me about a time you disagreed with your manager",
            "Describe a time when you took ownership of a project",
            "LeetCode: LRU Cache, Merge K Sorted Lists, Word Ladder"
        ],
        "preparation_time_weeks": 8,
        "sources": ["leetcode.com", "glassdoor.com", "blind.com"]
    },
    {
        "company": "Google",
        "company_aliases": ["google", "alphabet", "youtube"],
        "roles": ["L3", "L4", "L5", "Software Engineer", "SWE"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Phone Screen", "duration": 45, "description": "1 medium-hard coding problem"},
            {"round": 2, "type": "onsite", "name": "Virtual Onsite", "duration": 300, "description": "5 rounds: 4 coding + 1 Googleyness & Leadership"},
        ],
        "total_rounds": 6,
        "dsa_topics": ["arrays", "strings", "graphs", "trees", "dynamic programming", "backtracking", "binary search", "recursion", "bfs", "dfs", "tries"],
        "behavioral_themes": ["Googleyness", "Leadership", "Role-Related Knowledge", "Cognitive Ability"],
        "system_design_topics": ["design gmail", "design youtube", "design google drive", "distributed storage", "search systems"],
        "difficulty": "very hard",
        "tips": [
            "Focus heavily on algorithm optimization - Google cares about efficiency",
            "Be prepared to write clean, bug-free code quickly",
            "Practice on Google Docs/plain text editor - no IDE features",
            "System design is crucial for L4+ roles",
            "Googleyness is about collaboration and intellectual humility"
        ],
        "example_questions": [
            "Design a file sync system like Google Drive",
            "LeetCode: Median of Two Sorted Arrays, Word Break II, Alien Dictionary"
        ],
        "preparation_time_weeks": 10,
        "sources": ["leetcode.com", "glassdoor.com", "teamblind.com"]
    },
    {
        "company": "Microsoft",
        "company_aliases": ["microsoft", "msft", "azure"],
        "roles": ["SDE", "SDE-1", "SDE-2", "Software Engineer", "L59", "L60", "L61", "L62", "L63"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Phone Screen", "duration": 45, "description": "1-2 coding problems"},
            {"round": 2, "type": "onsite", "name": "Virtual Onsite", "duration": 240, "description": "4 rounds: 3 coding + 1 hiring manager/behavioral"},
        ],
        "total_rounds": 5,
        "dsa_topics": ["arrays", "strings", "linked lists", "trees", "graphs", "sorting", "searching", "recursion"],
        "behavioral_themes": ["Growth Mindset", "Customer Obsession", "Diversity & Inclusion", "One Microsoft"],
        "system_design_topics": ["design azure blob storage", "design teams", "design excel online", "cloud architecture"],
        "difficulty": "medium-hard",
        "tips": [
            "Microsoft focuses more on fundamentals than tricky algorithms",
            "Be ready to discuss your projects in depth",
            "Culture fit is important - show growth mindset",
            "Coding rounds may include follow-up optimizations"
        ],
        "example_questions": [
            "Design a distributed cache",
            "LeetCode: Validate BST, Merge Intervals, Serialize Binary Tree"
        ],
        "preparation_time_weeks": 6,
        "sources": ["leetcode.com", "glassdoor.com"]
    },
    {
        "company": "Meta",
        "company_aliases": ["meta", "facebook", "fb", "instagram", "whatsapp"],
        "roles": ["E3", "E4", "E5", "E6", "Software Engineer", "SWE"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Initial Screen", "duration": 45, "description": "2 medium coding problems"},
            {"round": 2, "type": "onsite", "name": "Virtual Onsite", "duration": 270, "description": "2 coding + 1 system design + 1 behavioral"},
        ],
        "total_rounds": 4,
        "dsa_topics": ["arrays", "strings", "trees", "graphs", "dynamic programming", "bfs", "dfs", "hashmaps", "intervals"],
        "behavioral_themes": ["Move Fast", "Be Bold", "Focus on Long-Term Impact", "Build Awesome Things", "Be Open"],
        "system_design_topics": ["design facebook newsfeed", "design messenger", "design instagram", "real-time systems"],
        "difficulty": "hard",
        "tips": [
            "Meta coding interviews are fast-paced - 2 problems in 45 mins",
            "Practice speed and accuracy",
            "Focus on graph problems and string manipulation",
            "Behavioral is less weighted but still important"
        ],
        "example_questions": [
            "Design Facebook News Feed",
            "LeetCode: Valid Parentheses, Add Binary, Clone Graph, Number of Islands"
        ],
        "preparation_time_weeks": 6,
        "sources": ["leetcode.com", "glassdoor.com"]
    },
    {
        "company": "Apple",
        "company_aliases": ["apple", "aapl"],
        "roles": ["ICT2", "ICT3", "ICT4", "ICT5", "Software Engineer"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Recruiter + Tech Screen", "duration": 60, "description": "Coding + domain knowledge"},
            {"round": 2, "type": "onsite", "name": "Onsite Loop", "duration": 300, "description": "5-6 rounds: coding, design, domain, behavioral"},
        ],
        "total_rounds": 7,
        "dsa_topics": ["arrays", "strings", "linked lists", "trees", "OS concepts", "concurrency", "memory management"],
        "behavioral_themes": ["Innovation", "Attention to Detail", "User Experience", "Collaboration", "Secrecy"],
        "system_design_topics": ["iOS architecture", "app design", "real-time sync", "privacy-focused design"],
        "difficulty": "hard",
        "tips": [
            "Apple values domain knowledge heavily - know their ecosystem",
            "OS/systems knowledge is important",
            "Be careful with NDA - they're big on secrecy",
            "User experience focus even in backend roles"
        ],
        "example_questions": [
            "How would you design iCloud sync?",
            "LeetCode: LRU Cache, Design Patterns, Concurrency problems"
        ],
        "preparation_time_weeks": 8,
        "sources": ["glassdoor.com", "levels.fyi"]
    },
    
    # ================== Other Top Tech ==================
    {
        "company": "Netflix",
        "company_aliases": ["netflix", "nflx"],
        "roles": ["Senior Software Engineer", "Staff Engineer"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Tech Screen", "duration": 60, "description": "Deep technical discussion + coding"},
            {"round": 2, "type": "onsite", "name": "Full Loop", "duration": 360, "description": "6+ rounds: coding, design, culture fit"},
        ],
        "total_rounds": 7,
        "dsa_topics": ["system design", "distributed systems", "streaming", "concurrency", "data structures"],
        "behavioral_themes": ["Freedom & Responsibility", "Context Not Control", "Highly Aligned, Loosely Coupled", "Pay Top of Market"],
        "system_design_topics": ["video streaming", "content delivery", "recommendation systems", "microservices at scale"],
        "difficulty": "very hard",
        "tips": [
            "Netflix culture deck is a MUST read",
            "They hire mostly senior engineers",
            "Be prepared for deep system design discussions",
            "Culture fit is extremely important"
        ],
        "example_questions": [
            "Design Netflix's video streaming architecture",
            "How would you handle personalized recommendations at scale?"
        ],
        "preparation_time_weeks": 10,
        "sources": ["glassdoor.com", "netflix.com/culture"]
    },
    {
        "company": "Uber",
        "company_aliases": ["uber"],
        "roles": ["Software Engineer", "SDE-1", "SDE-2", "Staff Engineer"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Tech Screen", "duration": 60, "description": "2 coding problems"},
            {"round": 2, "type": "onsite", "name": "Virtual Onsite", "duration": 240, "description": "4 rounds: 2 coding + 1 system design + 1 behavioral"},
        ],
        "total_rounds": 5,
        "dsa_topics": ["graphs", "shortest path", "geospatial", "real-time systems", "arrays", "hashmaps"],
        "behavioral_themes": ["Move the Ball Forward", "Obsess Over Quality", "Celebrate Differences"],
        "system_design_topics": ["ride matching", "real-time location", "surge pricing", "maps", "payments"],
        "difficulty": "hard",
        "tips": [
            "Focus on geospatial problems and graph algorithms",
            "Understand real-time system design",
            "Practice Dijkstra's and A* algorithms"
        ],
        "example_questions": [
            "Design Uber's ride matching system",
            "LeetCode: Shortest Path, Minimum Cost, Graph problems"
        ],
        "preparation_time_weeks": 6,
        "sources": ["leetcode.com", "glassdoor.com"]
    },
    {
        "company": "LinkedIn",
        "company_aliases": ["linkedin"],
        "roles": ["Software Engineer", "SDE", "Staff Engineer"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Tech Screen", "duration": 60, "description": "1-2 coding problems"},
            {"round": 2, "type": "onsite", "name": "Virtual Onsite", "duration": 240, "description": "4 rounds: 2 coding + 1 system design + 1 behavioral"},
        ],
        "total_rounds": 5,
        "dsa_topics": ["arrays", "strings", "graphs", "trees", "hashmaps", "sorting"],
        "behavioral_themes": ["Members First", "Relationships Matter", "Be Open, Honest and Constructive", "Demand Excellence"],
        "system_design_topics": ["design linkedin feed", "connections graph", "messaging", "search"],
        "difficulty": "medium-hard",
        "tips": [
            "LinkedIn problems are generally straightforward",
            "Focus on graph problems (social network context)",
            "Values alignment is important"
        ],
        "example_questions": [
            "Design LinkedIn connections recommendations",
            "LeetCode: Number of Islands, Course Schedule, Clone Graph"
        ],
        "preparation_time_weeks": 5,
        "sources": ["leetcode.com", "glassdoor.com"]
    },
    
    # ================== Indian Top Companies ==================
    {
        "company": "Flipkart",
        "company_aliases": ["flipkart", "walmart india"],
        "roles": ["SDE-1", "SDE-2", "SDE-3", "Software Engineer"],
        "rounds": [
            {"round": 1, "type": "online_assessment", "name": "Coding Round", "duration": 90, "description": "2-3 DSA problems"},
            {"round": 2, "type": "phone_screen", "name": "Machine Coding", "duration": 90, "description": "LLD problem with working code"},
            {"round": 3, "type": "onsite", "name": "Onsite", "duration": 180, "description": "DSA + System Design + Hiring Manager"},
        ],
        "total_rounds": 5,
        "dsa_topics": ["arrays", "strings", "trees", "graphs", "dynamic programming", "oops", "design patterns"],
        "behavioral_themes": ["Customer First", "Audacity", "Bias for Action", "Integrity"],
        "system_design_topics": ["e-commerce", "inventory", "cart", "payments", "order tracking"],
        "difficulty": "medium-hard",
        "tips": [
            "Machine coding round is unique - practice LLD problems",
            "Focus on SOLID principles and design patterns",
            "E-commerce domain knowledge helps"
        ],
        "example_questions": [
            "Design a parking lot system (machine coding)",
            "Design Flipkart's order management system",
            "LeetCode Medium-Hard level DSA"
        ],
        "preparation_time_weeks": 6,
        "sources": ["geeksforgeeks.org", "glassdoor.com"]
    },
    {
        "company": "Razorpay",
        "company_aliases": ["razorpay"],
        "roles": ["SDE-1", "SDE-2", "Software Engineer"],
        "rounds": [
            {"round": 1, "type": "online_assessment", "name": "HackerRank", "duration": 60, "description": "2 DSA problems"},
            {"round": 2, "type": "phone_screen", "name": "Tech Round 1", "duration": 60, "description": "DSA + basics"},
            {"round": 3, "type": "onsite", "name": "Tech Round 2 + HR", "duration": 120, "description": "Problem solving + culture fit"},
        ],
        "total_rounds": 4,
        "dsa_topics": ["arrays", "strings", "trees", "hashmaps", "basic graphs"],
        "behavioral_themes": ["Customer Obsession", "Ownership", "Speed", "Transparency"],
        "system_design_topics": ["payment gateway", "reconciliation", "fraud detection"],
        "difficulty": "medium",
        "tips": [
            "Focus on fintech domain knowledge",
            "Know basics of payment systems",
            "Good work-life balance culture"
        ],
        "example_questions": [
            "Design a payment processing system",
            "LeetCode Easy-Medium level"
        ],
        "preparation_time_weeks": 4,
        "sources": ["glassdoor.com", "ambitionbox.com"]
    },
    
    # ================== Startups (General Pattern) ==================
    {
        "company": "Startup (General)",
        "company_aliases": ["startup", "early stage", "series a", "series b"],
        "roles": ["Software Engineer", "Full Stack Developer", "Backend Developer"],
        "rounds": [
            {"round": 1, "type": "phone_screen", "name": "Intro Call", "duration": 30, "description": "Culture fit + background"},
            {"round": 2, "type": "take_home", "name": "Take Home Assignment", "duration": 480, "description": "Build a small project"},
            {"round": 3, "type": "onsite", "name": "Technical + Founder", "duration": 120, "description": "Code review + founder interview"},
        ],
        "total_rounds": 3,
        "dsa_topics": ["practical coding", "debugging", "api design", "database design"],
        "behavioral_themes": ["Ownership", "Adaptability", "Hustle", "Learning Agility"],
        "system_design_topics": ["mvp design", "scalable architecture basics", "api design"],
        "difficulty": "medium",
        "tips": [
            "Focus on practical coding over algorithm puzzles",
            "Be ready to discuss how you'd build products",
            "Show ownership mentality",
            "Research the startup's product before interview"
        ],
        "example_questions": [
            "Build a REST API for X feature",
            "How would you scale this system?",
            "Debug this code"
        ],
        "preparation_time_weeks": 2,
        "sources": ["glassdoor.com", "levels.fyi"]
    },
]


# Default pattern for unknown companies
DEFAULT_COMPANY_PATTERN = {
    "company": "Unknown",
    "roles": ["Software Engineer"],
    "rounds": [
        {"round": 1, "type": "phone_screen", "name": "Tech Screen", "duration": 60, "description": "Coding + discussion"},
        {"round": 2, "type": "onsite", "name": "Onsite/Virtual", "duration": 180, "description": "Multiple technical rounds"},
    ],
    "total_rounds": 3,
    "dsa_topics": ["arrays", "strings", "trees", "graphs", "hashmaps"],
    "behavioral_themes": ["Teamwork", "Problem Solving", "Communication"],
    "system_design_topics": ["basic system design", "api design"],
    "difficulty": "medium",
    "tips": [
        "Research the company thoroughly before the interview",
        "Practice common DSA problems",
        "Prepare questions about the role and team"
    ],
    "example_questions": ["LeetCode Medium problems", "Tell me about yourself"],
    "preparation_time_weeks": 4,
    "sources": []
}
