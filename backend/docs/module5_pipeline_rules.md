# Module 5: Pipeline Rules & Constraints

## Overview
This document defines the rules and constraints for customizable hiring pipelines.

---

## Pipeline Structure

### Stage Types
Every pipeline MUST contain these mandatory stage types:
1. **APPLIED** - Entry point (exactly 1)
2. **INTERVIEW** - At least one interview stage
3. **OFFER** - Offer extended stage
4. **TERMINAL** - Final outcome (HIRED, REJECTED, WITHDRAWN)

### Stage Schema
```json
{
  "id": "uuid",
  "name": "Human readable name",
  "order": 1,
  "type": "applied|screening|interview|offer|hired|rejected|withdrawn",
  "color": "#hex",
  "permissions": {
    "can_move_to": ["stage_ids"],
    "can_reject": true,
    "requires_scorecard": false
  }
}
```

---

## Default Pipeline Template

Every company starts with this default pipeline:

| Order | Stage Name | Type | Auto-Trigger |
|:---:|:---|:---|:---|
| 1 | Applied | applied | On job application |
| 2 | Resume Screening | screening | Manual |
| 3 | Phone Screen | interview | On interview schedule |
| 4 | Technical Round 1 | interview | On interview schedule |
| 5 | Technical Round 2 | interview | On interview schedule |
| 6 | HR Round | interview | On interview schedule |
| 7 | Offer Extended | offer | On offer create |
| 8 | Hired | hired | On offer accept |
| 9 | Rejected | rejected | Manual / offer decline |
| 10 | Withdrawn | withdrawn | On student withdraw |

---

## Constraints

### Validation Rules
1. **Single Entry**: Exactly one stage with `type=applied`
2. **Terminal Stages**: At least one each of `hired`, `rejected`, `withdrawn`
3. **No Orphans**: All stages must be reachable via transitions
4. **No Cycles**: Forward-only progression (except explicit "Revisit" if allowed)

### Transition Rules
- Allowed transitions defined per stage
- Some transitions may require scorecard submission
- Terminal stages have no outgoing transitions

---

## Versioning Policy

### When Pipeline Changes
1. New version created (old version preserved)
2. Existing applications continue with their original version
3. Recruiter can optionally migrate applications to new version

### Migration Rules
- Stage mapping required for breaking changes
- Audit log entry created for each migration
- Student notification if visible stage changes

---

## Auto-Stage Transitions

| Event | Trigger | Target Stage |
|:---|:---|:---|
| Job Application | `apply_to_job()` | First stage (Applied) |
| Interview Created | `create_interview()` | Next interview stage |
| Interview Completed | `submit_feedback()` | Next stage (manual confirm optional) |
| Offer Extended | `create_offer()` | Offer stage |
| Offer Accepted | `accept_offer()` | Hired |
| Offer Rejected | `reject_offer()` | Offer Declined / Rejected |
| Student Withdraws | `withdraw_application()` | Withdrawn |
