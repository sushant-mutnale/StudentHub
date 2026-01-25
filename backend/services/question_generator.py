"""
Question Generator Service
Generates interview questions by type: DSA, Behavioral, Design, Technical.
Features: Question bank lookup, LLM generation, difficulty adaptation, company customization.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import random
import re

from bson import ObjectId

from ..database import get_database


class QuestionType(str, Enum):
    DSA = "dsa"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    TECHNICAL = "technical"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# ============ Question Bank (Built-in) ============

DSA_QUESTION_BANK = [
    # Easy
    {
        "title": "Two Sum",
        "difficulty": "easy",
        "topics": ["arrays", "hashmaps"],
        "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume each input has exactly one solution.",
        "examples": [
            {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "nums[0] + nums[1] = 2 + 7 = 9"},
            {"input": "nums = [3,2,4], target = 6", "output": "[1,2]"}
        ],
        "constraints": ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
        "test_cases": [
            {"input": [[2,7,11,15], 9], "expected": [0,1]},
            {"input": [[3,2,4], 6], "expected": [1,2]},
            {"input": [[3,3], 6], "expected": [0,1]}
        ],
        "ideal_approach": "Use hashmap to store complement. O(n) time, O(n) space.",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)"
    },
    {
        "title": "Reverse Linked List",
        "difficulty": "easy",
        "topics": ["linked lists"],
        "description": "Given the head of a singly linked list, reverse the list and return the reversed list.",
        "examples": [
            {"input": "head = [1,2,3,4,5]", "output": "[5,4,3,2,1]"},
            {"input": "head = [1,2]", "output": "[2,1]"}
        ],
        "constraints": ["0 <= number of nodes <= 5000"],
        "test_cases": [],
        "ideal_approach": "Iterative: use three pointers (prev, curr, next). O(n) time, O(1) space.",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)"
    },
    {
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "topics": ["strings", "stacks"],
        "description": "Given a string containing just '(', ')', '{', '}', '[' and ']', determine if the input string is valid. An input string is valid if: Open brackets must be closed by the same type, in the correct order.",
        "examples": [
            {"input": "s = \"()\"", "output": "true"},
            {"input": "s = \"()[]{}\"", "output": "true"},
            {"input": "s = \"(]\"", "output": "false"}
        ],
        "constraints": ["1 <= s.length <= 10^4"],
        "test_cases": [
            {"input": ["()"], "expected": True},
            {"input": ["()[]{}"], "expected": True},
            {"input": ["(]"], "expected": False}
        ],
        "ideal_approach": "Use stack. Push opening brackets, pop and match for closing. O(n) time, O(n) space.",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)"
    },
    
    # Medium
    {
        "title": "Longest Substring Without Repeating Characters",
        "difficulty": "medium",
        "topics": ["strings", "sliding window", "hashmaps"],
        "description": "Given a string s, find the length of the longest substring without repeating characters.",
        "examples": [
            {"input": "s = \"abcabcbb\"", "output": "3", "explanation": "The answer is 'abc' with length 3"},
            {"input": "s = \"bbbbb\"", "output": "1"}
        ],
        "constraints": ["0 <= s.length <= 5 * 10^4"],
        "test_cases": [
            {"input": ["abcabcbb"], "expected": 3},
            {"input": ["bbbbb"], "expected": 1},
            {"input": ["pwwkew"], "expected": 3}
        ],
        "ideal_approach": "Sliding window with hashset/hashmap to track characters. O(n) time.",
        "time_complexity": "O(n)",
        "space_complexity": "O(min(n, m))"
    },
    {
        "title": "LRU Cache",
        "difficulty": "medium",
        "topics": ["design", "hashmaps", "linked lists"],
        "description": "Design a data structure that follows the constraints of a Least Recently Used (LRU) cache. Implement get(key) and put(key, value) with O(1) time complexity.",
        "examples": [
            {"input": "LRUCache(2), put(1,1), put(2,2), get(1) -> 1, put(3,3), get(2) -> -1", "output": "Cache evicts key 2"}
        ],
        "constraints": ["1 <= capacity <= 3000"],
        "test_cases": [],
        "ideal_approach": "Hashmap + Doubly Linked List. HashMap for O(1) lookup, DLL for O(1) removal/insertion.",
        "time_complexity": "O(1)",
        "space_complexity": "O(capacity)"
    },
    {
        "title": "Binary Tree Level Order Traversal",
        "difficulty": "medium",
        "topics": ["trees", "bfs", "queues"],
        "description": "Given the root of a binary tree, return the level order traversal of its nodes' values (i.e., from left to right, level by level).",
        "examples": [
            {"input": "root = [3,9,20,null,null,15,7]", "output": "[[3],[9,20],[15,7]]"}
        ],
        "constraints": ["0 <= number of nodes <= 2000"],
        "test_cases": [],
        "ideal_approach": "BFS with queue. Track level size for proper grouping.",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)"
    },
    {
        "title": "Number of Islands",
        "difficulty": "medium",
        "topics": ["graphs", "dfs", "bfs", "arrays"],
        "description": "Given an m x n 2D grid map of '1's (land) and '0's (water), return the number of islands. An island is surrounded by water and formed by connecting adjacent lands horizontally or vertically.",
        "examples": [
            {"input": "[[1,1,0],[1,1,0],[0,0,1]]", "output": "2"}
        ],
        "constraints": ["1 <= m, n <= 300"],
        "test_cases": [],
        "ideal_approach": "DFS/BFS from each unvisited '1', mark connected cells as visited.",
        "time_complexity": "O(m*n)",
        "space_complexity": "O(m*n)"
    },
    
    # Hard
    {
        "title": "Merge K Sorted Lists",
        "difficulty": "hard",
        "topics": ["linked lists", "heaps", "divide and conquer"],
        "description": "You are given an array of k linked-lists lists, each linked-list is sorted in ascending order. Merge all the linked-lists into one sorted linked-list and return it.",
        "examples": [
            {"input": "lists = [[1,4,5],[1,3,4],[2,6]]", "output": "[1,1,2,3,4,4,5,6]"}
        ],
        "constraints": ["k == lists.length", "0 <= k <= 10^4"],
        "test_cases": [],
        "ideal_approach": "Use min-heap to always get smallest element. Alternative: divide and conquer merge.",
        "time_complexity": "O(N log k)",
        "space_complexity": "O(k)"
    },
    {
        "title": "Trapping Rain Water",
        "difficulty": "hard",
        "topics": ["arrays", "two pointers", "stacks", "dp"],
        "description": "Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining.",
        "examples": [
            {"input": "height = [0,1,0,2,1,0,1,3,2,1,2,1]", "output": "6"}
        ],
        "constraints": ["n == height.length", "0 <= height[i] <= 10^5"],
        "test_cases": [],
        "ideal_approach": "Two pointers approach. Track max heights from left and right.",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)"
    },
    {
        "title": "Word Search II",
        "difficulty": "hard",
        "topics": ["tries", "backtracking", "dfs"],
        "description": "Given an m x n board of characters and a list of strings words, return all words on the board. Each word must be constructed from letters of sequentially adjacent cells.",
        "examples": [
            {"input": "board = [[o,a,a,n],[e,t,a,e],[i,h,k,r],[i,f,l,v]], words = [oath,pea,eat,rain]", "output": "[eat,oath]"}
        ],
        "constraints": ["m == board.length", "n == board[i].length"],
        "test_cases": [],
        "ideal_approach": "Build Trie from words, DFS on board with Trie pruning.",
        "time_complexity": "O(m*n*4^L)",
        "space_complexity": "O(W*L)"
    }
]

BEHAVIORAL_QUESTION_TEMPLATES = [
    # Leadership
    {"theme": "leadership", "question": "Tell me about a time when you had to lead a team through a challenging project. What was your approach?", "expected_format": "STAR", "key_points": ["clear leadership style", "team coordination", "outcome achieved"]},
    {"theme": "leadership", "question": "Describe a situation where you had to motivate team members who were struggling. How did you handle it?", "expected_format": "STAR", "key_points": ["empathy", "motivation techniques", "results"]},
    
    # Ownership
    {"theme": "ownership", "question": "Tell me about a time when you took ownership of a project outside your normal responsibilities.", "expected_format": "STAR", "key_points": ["initiative", "accountability", "impact"]},
    {"theme": "ownership", "question": "Describe a situation where something went wrong and you took responsibility for fixing it.", "expected_format": "STAR", "key_points": ["accountability", "problem-solving", "learning"]},
    
    # Customer Focus
    {"theme": "customer obsession", "question": "Tell me about a time when you went above and beyond for a customer or user.", "expected_format": "STAR", "key_points": ["understanding needs", "extra effort", "customer satisfaction"]},
    {"theme": "customer obsession", "question": "Describe a situation where you had to balance customer needs with technical constraints.", "expected_format": "STAR", "key_points": ["prioritization", "communication", "compromise"]},
    
    # Conflict Resolution
    {"theme": "conflict resolution", "question": "Tell me about a time when you disagreed with a coworker or manager. How did you handle it?", "expected_format": "STAR", "key_points": ["professional approach", "communication", "resolution"]},
    {"theme": "conflict resolution", "question": "Describe a situation where you had to give difficult feedback to someone.", "expected_format": "STAR", "key_points": ["constructive approach", "empathy", "outcome"]},
    
    # Innovation
    {"theme": "innovation", "question": "Tell me about a time when you came up with a creative solution to a problem.", "expected_format": "STAR", "key_points": ["creativity", "implementation", "impact"]},
    {"theme": "innovation", "question": "Describe a project where you simplified a complex process.", "expected_format": "STAR", "key_points": ["analysis", "simplification", "efficiency gains"]},
    
    # Failure & Learning
    {"theme": "learning", "question": "Tell me about a time you failed. What did you learn from it?", "expected_format": "STAR", "key_points": ["honest failure", "self-reflection", "applied learning"]},
    {"theme": "learning", "question": "Describe a situation where you had to learn something new quickly.", "expected_format": "STAR", "key_points": ["learning approach", "adaptability", "application"]},
    
    # Teamwork
    {"theme": "teamwork", "question": "Tell me about a successful team project. What was your role?", "expected_format": "STAR", "key_points": ["collaboration", "contribution", "team success"]},
    {"theme": "teamwork", "question": "Describe a time when you helped a struggling teammate.", "expected_format": "STAR", "key_points": ["empathy", "support", "team improvement"]},
]

SYSTEM_DESIGN_QUESTIONS = [
    {
        "title": "Design a URL Shortener",
        "description": "Design a URL shortening service like bit.ly. Users should be able to create short URLs and be redirected to the original URL.",
        "requirements": ["Handle 100M URLs", "Short URLs should be unique", "Analytics for clicks", "Custom aliases"],
        "expected_components": ["hash generation", "database", "caching", "load balancer", "analytics"],
        "discussion_points": ["hash collision handling", "read-heavy optimization", "cache invalidation"],
        "difficulty": "medium"
    },
    {
        "title": "Design Twitter/X Feed",
        "description": "Design the home timeline feature. Users should see tweets from people they follow, sorted by relevance/time.",
        "requirements": ["Handle 300M users", "Real-time updates", "Personalized ranking", "Media support"],
        "expected_components": ["feed generation", "caching", "fanout", "ranking", "CDN"],
        "discussion_points": ["push vs pull", "celebrity problem", "relevance algorithm"],
        "difficulty": "hard"
    },
    {
        "title": "Design a Rate Limiter",
        "description": "Design a rate limiter for an API that limits requests per user/IP to prevent abuse.",
        "requirements": ["Distributed across servers", "Multiple rate limit policies", "Minimal latency"],
        "expected_components": ["token bucket/sliding window", "redis", "response headers"],
        "discussion_points": ["algorithm choice", "distributed sync", "race conditions"],
        "difficulty": "medium"
    },
    {
        "title": "Design a Chat Application",
        "description": "Design a real-time messaging application like WhatsApp/Slack with 1-1 and group chats.",
        "requirements": ["Real-time delivery", "Message persistence", "Read receipts", "Presence status"],
        "expected_components": ["websockets", "message queue", "database", "presence service"],
        "discussion_points": ["delivery guarantees", "message ordering", "offline sync"],
        "difficulty": "hard"
    },
    {
        "title": "Design an E-commerce System",
        "description": "Design the core system for an e-commerce platform handling products, cart, orders, and payments.",
        "requirements": ["Handle flash sales", "Inventory management", "Payment processing", "Order tracking"],
        "expected_components": ["product catalog", "cart service", "order service", "payment gateway", "inventory"],
        "discussion_points": ["inventory locking", "distributed transactions", "eventual consistency"],
        "difficulty": "hard"
    },
    {
        "title": "Design a Notification System",
        "description": "Design a system to send notifications (push, email, SMS) to millions of users.",
        "requirements": ["Multiple channels", "Priority handling", "Template management", "Analytics"],
        "expected_components": ["message queue", "channel handlers", "template engine", "preference service"],
        "discussion_points": ["delivery priority", "rate limiting per channel", "retry strategies"],
        "difficulty": "medium"
    },
]


class QuestionGenerator:
    """
    Generates interview questions based on type, company, difficulty, and context.
    """
    
    def __init__(self):
        self._llm_service = None
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def _questions_collection(self):
        return get_database()["question_bank"]
    
    # ============ DSA Questions ============
    
    async def generate_dsa_question(
        self,
        difficulty: str = "medium",
        topics: Optional[List[str]] = None,
        company: Optional[str] = None,
        exclude_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a DSA coding question."""
        
        # 1. Try to find from question bank in DB
        db_question = await self._find_dsa_from_db(difficulty, topics, company, exclude_ids)
        if db_question:
            return self._format_dsa_question(db_question, "database")
        
        # 2. Find from built-in bank
        matching = [q for q in DSA_QUESTION_BANK if q["difficulty"] == difficulty]
        
        if topics:
            topics_lower = [t.lower() for t in topics]
            matching = [q for q in matching if any(t in topics_lower for t in q["topics"])]
        
        if matching:
            question = random.choice(matching)
            return self._format_dsa_question(question, "builtin")
        
        # 3. Generate with LLM
        llm = self._get_llm_service()
        if llm:
            return await self._generate_dsa_with_llm(difficulty, topics, company)
        
        # 4. Fallback to any question
        return self._format_dsa_question(random.choice(DSA_QUESTION_BANK), "fallback")
    
    async def _find_dsa_from_db(
        self,
        difficulty: str,
        topics: Optional[List[str]],
        company: Optional[str],
        exclude_ids: Optional[List[str]]
    ) -> Optional[Dict]:
        """Find DSA question from database."""
        try:
            query = {"type": "dsa", "difficulty": difficulty}
            
            if topics:
                query["topics"] = {"$in": topics}
            
            if company:
                query["$or"] = [
                    {"companies": {"$regex": company, "$options": "i"}},
                    {"companies": {"$exists": False}}
                ]
            
            if exclude_ids:
                query["_id"] = {"$nin": [ObjectId(id) for id in exclude_ids if ObjectId.is_valid(id)]}
            
            cursor = self._questions_collection().find(query).limit(10)
            questions = await cursor.to_list(10)
            
            if questions:
                return random.choice(questions)
        except Exception:
            pass
        return None
    
    async def _generate_dsa_with_llm(
        self,
        difficulty: str,
        topics: Optional[List[str]],
        company: Optional[str]
    ) -> Dict[str, Any]:
        """Generate DSA question using LLM."""
        llm = self._get_llm_service()
        if not llm:
            return self._format_dsa_question(random.choice(DSA_QUESTION_BANK), "fallback")
        
        topic = random.choice(topics) if topics else "arrays"
        
        prompt = f"""Generate a {difficulty} difficulty LeetCode-style coding problem.

Topic: {topic}
{"Company context: " + company if company else ""}

Respond in this EXACT format:
TITLE: [Problem title]
DESCRIPTION: [Clear problem statement with examples]
CONSTRAINTS: [Input constraints, one per line]
EXAMPLE_INPUT: [Example input]
EXAMPLE_OUTPUT: [Expected output]
APPROACH: [Brief solution approach]
TIME_COMPLEXITY: [e.g., O(n)]
SPACE_COMPLEXITY: [e.g., O(1)]"""

        try:
            response = await llm.generate(prompt)
            return self._parse_llm_dsa_question(response, difficulty, topics)
        except Exception:
            return self._format_dsa_question(random.choice(DSA_QUESTION_BANK), "fallback")
    
    def _parse_llm_dsa_question(
        self,
        response: str,
        difficulty: str,
        topics: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Parse LLM-generated DSA question."""
        question = {
            "type": "dsa",
            "title": "",
            "description": "",
            "difficulty": difficulty,
            "topics": topics or [],
            "examples": [],
            "constraints": [],
            "ideal_approach": "",
            "time_complexity": "",
            "space_complexity": "",
            "source": "llm"
        }
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("TITLE:"):
                question["title"] = line[6:].strip()
            elif line.upper().startswith("DESCRIPTION:"):
                question["description"] = line[12:].strip()
            elif line.upper().startswith("CONSTRAINTS:"):
                question["constraints"] = [c.strip() for c in line[12:].split(",")]
            elif line.upper().startswith("EXAMPLE_INPUT:"):
                question["examples"].append({"input": line[14:].strip()})
            elif line.upper().startswith("EXAMPLE_OUTPUT:"):
                if question["examples"]:
                    question["examples"][-1]["output"] = line[15:].strip()
            elif line.upper().startswith("APPROACH:"):
                question["ideal_approach"] = line[9:].strip()
            elif line.upper().startswith("TIME_COMPLEXITY:"):
                question["time_complexity"] = line[16:].strip()
            elif line.upper().startswith("SPACE_COMPLEXITY:"):
                question["space_complexity"] = line[17:].strip()
        
        if not question["title"]:
            question["title"] = "Coding Problem"
        if not question["description"]:
            question["description"] = response[:500]
        
        return question
    
    def _format_dsa_question(self, question: Dict, source: str) -> Dict[str, Any]:
        """Format DSA question for response."""
        return {
            "type": "dsa",
            "title": question.get("title", ""),
            "description": question.get("description", ""),
            "difficulty": question.get("difficulty", "medium"),
            "topics": question.get("topics", []),
            "examples": question.get("examples", []),
            "constraints": question.get("constraints", []),
            "ideal_approach": question.get("ideal_approach", ""),
            "time_complexity": question.get("time_complexity", ""),
            "space_complexity": question.get("space_complexity", ""),
            "test_cases": question.get("test_cases", []),
            "source": source,
            "hints": [
                "Think about edge cases",
                "Consider time and space complexity",
                question.get("ideal_approach", "")[:50] if question.get("ideal_approach") else ""
            ]
        }
    
    # ============ Behavioral Questions ============
    
    async def generate_behavioral_question(
        self,
        themes: Optional[List[str]] = None,
        company: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate a behavioral interview question."""
        
        # Filter by themes if provided
        matching = BEHAVIORAL_QUESTION_TEMPLATES
        if themes:
            themes_lower = [t.lower() for t in themes]
            matching = [q for q in matching if any(t in q["theme"].lower() for t in themes_lower)]
        
        if not matching:
            matching = BEHAVIORAL_QUESTION_TEMPLATES
        
        # Try LLM for company-specific question
        llm = self._get_llm_service()
        if llm and company:
            try:
                return await self._generate_behavioral_with_llm(themes, company)
            except Exception:
                pass
        
        # Use template
        template = random.choice(matching)
        return {
            "type": "behavioral",
            "theme": template["theme"],
            "question": template["question"],
            "expected_format": template["expected_format"],
            "key_points": template["key_points"],
            "hints": [
                "Use STAR format: Situation, Task, Action, Result",
                "Be specific with examples and metrics",
                "Focus on your individual contribution"
            ],
            "source": "template"
        }
    
    async def _generate_behavioral_with_llm(
        self,
        themes: Optional[List[str]],
        company: str
    ) -> Dict[str, Any]:
        """Generate behavioral question using LLM."""
        llm = self._get_llm_service()
        theme = random.choice(themes) if themes else "leadership"
        
        prompt = f"""Generate a behavioral interview question for {company}.

Theme/Value: {theme}
Company context: {company} interview

The question should:
1. Start with "Tell me about a time when..." or "Describe a situation where..."
2. Relate to {theme}
3. Be answerable using STAR format

Respond in this format:
QUESTION: [The behavioral question]
KEY_POINTS: [Point 1] | [Point 2] | [Point 3]"""

        try:
            response = await llm.generate(prompt)
            return self._parse_behavioral_response(response, theme)
        except Exception:
            # Fallback to template
            template = random.choice(BEHAVIORAL_QUESTION_TEMPLATES)
            return {
                "type": "behavioral",
                "theme": template["theme"],
                "question": template["question"],
                "expected_format": "STAR",
                "key_points": template["key_points"],
                "hints": ["Use STAR format", "Be specific"],
                "source": "template"
            }
    
    def _parse_behavioral_response(self, response: str, theme: str) -> Dict[str, Any]:
        """Parse LLM behavioral question."""
        result = {
            "type": "behavioral",
            "theme": theme,
            "question": "",
            "expected_format": "STAR",
            "key_points": [],
            "hints": ["Use STAR format", "Be specific", "Quantify results"],
            "source": "llm"
        }
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            if line.upper().startswith("QUESTION:"):
                result["question"] = line[9:].strip()
            elif line.upper().startswith("KEY_POINTS:"):
                points = line[11:].strip().split("|")
                result["key_points"] = [p.strip() for p in points if p.strip()]
        
        if not result["question"]:
            result["question"] = response.split("\n")[0][:200]
        
        return result
    
    # ============ System Design Questions ============
    
    async def generate_design_question(
        self,
        difficulty: str = "medium",
        exclude_titles: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate a system design question."""
        
        matching = SYSTEM_DESIGN_QUESTIONS
        if difficulty:
            matching = [q for q in matching if q["difficulty"] == difficulty]
        
        if exclude_titles:
            matching = [q for q in matching if q["title"] not in exclude_titles]
        
        if not matching:
            matching = SYSTEM_DESIGN_QUESTIONS
        
        question = random.choice(matching)
        
        return {
            "type": "system_design",
            "title": question["title"],
            "description": question["description"],
            "requirements": question["requirements"],
            "expected_components": question["expected_components"],
            "discussion_points": question["discussion_points"],
            "difficulty": question["difficulty"],
            "hints": [
                "Start with requirements clarification",
                "Discuss high-level architecture first",
                "Consider scalability and tradeoffs"
            ],
            "source": "template"
        }
    
    # ============ Technical Questions (Resume-based) ============
    
    async def generate_technical_question(
        self,
        resume_data: Dict[str, Any],
        asked_topics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate technical question based on resume projects."""
        
        projects = resume_data.get("projects", [])
        experience = resume_data.get("experience", [])
        skills = resume_data.get("skills", [])
        
        llm = self._get_llm_service()
        
        if projects and llm:
            # Pick a project not yet asked about
            available = [p for p in projects if p.get("name") not in (asked_topics or [])]
            if not available:
                available = projects
            
            project = random.choice(available) if available else {"name": "project", "description": ""}
            
            return await self._generate_project_question(project, skills)
        
        # Fallback: skill-based question
        if skills:
            skill = random.choice(skills[:5])
            return {
                "type": "technical",
                "question": f"Can you explain how you've used {skill} in your projects? What challenges did you face?",
                "context": f"Based on your skill: {skill}",
                "expected_depth": "Explain concepts, share examples, discuss challenges",
                "hints": ["Explain the 'why' not just 'what'", "Share specific examples"],
                "source": "skill_based"
            }
        
        return {
            "type": "technical",
            "question": "Tell me about a technical project you're most proud of. What was your contribution?",
            "context": "General technical discussion",
            "expected_depth": "Architecture, challenges, solutions",
            "hints": ["Be specific about your role", "Discuss technical decisions"],
            "source": "fallback"
        }
    
    async def _generate_project_question(
        self,
        project: Dict[str, Any],
        skills: List[str]
    ) -> Dict[str, Any]:
        """Generate question about a specific project."""
        llm = self._get_llm_service()
        
        project_name = project.get("name", "project")
        project_desc = project.get("description", "")
        technologies = project.get("technologies", [])
        
        if llm:
            prompt = f"""Generate a deep technical interview question about this project.

Project: {project_name}
Description: {project_desc}
Technologies: {', '.join(technologies) if technologies else 'not specified'}

Ask a question that:
1. Tests understanding of architecture/design decisions
2. Probes for challenges faced
3. Is specific to the project

Respond with just the question, starting with "I see you built..." or "Tell me about..."."""

            try:
                response = await llm.generate(prompt)
                question = response.strip().split("\n")[0]
                
                return {
                    "type": "technical",
                    "question": question,
                    "context": f"Based on: {project_name}",
                    "project_name": project_name,
                    "expected_depth": "Architecture, decisions, challenges, learnings",
                    "hints": [
                        "Explain your design decisions",
                        "Discuss challenges and how you solved them",
                        "Mention what you would do differently"
                    ],
                    "source": "llm_project"
                }
            except Exception:
                pass
        
        # Fallback
        return {
            "type": "technical",
            "question": f"I see you built {project_name}. Can you walk me through the architecture and key technical decisions you made?",
            "context": f"Based on: {project_name}",
            "project_name": project_name,
            "expected_depth": "Architecture, decisions, challenges",
            "hints": ["Explain the system design", "Discuss tradeoffs"],
            "source": "template_project"
        }
    
    # ============ Question by Type ============
    
    async def generate_question(
        self,
        question_type: str,
        difficulty: str = "medium",
        company: Optional[str] = None,
        themes: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        resume_data: Optional[Dict] = None,
        exclude_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate question based on type."""
        
        if question_type in ["dsa", QuestionType.DSA]:
            return await self.generate_dsa_question(difficulty, topics, company, exclude_ids)
        
        elif question_type in ["behavioral", QuestionType.BEHAVIORAL]:
            return await self.generate_behavioral_question(themes, company)
        
        elif question_type in ["system_design", QuestionType.SYSTEM_DESIGN]:
            return await self.generate_design_question(difficulty)
        
        elif question_type in ["technical", QuestionType.TECHNICAL]:
            return await self.generate_technical_question(resume_data or {})
        
        else:
            # Default to DSA
            return await self.generate_dsa_question(difficulty, topics, company, exclude_ids)


# Singleton instance
question_generator = QuestionGenerator()
