# Core Modules: Mermaid Data Flow Diagrams

This document contains Mermaid.js diagrams illustrating the data flows and architecture for each of the 5 Core Modules in the StudentHub platform. Markdown viewers with Mermaid support (like GitHub or many VSCode previewers) will render these automatically.

---

## 1. User & Profile Management

```mermaid
graph TD
    %% Entities
    Student[Student]
    Recruiter[Recruiter]
    Admin[Admin]
    
    %% Processes
    Auth(1.1 Authentication & JWT)
    ResumeParser(1.2 AI Resume Parser)
    ProfileStore(1.3 Profile Management)
    Verification(1.4 Verification)
    
    %% Databases
    DB_User[(User Database)]
    LLM[Gemini LLM]
    
    %% Flows
    Student -->|Credentials| Auth
    Recruiter -->|Credentials| Auth
    Auth -->|JWT Token| Student
    Auth -->|JWT Token| Recruiter
    
    Student -->|PDF Upload| ResumeParser
    ResumeParser -->|Raw Text| LLM
    LLM -->|Extracts Skills/Edu| ResumeParser
    ResumeParser -->|Structured JSON| ProfileStore
    
    Student -->|Updates| ProfileStore
    ProfileStore <-->|R/W Profiles| DB_User
    
    Admin -->|Approves| Verification
    Verification -->|Verified Status| DB_User
```

---

## 2. Evaluation & Matching

```mermaid
graph TD
    %% Entities
    DB_User[(User DB)]
    DB_Jobs[(Jobs DB)]
    JobsIngest[opportunity_ingestion.py]
    Web[External Sites : Internshala / Devpost]
    
    %% Processes
    SemanticCalc(2.1 Semantic Mapping)
    Scoring(2.2 Scoring Engine)
    Sync(2.3 Ingestion Sync)
    
    %% Output
    RN[To Module 4: Notifications]
    
    %% Flows
    Web -->|Scraped Data| Sync
    Sync -->|Normalized Jobs| DB_Jobs
    
    DB_User -->|Student Profiles| SemanticCalc
    DB_Jobs -->|Job Requirements| SemanticCalc
    
    SemanticCalc -->|Mapped Vectors| Scoring
    Scoring -->|Calculate Match %| Scoring
    Scoring -->|High Match Scores| RN
```

---

## 3. Learning & Feedback

```mermaid
graph TD
    %% Entities
    Student[Student]
    DB_Assess[(Assessments DB)]
    LLM[Gemini LLM]
    
    %% Processes
    VoiceInt(3.1 Voice Interview)
    ScoreGen(3.2 Scorecard Generator)
    RoadmapGen(3.3 Roadmap Creator)
    
    %% Flows
    Student <-->|Audio / STT & TTS| VoiceInt
    VoiceInt <-->|Interview Context| LLM
    
    VoiceInt -->|Transcript| ScoreGen
    ScoreGen <-->|Analysis Request| LLM
    ScoreGen -->|JSON Scorecard| DB_Assess
    ScoreGen -->|Results View| Student
    
    DB_Assess -->|Identified Weaknesses| RoadmapGen
    RoadmapGen -->|Generate Markdown| LLM
    RoadmapGen -->|Personalized Path| Student
```

---

## 4. Recommendation & Notification

```mermaid
graph TD
    %% Entities
    StudentUI[Student Dashboard]
    RecruiterUI[Recruiter Dashboard]
    EM[From Module 2: Matching]
    CT[From Module 5: Tracking]
    DB_Jobs[(Jobs DB)]
    DB_Logs[(Logs & Alerts DB)]
    
    %% Processes
    FeedGen(4.1 Opportunity Feed)
    AlertSys(4.2 Alert System)
    
    %% Flows
    EM -->|Top Match Scores| AlertSys
    CT -->|Stage Movement| AlertSys
    
    AlertSys -->|Save Unread Alert| DB_Logs
    DB_Logs -->|Fetch Alerts| StudentUI
    DB_Logs -->|Fetch Alerts| RecruiterUI
    
    StudentUI -->|Query Recommended| FeedGen
    FeedGen -->|Sort by Match Score| DB_Jobs
    DB_Jobs -->|Job List| FeedGen
    FeedGen -->|Display Feed| StudentUI
```

---

## 5. Communication & Tracking

```mermaid
graph TD
    %% Entities
    Student[Student]
    Recruiter[Recruiter]
    DB_User[(User DB - Apps)]
    
    %% Processes
    ApplyReq(5.1 Application Init)
    Kanban(5.2 Stage Kanban)
    Timeline(5.3 Timeline Tracker)
    Chat(5.4 Direct Messaging)
    
    %% Flows
    Student -->|Submit App| ApplyReq
    ApplyReq -->|Status: Pending| DB_User
    
    Recruiter -->|Drag Card| Kanban
    Kanban -->|Update Stage| DB_User
    Kanban -->|Stage Change Event| Timeline
    
    DB_User -->|App History| Timeline
    Timeline -->|View Progress| Student
    
    Student <-->|Send Msg| Chat
    Recruiter <-->|Send Msg| Chat
    Chat <-->|Append Thread| DB_User
```
