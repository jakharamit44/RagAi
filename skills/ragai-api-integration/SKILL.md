---
name: 'ragai-api-integration'
description: 'Use this skill to integrate the RagAi RAG and Cognitive AI Brain APIs into student portals, employee intranets, faculty dashboards, HR platforms, LMS, and third-party web or mobile applications.'
---

# RagAi API Integration Skill & Developer Guide

## 1. Skill Purpose & Scope

This skill empowers AI agents and software engineers to seamlessly integrate RagAi's high-performance Retrieval-Augmented Generation (RAG) and Cognitive AI Brain services into external web portals, intranet dashboards, mobile applications, and learning management systems (LMS).

### Universal Persona Support
**RagAi is NOT only for students.** The platform is engineered to serve the entire institutional and enterprise ecosystem:
- **Students:** Course syllabi, lecture notes, assignment guidelines, exam schedules, grading schemes, academic calendar.
- **Employees & Administrative Staff:** HR policies, employee leave applications, medical reimbursement rules, payroll & provident fund circulars, procurement processes, campus maintenance requests, IT security protocols.
- **Faculty & Academic Officers:** Curriculum revision notices, departmental committee meeting minutes, research grant circulars, exam supervision rosters, grading submission deadlines.
- **Prospective Candidates & General Public:** Admission criteria, program fee structures, eligibility requirements, campus facilities, contact directories.

---

## 2. Integration Mental Model & Architecture

RagAi operates as an on-premise, secure, private cognitive intelligence layer. External applications interact with it via clean REST JSON APIs or via lightweight embeddable frontend widgets.

```
+----------------------------------------------------------------------------------------------------+
|                                    EXTERNAL CLIENT APPLICATIONS                                    |
+----------------------------------------------------------------------------------------------------+
|   [ Student Portal ]       [ Employee Intranet ]       [ Faculty Dashboard ]    [ Mobile App / LMS]|
+-----------+--------------------------+---------------------------+-----------------------+---------+
            |                          |                           |                       |
            +--------------------------+-------------+-------------+-----------------------+
                                                     |
                                                     v  HTTP POST (JSON)
                                        +-------------------------+
                                        |  X-API-Key Header       |
                                        |  Authorization & RBAC   |
                                        +------------+------------+
                                                     |
                                                     v
                                +-----------------------------------------+
                                |             RAGAI BACKEND               |
                                |       (http://localhost:8000)           |
                                +--------------------+--------------------+
                                                     |
                 +-----------------------------------+-----------------------------------+
                 |                                                                       |
                 v                                                                       v
  +-------------------------------+                                       +-------------------------------+
  |   RETRIEVAL & GENERATION      |                                       |       COGNITIVE AI BRAIN      |
  |   /api/v1/ask                 |                                       |   /api/v1/brain/cortex        |
  |   - Multi-department filter   |                                       |   /api/v1/brain/fire          |
  |   - Role-based scoping        |                                       |   - 4-Phase Thought Pathway   |
  |   - KaTeX Math & Citations    |                                       |   - Semantic associations     |
  |   - Sub-second grounding      |                                       |   - Real-time neural pulses   |
  +-------------------------------+                                       +-------------------------------+
```

---

## 3. Quick Start: 3 Ways to Integrate

Depending on the host platform architecture, choose one of three primary integration paths:

### Method A: Zero-Code Drop-In Web Widget (Simplest & Fastest)
Add a single script tag into the HTML `<head>` or `<body>` of your student portal or employee intranet:

```html
<!-- Include KaTeX for mathematical formulas -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.js"></script>

<!-- RagAi Universal Floating Chat Widget -->
<script 
  src="http://localhost:8000/static/ragai_chat_widget.js"
  data-api-base="http://localhost:8000"
  data-api-key="ragai_student_default"
  data-role="employee"
  data-department="Human Resources"
  data-title="Staff HR Assistant"
  defer>
</script>
```

### Method B: React / Next.js Custom Hook & Component
Import the pre-built `useRagAiChat` hook and `RagAiChatModal` component from `examples/react_integration.tsx`:

