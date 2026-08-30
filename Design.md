# Design.md

# Product & UX Design Specification

## 1. Design Goal

Create a calm, information-dense research workspace that makes a complex autonomous process understandable without overwhelming the user.

The interface should feel like a serious analytical tool, not a generic AI chat application.

## 2. Design Principles

- Chat is the entry point, not the whole product.
- Evidence and decisions should be first-class UI objects.
- Users should understand what the system is doing, why it is doing it, and where uncertainty remains.
- Important information should be inspectable without opening raw agent logs.
- Visual hierarchy should favor conclusions, evidence, uncertainty, and actions.
- Avoid dashboard clutter.

## 3. Primary Information Architecture

```text
App
├── Home
│   ├── New Task
│   ├── Recent Research
│   └── Active Runs
├── Projects
│   └── Project Workspace
│       ├── Overview
│       ├── Research
│       ├── Evidence
│       ├── Decisions
│       ├── Documents
│       └── Memory
├── Task / Run Workspace
│   ├── Conversation
│   ├── Plan
│   ├── Evidence
│   ├── Sources
│   ├── Agent Activity
│   └── Final Decision
└── Settings
```

## 4. Primary Screen: Research Workspace

The default desktop composition should use three areas:

```text
┌──────────────────────────────────────────────────────────────┐
│ Header: Project / Task / Status / Share / Export             │
├────────────────┬────────────────────────────┬────────────────┤
│ Investigation  │ Conversation / Findings    │ Evidence       │
│                │                            │                │
│ Plan           │ User messages              │ Claims         │
│ Tasks          │ Agent findings             │ Sources        │
│ Status         │ Current conclusion         │ Confidence     │
│                │                            │                │
│                │                            │                │
├────────────────┴────────────────────────────┴────────────────┤
│ Agent activity / progress / approvals / system events        │
└──────────────────────────────────────────────────────────────┘
```

## 5. Main Components

### Task Header
Shows:
- Project
- Task title
- Mode
- Status
- Confidence
- Runtime
- Cost

### Investigation Plan
Displays dynamic workstreams:
- Research
- Data analysis
- Validation
- Critic
- Decision

The plan must visibly support new tasks appearing dynamically.

### Conversation
Normal chat interaction with rich result cards.

### Evidence Panel
Each claim should show:
- Claim text
- Status
- Confidence
- Supporting sources
- Contradicting sources
- Source type

### Source Card
Show:
- Title
- Publisher
- Date
- Source type
- Relevance
- Evidence excerpt
- Open source action

### Decision Card
Show:
- Recommendation
- Confidence
- Alternatives
- Key reasons
- Risks
- Assumptions
- What would change the decision

### Agent Activity
Show human-readable events such as:
- Researching pricing data
- Checking company filings
- Comparing two conflicting sources
- Testing downside scenario

Do not show raw prompts by default.

## 6. Research Status Model

Use clear states:

```text
Queued
Planning
Researching
Analyzing
Validating
Challenging
Waiting for user
Synthesizing
Complete
Failed
```

## 7. Visual Language

Recommended:
- Light neutral background
- Strong typography hierarchy
- Restrained accent color
- Subtle borders
- Medium corner radius
- Minimal shadows
- Compact but readable data tables

Avoid:
- Excessive gradients
- Giant hero illustrations
- Neon AI aesthetics
- Too many cards
- Decorative charts without analytical value

## 8. Evidence States

The design should make evidence state instantly readable:

- Supported
- Partially supported
- Contradicted
- Inferred
- Assumption
- Insufficient evidence

Use icon + label + text rather than color alone.

## 9. Decision Visualization

Provide a compact decision summary:

```text
Recommendation
OPTION B

Confidence
81%

Why
• Lower total cost
• Lower operational risk
• Meets stated constraints

Main risks
• Vendor lock-in
• Uncertain long-term pricing

Decision trigger
Re-evaluate if monthly spend exceeds X.
```

## 10. Responsive Design

### Desktop
Three-column research workspace.

### Tablet
Two-column layout with collapsible evidence.

### Mobile
Single-column flow:
- Recommendation
- Conversation
- Evidence
- Plan

Agent activity should become an expandable bottom sheet/section.

## 11. Accessibility

- Keyboard navigation
- Visible focus states
- Semantic headings
- Minimum readable text sizing
- Do not rely on color alone
- Accessible status labels

## 12. AI-Agent Handoff Protocol for UI Design

This document is intentionally structured so separate UI-generation agents can work independently.

### Agent A: Information Architecture
Input: sections 3-5.
Output: page hierarchy and interaction map.

### Agent B: Visual System
Input: sections 6-8.
Output: typography, spacing, colors, component states.

### Agent C: Research Workspace
Input: sections 4-5.
Output: desktop workspace layout.

### Agent D: Evidence UX
Input: sections 5 and 8.
Output: evidence panel, source cards, claim states.

### Agent E: Decision UX
Input: section 9.
Output: recommendation and scenario components.

### Agent F: Responsive UX
Input: section 10.
Output: tablet and mobile adaptations.

### Agent G: Accessibility Review
Input: section 11.
Output: accessibility issues and fixes.

## 13. Design Review Format

Every UI agent should report:
1. What screen was designed.
2. What user action it supports.
3. What data is visible.
4. What is interactive.
5. What happens in loading, empty, error, and completion states.
6. What is intentionally hidden to reduce cognitive load.
7. Any deviation from this Design.md.

## 14. Required States

Every major screen must have:
- Empty state
- Loading state
- Partial-progress state
- Error state
- Waiting-for-user state
- Completed state

