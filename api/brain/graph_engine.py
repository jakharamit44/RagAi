import re
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from sqlalchemy import select

from db.session import async_session_factory
from db.models import Document, Chunk, WebScrapeManifest

logger = logging.getLogger("api.brain.graph_engine")

# Academic topic patterns for automatic concept mining from chunks & documents
ACADEMIC_CONCEPT_PATTERNS = [
    (r"(?i)\b(dynamic programming|greedy algorithm|divide and conquer|backtracking)\b", "Dynamic Programming & Optimization"),
    (r"(?i)\b(graph algorithm|shortest path|dijkstra|minimum spanning tree|bfs|dfs|network flow)\b", "Graph Theory & Network Flow"),
    (r"(?i)\b(np-complete|p vs np|computational complexity|turing machine|reduction)\b", "Complexity Theory & NP-Completeness"),
    (r"(?i)\b(distributed systems|consensus|paxos|raft|fault tolerance|byzantine)\b", "Distributed Consensus & Fault Tolerance"),
    (r"(?i)\b(relational calculus|normalization|acid|b-tree|query optimization)\b", "Database Architecture & Relational Theory"),
    (r"(?i)\b(practical exam|datesheet|examination schedule|examination branch|centre of exam)\b", "Examination Schedules & Practical Datesheets"),
    (r"(?i)\b(academic council|curriculum framework|ordinance|scheme of examination|semester system)\b", "Academic Council Resolutions & Ordinances"),
    (r"(?i)\b(nep 2020|national education policy|credit framework|choice based credit)\b", "NEP 2020 Curricular Framework"),
    (r"(?i)\b(phd course work|doctoral research|research methodology|dissertation)\b", "Doctoral Research & Ph.D Regulations"),
    (r"(?i)\b(court meeting|statute|university governance|executive council)\b", "University Court Statutory Proceedings"),
    (r"(?i)\b(machine learning|neural network|deep learning|gradient descent)\b", "Neural Computing & Machine Learning"),
    (r"(?i)\b(cryptography|security|authentication|rsa|sha-256|encryption)\b", "Information Security & Cryptographic Systems"),
]

DEPARTMENT_COLOR_MAP = {
    "MDU Rohtak": "#f59e0b",           # Gold
    "Computer Science": "#4f46e5",     # Indigo
    "ComputerScience": "#4f46e5",
    "Examination Branch": "#ef4444",   # Rose
    "Academic Council": "#06b6d4",     # Cyan
    "University Court": "#8b5cf6",     # Purple
    "Physical Sciences": "#10b981",    # Emerald
    "General": "#64748b",              # Slate
}

NODE_TYPE_CONFIG = {
    "core": {"size": 38, "color": "#f59e0b", "shape": "diamond"},
    "department": {"size": 26, "color": "#4f46e5", "shape": "hexagon"},
    "course": {"size": 20, "color": "#10b981", "shape": "circle"},
    "concept": {"size": 15, "color": "#8b5cf6", "shape": "circle"},
    "document": {"size": 12, "color": "#06b6d4", "shape": "rect"},
    "web_notice": {"size": 13, "color": "#f97316", "shape": "rect"},
}