```tsx
import React from 'react';
import { useRagAiChat, RagAiChatModal } from './ragai_integration';

export function UniversityPortal() {
  const chat = useRagAiChat({
    apiBase: "http://localhost:8000",
    apiKey: "ragai_student_default",
    role: "student",
    department: "Computer Science",
    course: "Operating Systems"
  });

  return (
    <div>
      <h1>Student Dashboard</h1>
      <button onClick={chat.openModal}>Ask AI Tutor</button>
      <RagAiChatModal chat={chat} />
    </div>
  );
}
```

### Method C: Server-to-Server Backend Integration (Python SDK)
Use the official typed Python SDK (`scripts/ragai_client.py`):

```python
from ragai_client import RagAiClient

# Initialize client with role credentials
client = RagAiClient(
    base_url="http://localhost:8000",
    api_key="ragai_employee_key"
)

# Ask an HR policy question for university employees
response = client.ask(
    query="What is the procedure and entitlement for earned leave for non-teaching staff?",
    department="Human Resources",
    role="employee"
)

print("AI Answer:", response["answer"])
print("Verified Citations:", response["citations"])
print("Confidence:", response["confidence_score"])
```

---

## 4. API Specification & Request/Response Contracts

### 4.1 Ask Question Endpoint (`POST /api/v1/ask`)

The primary conversational RAG endpoint for students, staff, and faculty.

#### Headers:
```http
Content-Type: application/json
X-API-Key: <your_api_key>
```

#### Request Payload Schema:
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `query` | string | **Yes** | — | The natural language question (max 2,000 chars). |
| `department`| string | No | `null` | Department filter tag (e.g. `'Computer Science'`, `'Human Resources'`, `'Finance'`). |
| `course` | string | No | `null` | Course or topic filter (e.g. `'Operating Systems'`, `'Leave Rules 2026'`). |
| `role` | string | No | `'general'`| Caller persona context: `'student'`, `'employee'`, `'faculty'`, `'admin'`. |
| `top_k` | integer| No | `5` | Number of high-similarity document passages to retrieve (1–20). |
| `temperature`| float | No | `0.20` | Sampling temperature (0.00 = strict factual, 1.00 = creative). |
| `session_id`| string | No | `null` | Conversational session token to maintain multi-turn history. |

#### Example Request:
```json
{
  "query": "What are the rules regarding maternity leave for permanent university employees?",
  "department": "Human Resources",
  "role": "employee",
  "top_k": 5,
  "temperature": 0.15
}
```

#### Example Response:
```json
{
  "answer": "According to the University Employee Service Rules (Chapter IV, Section 12), permanent female employees are entitled to maternity leave for up to 180 days with full pay. The application must be supported by a certified medical certificate.",
  "citations": [
    {
      "document_name": "Employee_Service_Rules_2026.pdf",
      "page_number": 48,
      "similarity_score": 0.961,
      "chunk_id": "chunk_hr_rules_48_2",
      "snippet": "Section 12: Maternity leave may be granted to a female university employee for a period of up to 180 days..."
    }
  ],
  "confidence_score": 0.961,
  "session_id": "sess_employee_94821a",
  "crag_fallback_triggered": false
}
```

---

### 4.2 User Feedback Endpoint (`POST /api/v1/feedback`)

Captures reinforcement signals from end-users to drive Corrective RAG (CRAG) self-improvement.

#### Request Payload:
```json
{
  "query_id": "sess_employee_94821a",
  "feedback": "up",
  "reason": null
}
```
*For negative feedback (`"feedback": "down"`), pass an optional string reason (e.g. `'Outdated rule reference'`, `'Missing page citation'`).*

---

### 4.3 Cognitive Brain Cortex & Synapse Probing

Allows administrators and diagnostic portals to interrogate the conceptual understanding and semantic graph of the organization.

- **Knowledge Graph Endpoint:** `GET /api/v1/admin/brain/graph` *(Alias: `GET /api/v1/brain/cortex`)*
- **Synapse Probing Endpoint:** `POST /api/v1/admin/brain/fire-synapse` *(Alias: `POST /api/v1/brain/fire`)*

