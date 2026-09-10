# Multi-Persona Role & Permission Matrix

RagAi supports multiple distinct institutional and enterprise personas. Below is the operational matrix defining permissions, default scopes, and sample workflows.

| Role | Target Users | Allowed Endpoints | Rate Limit | Target Document Types | Primary Use Cases |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`student`** | Enrolled undergraduate and postgraduate students | `/api/v1/ask`, `/api/v1/feedback` | 60 req/min | Course textbooks, syllabi, lecture notes, date sheets, exam schemes | Clarifying textbook topics, checking exam dates, understanding assignment rules. |
| **`employee`** | Administrative staff, lab attendants, registrars, HR personnel | `/api/v1/ask`, `/api/v1/feedback` | 90 req/min | Service books, leave rules, medical policies, pension circulars, statutory acts | Verifying leave entitlement, medical claim reimbursement steps, payroll updates. |
| **`faculty`** | Professors, lecturers, researchers | `/api/v1/ask`, `/api/v1/feedback` | 120 req/min | Curriculum guidelines, Academic Council minutes, research grant circulars | Verifying syllabus changes, finding research grant deadlines, checking examination duty rosters. |
| **`admin`** | System administrators, university IT officers | Full API access including `/brain/*`, `/admin/*` | Unlimited | All institutional databases, logs, configurations | Rebuilding cortex, monitoring GPU VRAM, managing API keys, configuring web scrapers. |
| **`guest`** | External visitors, prospective students, parents | `/api/v1/ask` (strict top_k=3) | 20 req/min | Public prospectuses, admission notifications, fee circulars | Checking admission cutoffs, hostel facilities, campus directions, program fees. |