class BrainGraphEngine:
    """
    Constructs, maintains, and caches the multi-tiered University Knowledge Cortex.
    Extracts semantic concepts, curriculum modules, and cross-synaptic relationships.
    """

    def __init__(self):
        self._cached_graph: Optional[Dict[str, Any]] = None
        self._last_build_time: float = 0.0
        self._cache_ttl_seconds: float = 900.0  # 15 minutes
        self._lock = asyncio.Lock()

    def invalidate_cache(self):
        """Forces recalculation of the knowledge graph on next query."""
        self._cached_graph = None
        self._last_build_time = 0.0
        logger.info("Cognitive Brain Graph cache invalidated.")

    async def get_graph(self, department: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves the Knowledge Graph. Automatically builds or refreshes if cache is expired.
        Applies optional department-focused filtering.
        Thread-safe and protected against cache stampedes using double-checked locking.
        """
        now = time.time()
        if not self._cached_graph or (now - self._last_build_time) > self._cache_ttl_seconds:
            async with self._lock:
                if not self._cached_graph or (time.time() - self._last_build_time) > self._cache_ttl_seconds:
                    self._cached_graph = await self._build_full_graph()
                    self._last_build_time = time.time()

        if not department or department.lower() in ("all", "*", "any"):
            return self._cached_graph

        return self._filter_by_department(self._cached_graph, department)

    async def _build_full_graph(self) -> Dict[str, Any]:
        """
        Scans SQLite metadata and synthesizes the Knowledge Graph.
        """
        logger.info("Synthesizing University Knowledge Cortex from persistent records...")
        t0 = time.time()

        nodes: List[Dict[str, Any]] = []
        links: List[Dict[str, Any]] = []
        node_ids: Set[str] = set()

        def add_node(
            n_id: str,
            label: str,
            n_type: str,
            department: str = "General",
            custom_size: Optional[int] = None,
            meta: Optional[Dict[str, Any]] = None
        ):
            if n_id not in node_ids:
                node_ids.add(n_id)
                cfg = NODE_TYPE_CONFIG.get(n_type, {"size": 12, "color": "#64748b", "shape": "circle"})
                color = DEPARTMENT_COLOR_MAP.get(department, cfg["color"])
                nodes.append({
                    "id": n_id,
                    "label": label,
                    "type": n_type,
                    "department": department,
                    "val": custom_size or cfg["size"],
                    "color": color,
                    "meta": meta or {}
                })

        def add_link(source: str, target: str, l_type: str = "relates_to", weight: float = 1.0):
            if source in node_ids and target in node_ids and source != target:
                links.append({
                    "source": source,
                    "target": target,
                    "type": l_type,
                    "weight": round(weight, 2)
                })

        # 1. Central Core Nucleus
        add_node(
            n_id="core-mdu",
            label="Maharshi Dayanand University Cognitive Core",
            n_type="core",
            department="MDU Rohtak",
            custom_size=40,
            meta={"description": "Central AI Knowledge Hub for MDU Rohtak academic programs and governance."}
        )

        async with async_session_factory() as session:
            docs = (await session.execute(select(Document))).scalars().all()
            scrapes = (await session.execute(select(WebScrapeManifest))).scalars().all()
            chunks = (await session.execute(select(Chunk).limit(400))).scalars().all()

        # 2. Level 2: Faculties & Departments
        known_depts = {
            "Computer Science": "Dept. of Computer Science & Engineering",
            "Examination Branch": "Controller of Examinations & Evaluation",
            "Academic Council": "Academic Council & Syllabus Committee",
            "University Court": "University Court & Executive Governance",
            "Physical Sciences": "Faculty of Physical Sciences",
            "General": "General University Administration"
        }

        # Normalize department names
        for doc in docs:
            raw_dept = doc.department or "General"
            if raw_dept in ("d:", "data", "None", ""):
                raw_dept = "General"
            if "computer" in raw_dept.lower():
                raw_dept = "Computer Science"
            if raw_dept not in known_depts:
                known_depts[raw_dept] = f"Department of {raw_dept}"

        for dept_key, dept_name in known_depts.items():
            dept_node_id = f"dept-{dept_key.replace(' ', '_')}"
            add_node(
                n_id=dept_node_id,
                label=dept_name,
                n_type="department",
                department=dept_key,
                custom_size=28,
                meta={"dept_key": dept_key}
            )
            add_link("core-mdu", dept_node_id, "governs", 1.0)

        # 3. Level 3: Academic Programs & Courses
        courses_map: Dict[str, str] = {
            "CS401": "Computer Science",
            "CS402": "Computer Science",
            "B.Tech": "Computer Science",
            "M.Sc": "Physical Sciences",
            "PhD_Work": "Academic Council",
            "Court_Resolutions": "University Court",
        }

        for doc in docs:
            c = doc.course
            raw_dept = doc.department or "General"
            if "computer" in raw_dept.lower():
                raw_dept = "Computer Science"
            elif raw_dept in ("d:", "data", "None", ""):
                raw_dept = "General"

            if c and c not in courses_map:
                courses_map[c] = raw_dept

        for c_code, c_dept in courses_map.items():
            c_node_id = f"course-{c_code}"
            label_name = f"Course {c_code}"
            if c_code == "CS401":
                label_name = "CS401: Advanced Data Structures & Algorithms"
            elif c_code == "CS402":
                label_name = "CS402: Distributed Systems & Cloud"
            elif c_code == "B.Tech":
                label_name = "B.Tech Engineering Program"
            elif c_code == "M.Sc":
                label_name = "NEP Master of Science (M.Sc)"
            elif c_code == "PhD_Work":
                label_name = "Ph.D Course Work & Research"
            elif c_code == "Court_Resolutions":
                label_name = "Court Meeting Statutes & Resolutions"

            add_node(
                n_id=c_node_id,
                label=label_name,
                n_type="course",
                department=c_dept,
                custom_size=22,
                meta={"course_code": c_code}
            )
            parent_dept_id = f"dept-{c_dept.replace(' ', '_')}"
            if parent_dept_id in node_ids:
                add_link(parent_dept_id, c_node_id, "offers", 0.95)

        # 4. Level 4: Academic Topics & Concepts (Mined from chunks & syllabi)
        concept_occurrences: Dict[str, Set[str]] = {}
        for chunk in chunks:
            chunk_text = (chunk.text or "") + " " + (chunk.section or "")
            for pattern, concept_label in ACADEMIC_CONCEPT_PATTERNS:
                if re.search(pattern, chunk_text):
                    if concept_label not in concept_occurrences:
                        concept_occurrences[concept_label] = set()
                    concept_occurrences[concept_label].add(str(chunk.document_id))

        # Ensure essential university concepts are established
        base_concepts = [
            ("Dynamic Programming & Optimization", "CS401", "Computer Science"),
            ("Graph Theory & Network Flow", "CS401", "Computer Science"),
            ("Complexity Theory & NP-Completeness", "CS401", "Computer Science"),
            ("Distributed Consensus & Fault Tolerance", "CS402", "Computer Science"),
            ("Database Architecture & Relational Theory", "CS401", "Computer Science"),
            ("Examination Schedules & Practical Datesheets", "B.Tech", "Examination Branch"),
            ("Academic Council Resolutions & Ordinances", "Academic Council", "Academic Council"),
            ("NEP 2020 Curricular Framework", "M.Sc", "Academic Council"),
            ("Doctoral Research & Ph.D Regulations", "PhD_Work", "Academic Council"),
            ("University Court Statutory Proceedings", "Court_Resolutions", "University Court"),
        ]

        for concept_title, linked_course, concept_dept in base_concepts:
            concept_node_id = f"concept-{concept_title.lower().replace(' ', '_')[:30]}"
            doc_count = len(concept_occurrences.get(concept_title, set()))
            val_size = min(22, 14 + doc_count)
            add_node(
                n_id=concept_node_id,
                label=concept_title,
                n_type="concept",
                department=concept_dept,
                custom_size=val_size,
                meta={"citations_count": doc_count, "primary_course": linked_course}
            )

            # Link concept to associated course or department
            course_id = f"course-{linked_course}"
            if course_id in node_ids:
                add_link(course_id, concept_node_id, "covers_topic", 0.9)
            else:
                dept_id = f"dept-{concept_dept.replace(' ', '_')}"
                if dept_id in node_ids:
                    add_link(dept_id, concept_node_id, "regulates", 0.8)

        # 5. Level 5: Verified Documents
        for doc in docs:
            doc_id_short = str(doc.id)[:8]
            doc_node_id = f"doc-{doc_id_short}"
            raw_dept = doc.department or "General"
            if "computer" in raw_dept.lower():
                raw_dept = "Computer Science"
            elif raw_dept in ("d:", "data", "None", ""):
                raw_dept = "General"

            # Format human-readable title
            clean_title = doc.title
            if len(clean_title) > 38:
                clean_title = clean_title[:35] + "..."

            add_node(
                n_id=doc_node_id,
                label=clean_title,
                n_type="document",
                department=raw_dept,
                custom_size=12,
                meta={
                    "full_title": doc.title,
                    "doc_type": doc.doc_type,
                    "course": doc.course,
                    "source_path": doc.source_path,
                    "created_at": str(doc.created_at)
                }
            )

            # Link document to its course or department
            if doc.course and f"course-{doc.course}" in node_ids:
                add_link(f"course-{doc.course}", doc_node_id, "contains_doc", 0.85)
            else:
                dept_link_id = f"dept-{raw_dept.replace(' ', '_')}"
                if dept_link_id in node_ids:
                    add_link(dept_link_id, doc_node_id, "archives_doc", 0.75)

            # Link document to matching concepts
            doc_title_lower = doc.title.lower()
            if "court" in doc_title_lower:
                add_link(doc_node_id, "concept-university_court_statutory_p", "authoritative_source", 0.85)
            if "academic council" in doc_title_lower:
                add_link(doc_node_id, "concept-academic_council_resolutions", "authoritative_source", 0.85)
            if "schedule" in doc_title_lower or "datesheet" in doc_title_lower or "exam" in doc_title_lower:
                add_link(doc_node_id, "concept-examination_schedules_&_prac", "authoritative_source", 0.85)
            if "syllabus" in doc_title_lower:
                add_link(doc_node_id, "concept-dynamic_programming_&_optimi", "authoritative_source", 0.8)

        # 6. Level 6: Web Scraped Live Resources & Notices
        for scrape in scrapes:
            scrape_node_id = f"scrape-{scrape.id}"
            title_label = scrape.title or scrape.url
            if len(title_label) > 38:
                title_label = title_label[:35] + "..."

            add_node(
                n_id=scrape_node_id,
                label=f"Notice: {title_label}",
                n_type="web_notice",
                department="Examination Branch",
                custom_size=13,
                meta={
                    "url": scrape.url,
                    "title": scrape.title,
                    "content_type": scrape.content_type,
                    "status": scrape.status,
                    "last_checked": str(scrape.last_checked_at)
                }
            )
            add_link("dept-Examination_Branch", scrape_node_id, "broadcasts", 0.85)
            add_link(scrape_node_id, "concept-examination_schedules_&_prac", "updates_notice", 0.8)

        # 7. Cross-Synaptic Cognitive Affinities (Inter-departmental semantic bridges)
        synapses = [
            ("concept-dynamic_programming_&_optimi", "concept-graph_theory_&_network_flow", "algorithmic_affinity", 0.88),
            ("concept-dynamic_programming_&_optimi", "concept-complexity_theory_&_np-compl", "computational_boundary", 0.85),
            ("concept-distributed_consensus_&_fa", "concept-graph_theory_&_network_flow", "topology_mesh", 0.78),
            ("concept-examination_schedules_&_prac", "course-CS401", "evaluates_curriculum", 0.82),
            ("concept-examination_schedules_&_prac", "course-B.Tech", "schedules_evaluation", 0.92),
            ("concept-nep_2020_curricular_framework", "dept-Academic_Council", "statutory_compliance", 0.90),
            ("concept-university_court_statutory_p", "dept-Academic_Council", "governance_coordination", 0.86),
        ]
        for src, tgt, rel, w in synapses:
            add_link(src, tgt, rel, w)

        elapsed_ms = round((time.time() - t0) * 1000, 2)
        logger.info(f"Knowledge Cortex built: {len(nodes)} nodes, {len(links)} synapses in {elapsed_ms}ms.")

        result = {
            "status": "success",
            "nodes": nodes,
            "links": links,
            "stats": {
                "total_nodes": len(nodes),
                "total_links": len(links),
                "departments_count": len(known_depts),
                "courses_count": len(courses_map),
                "concepts_count": len(base_concepts),
                "documents_count": len(docs),
                "scraped_notices_count": len(scrapes),
                "build_latency_ms": elapsed_ms,
            }
        }
        return result

    def _filter_by_department(self, full_graph: Dict[str, Any], department: str) -> Dict[str, Any]:
        """Filters nodes and links to focus on a target department."""
        dept_clean = department.strip().lower()
        active_nodes = []
        active_node_ids = set()

        for n in full_graph["nodes"]:
            n_dept = n.get("department", "").lower()
            if n["type"] == "core" or dept_clean in n_dept or n_dept in dept_clean:
                active_nodes.append(n)
                active_node_ids.add(n["id"])

        active_links = []
        for l in full_graph["links"]:
            src = l["source"] if isinstance(l["source"], str) else l["source"].get("id")
            tgt = l["target"] if isinstance(l["target"], str) else l["target"].get("id")
            if src in active_node_ids and tgt in active_node_ids:
                active_links.append(l)

        return {
            "status": "success",
            "department": department,
            "nodes": active_nodes,
            "links": active_links,
            "stats": {
                "total_nodes": len(active_nodes),
                "total_links": len(active_links),
                "filtered": True
            }
        }


brain_graph_engine = BrainGraphEngine()