> [!NOTE]
> Brain Cortex inspection requires administrative authorization. Pass an admin API key (e.g. `X-API-Key: ragai_master_admin_key`) in request headers.

#### Interrogating Cognitive Activation:
```http
POST /api/v1/admin/brain/fire-synapse
Content-Type: application/json
X-API-Key: ragai_master_admin_key

{"query": "Holiday calendar and leave guidelines"}
```
Returns:
- `activated_nodes`: List of concept and document IDs stimulated by the query.
- `synaptic_pulses`: Array of directional energy pulses between connected concepts.
- `thought_pathway`: 4-phase reasoning breakdown (Perceptual Encoding, Associative Spreading, Context Synthesis, Executive Decision).

---

## 5. Multi-Persona Role Scoping Matrix

When integrating RagAi into your portals, configure the appropriate role and department headers:

| Persona / Portal | Role Tag | Default Department Scope | Target Ingested Materials | Typical Queries |
| :--- | :--- | :--- | :--- | :--- |
| **Student Portal** | `student` | Selected by student (e.g. *Computer Science*) | Syllabi, lecture notes, date sheets, exam schemes | *"When is the Data Structures practical viva?"* |
| **Employee Intranet** | `employee` | Institutional Administration / HR | Service books, leave rules, pension circulars, medical benefits | *"How do I claim medical reimbursement for OPD visits?"* |
| **Faculty Portal** | `faculty` | Department or Academic Council | Board of Studies minutes, research grants, grade submission portals | *"What is the deadline for submitting internal assessment marks?"* |
| **Administrative Staff**| `admin` | All Departments | Financial rules, store purchase guidelines, university statutory acts | *"What is the threshold for single-source procurement tenders?"* |
| **Admissions / Public** | `guest` | General Public & Registrar | Admission prospectuses, eligibility criteria, fee schedules | *"What is the minimum eligibility for M.Tech Computer Science?"* |

---

## 6. UI & Frontend Rendering Best Practices

To deliver an optimal user experience in external chat portals, adhere to these rendering standards:

1. **LaTeX Mathematical Formula Rendering:**
   - Detect inline math `$formula$` and block math `$$formula$$`.
   - Render via KaTeX (`renderMathInElement`) to ensure fraction lines, square roots, and integrals display cleanly.

2. **Source Citation Badges:**
   - Display citations as compact pill badges underneath the assistant's response.
   - Show: `📄 Document Name (Page X, Match %)`
   - On click, expand a drawer displaying the verbatim text snippet to ensure factual transparency.

3. **Code Syntax Highlighting & Copy Button:**
   - Wrap code snippets in styled `<pre><code>` containers with language tags.
   - Include a one-click copy button that copies the clean code to clipboard.

4. **Handling Rate Limits Gracefully:**
   - If HTTP 429 is encountered, parse the `Retry-After` response header and display a friendly countdown timer to the user.

---

## 7. Troubleshooting Integration Issues

| Symptom | Cause | Resolution |
| :--- | :--- | :--- |
| **HTTP 401 Unauthorized** | Missing or incorrect `X-API-Key` header. | Verify the key against Tab 5 of the Admin Hub (`/admin`). Ensure header name is exactly `X-API-Key`. |
| **HTTP 403 Forbidden** | The API key's role lacks permissions for the target endpoint. | Use a key with role `admin` for brain rebuilds or scraper controls; use `student`/`employee` for `/ask`. |
| **CORS Origin Blocked** | The external portal's domain is not in the FastAPI CORS whitelist. | In `api/main.py`, ensure `CORSMiddleware` includes your portal's URL in `allow_origins` or `["*"]`. |
| **Low Confidence Fallback** | RagAi returns a cautionary answer with `crag_fallback_triggered: true`. | The query was not found in the indexed documents. Upload the relevant circular or course PDF in Tab 1 or Tab 7. |
| **KaTeX Math Not Rendering** | Math delimiters unescaped or KaTeX script omitted. | Include KaTeX CSS and JS in your portal's HTML header. |

---

*This skill is maintained as part of the RagAi universal on-premise AI platform.*
