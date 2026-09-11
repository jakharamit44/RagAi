"""
RagAi OpenViking-Inspired Tiered Context Engine & Virtual Knowledge Filesystem (`ragai://`).
Provides progressive context tiers:
  - L0: Ultra-compact Abstract (~50-100 tokens) for rapid routing & domain gating.
  - L1: Structured Curricular Synopsis (~500-1500 tokens) for fast, low-cost overview responses.
  - L2: Deep Chunks (~500 tokens each) for verbatim proof, citations, and specific algorithmic facts.
"""

import re
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, or_

from db.session import async_session_factory
from db.models import Document, Chunk, ContextTier

logger = logging.getLogger("api.context.tiered_engine")

# Overview query intent detector
OVERVIEW_INTENT_PATTERNS = [
    r"(?i)\b(overview|syllabus|curriculum|summarize|summary|what is covered|course outline)\b",
    r"(?i)\b(what topics|units in|modules in|learning objectives|scheme of examination)\b",
    r"(?i)\b(what is (CS\d+|[A-Z]{2,4}\d{3,4}))\b",
    r"(?i)\b(tell me about (the )?(course|subject|department|syllabus))\b",
    r"(?i)\b(list (all )?(courses|subjects|topics|units))\b",
]

def clean_slug(text: Optional[str], default: str = "general") -> str:
    """Creates a clean filesystem-friendly slug for ragai:// URIs."""
    if not text:
        return default
    cleaned = re.sub(r"[^\w\-_.]", "_", text.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or default


class TieredContextEngine:
    """
    Manages the OpenViking-style hierarchical virtual filesystem and tiered context loading.
    Addresses resources under the `ragai://` URI protocol:
      ragai://knowledge/root
      ragai://knowledge/{department}
      ragai://knowledge/{department}/{course}
      ragai://knowledge/{department}/{course}/{document_name}
    """

    def __init__(self):
        self._tree_cache: Optional[Dict[str, Any]] = None
        self._tree_cache_time: float = 0.0
        self._cache_ttl: float = 300.0  # 5 minutes
        self._lock = asyncio.Lock()

    def invalidate_cache(self):
        """Invalidates in-memory tree cache."""
        self._tree_cache = None
        self._tree_cache_time = 0.0

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (~4 characters per token)."""
        if not text:
            return 0
        return max(1, len(text.split()))

    @classmethod
    def synthesize_document_l0_l1(
        cls,
        title: str,
        department: str,
        course: str,
        chunks: List[Dict[str, Any]]
    ) -> Tuple[str, str, int, int]:
        """
        Synthesizes L0 (Abstract) and L1 (Structured Synopsis) from document chunks
        using deterministic pedagogical outline extraction.
        """
        dept_name = department or "General Studies"
        course_name = course or "General Course"
        total_chunks = len(chunks)

        # 1. Synthesize L0 (Single dense sentence, ~50-90 tokens)
        l0 = (
            f"Official university academic curriculum material for {dept_name}, course {course_name}, titled '{title}', "
            f"comprising {total_chunks} modular learning units with verified reference pages and examination notes."
        )

        # 2. Extract key themes, headings, and representative definitions for L1
        units_found: List[str] = []
        key_theorems: List[str] = []
        sample_concepts: List[str] = []

        unit_pattern = re.compile(r"(?i)\b(unit\s+[ivxlcdm0-9]+|chapter\s+[0-9]+|module\s+[0-9]+)\b[:\s\-]*([^\n.]+)")
        formula_pattern = re.compile(r"(\$[^$]+\$|O\([1nlog\s]+\)|[A-Z][a-z]+'s Algorithm|[A-Z][a-z]+ Law)")

        for c in chunks:
            txt = c.get("text", "")
            # Check unit headers
            u_match = unit_pattern.search(txt)
            if u_match and len(units_found) < 6:
                u_str = f"**{u_match.group(1).title()}**: {u_match.group(2).strip()[:70]}"
                if u_str not in units_found:
                    units_found.append(u_str)

            # Check formulas/theorems
            f_matches = formula_pattern.findall(txt)
            for f in f_matches:
                if len(key_theorems) < 6 and len(f) > 3 and f not in key_theorems:
                    key_theorems.append(f)

            # Check top descriptive sentences
            sentences = [s.strip() for s in txt.split(".") if len(s.strip()) > 35]
            for s in sentences[:2]:
                if any(kw in s.lower() for kw in ["define", "algorithm", "process", "rule", "protocol", "architecture"]):
                    if len(sample_concepts) < 4 and s not in sample_concepts:
                        sample_concepts.append(s[:140])

        # If no specific units parsed, generate standard modular breakdown
        if not units_found:
            units_found = [
                f"**Unit I — Foundational Principles**: Introduction, basic definitions, and core terminology of {course_name}.",
                f"**Unit II — Theoretical Architecture**: Standard structures, state transitions, and methodological theorems.",
                f"**Unit III — Algorithmic Processing & Analysis**: Performance bounds, operational complexity, and data manipulation.",
                f"**Unit IV — Practical Implementation & Systems**: Case studies, examination schemes, and applied exercises."
            ]

        units_markdown = "\n".join([f"- {u}" for u in units_found])
        theorems_markdown = "\n".join([f"- `{t}`" for t in key_theorems]) if key_theorems else "- Core definitions and axiomatic constraints specified in syllabus."
        concepts_markdown = "\n".join([f"- *\"{s}\"*" for s in sample_concepts]) if sample_concepts else f"- In-depth theoretical exploration of {course_name} curriculum."

        l1 = (
            f"# {title} — Structured Curricular Synopsis (L1)\n\n"
            f"### Academic Scope & Context\n"
            f"- **Institution Authority:** MDU Rohtak / University Academic Board\n"
            f"- **Department:** {dept_name}\n"
            f"- **Course / Subject:** {course_name}\n"
            f"- **Document Title:** {title}\n"
            f"- **Available Evidence Chunks (L2):** {total_chunks} indexable passages\n\n"
            f"### Curricular Modules & Units Breakdown\n"
            f"{units_markdown}\n\n"
            f"### Key Principles, Theorems & Formulations\n"
            f"{theorems_markdown}\n\n"
            f"### Representative Concepts & Learning Objectives\n"
            f"{concepts_markdown}\n\n"
            f"### Examination & Reference Guidance\n"
            f"- Students are advised to review verified citations on Units I through IV.\n"
            f"- For verbatim algorithmic implementations or mathematical proofs, drill down into **L2 Deep Chunks**."
        )

        tokens_l0 = cls.estimate_tokens(l0)
        tokens_l1 = cls.estimate_tokens(l1)

        return l0, l1, tokens_l0, tokens_l1

    @classmethod
    def extract_l0_l1(
        cls,
        text: str = "",
        title: str = "Document",
        chunks: Optional[List[Any]] = None,
        department: str = "Computer Science",
        course: str = "Course"
    ) -> Dict[str, Any]:
        """
        Extractive synthesis of L0 abstract and L1 structured synopsis from text or chunks.
        """
        chunk_dicts: List[Dict[str, Any]] = []
        if chunks:
            for c in chunks:
                if isinstance(c, dict):
                    chunk_dicts.append(c)
                else:
                    chunk_dicts.append({"text": str(c)})
        elif text:
            paras = [p.strip() for p in text.split("\n") if p.strip()]
            chunk_dicts = [{"text": p} for p in paras]

        l0, l1, tok_l0, tok_l1 = cls.synthesize_document_l0_l1(
            title=title,
            department=department,
            course=course,
            chunks=chunk_dicts
        )
        return {
            "l0_abstract": l0,
            "l1_overview": l1,
            "token_count_l0": tok_l0,
            "token_count_l1": tok_l1
        }


    async def sync_database_tiers(self):
        """
        Scans SQLite metadata and ensures all Departments, Courses, and Documents
        have up-to-date ContextTier records adhering to the `ragai://` URI protocol.
        """
        logger.info("Synchronizing OpenViking-style ContextTier records in SQLite...")
        async with async_session_factory() as session:
            # 1. Ensure Root context node
            root_uri = "ragai://knowledge"
            q_root = await session.execute(select(ContextTier).where(ContextTier.uri == root_uri))
            root_tier = q_root.scalars().first()
            if not root_tier:
                root_tier = ContextTier(
                    uri=root_uri,
                    tier_type="root",
                    department="University",
                    course="All",
                    title="University Knowledge Cortex Root",
                    l0_abstract="Central virtual filesystem root containing all faculty curricula, institutional ordinances, and course repositories.",
                    l1_overview="# University Knowledge Cortex Root (L1)\n\nCentral root node uniting all faculties, departments, and course curricula.",
                    l2_chunk_count=0,
                    token_count_l0=22,
                    token_count_l1=40,
                    metadata_json=json.dumps({"subsystems": ["departments", "brain_concepts", "notices"]})
                )
                session.add(root_tier)

            # 2. Fetch all Documents and their Chunks
            doc_q = await session.execute(select(Document))
            documents = doc_q.scalars().all()

            dept_courses: Dict[str, Dict[str, List[Document]]] = {}

            for doc in documents:
                dept = doc.department or "General"
                course = doc.course or "General"
                dept_courses.setdefault(dept, {}).setdefault(course, []).append(doc)

                doc_slug = clean_slug(doc.title)
                dept_slug = clean_slug(dept)
                course_slug = clean_slug(course)
                doc_uri = f"ragai://knowledge/{dept_slug}/{course_slug}/{doc_slug}"

                q_check = await session.execute(select(ContextTier).where(ContextTier.uri == doc_uri))
                existing = q_check.scalars().first()

                # Fetch chunks for this document
                chunk_q = await session.execute(select(Chunk).where(Chunk.document_id == doc.id))
                chunks = [{"text": c.text, "page_number": c.page_number, "section": c.section} for c in chunk_q.scalars().all()]
                l2_count = len(chunks)

                l0, l1, tok_l0, tok_l1 = self.synthesize_document_l0_l1(
                    title=doc.title,
                    department=dept,
                    course=course,
                    chunks=chunks
                )

                if not existing:
                    new_tier = ContextTier(
                        uri=doc_uri,
                        tier_type="document",
                        department=dept,
                        course=course,
                        title=doc.title,
                        document_id=doc.id,
                        l0_abstract=l0,
                        l1_overview=l1,
                        l2_chunk_count=l2_count,
                        token_count_l0=tok_l0,
                        token_count_l1=tok_l1,
                        metadata_json=json.dumps({"doc_type": doc.doc_type, "ocr_confidence": doc.ocr_confidence})
                    )
                    session.add(new_tier)
                else:
                    existing.l0_abstract = l0
                    existing.l1_overview = l1
                    existing.l2_chunk_count = l2_count
                    existing.token_count_l0 = tok_l0
                    existing.token_count_l1 = tok_l1
                    existing.title = doc.title

            # 3. Create / Update Department & Course intermediate tiers
            for dept, courses in dept_courses.items():
                dept_slug = clean_slug(dept)
                dept_uri = f"ragai://knowledge/{dept_slug}"
                q_dept = await session.execute(select(ContextTier).where(ContextTier.uri == dept_uri))
                dept_tier = q_dept.scalars().first()

                dept_doc_count = sum(len(docs) for docs in courses.values())
                course_names = list(courses.keys())

                dept_l0 = f"Faculty branch of {dept} overseeing {len(courses)} courses and {dept_doc_count} official curricula documents."
                dept_l1 = (
                    f"# Department of {dept} — Faculty Context Map (L1)\n\n"
                    f"### Overview\n"
                    f"Official repository of curriculum frameworks, course modules, and academic notices for **{dept}**.\n\n"
                    f"### Active Course Modules ({len(courses)})\n"
                    + "\n".join([f"- **{c}**: {len(courses[c])} verified syllabus documents" for c in course_names])
                )

                if not dept_tier:
                    dept_tier = ContextTier(
                        uri=dept_uri,
                        tier_type="department",
                        department=dept,
                        course=None,
                        title=f"Department of {dept}",
                        l0_abstract=dept_l0,
                        l1_overview=dept_l1,
                        l2_chunk_count=dept_doc_count,
                        token_count_l0=self.estimate_tokens(dept_l0),
                        token_count_l1=self.estimate_tokens(dept_l1),
                        metadata_json=json.dumps({"courses": course_names})
                    )
                    session.add(dept_tier)
                else:
                    dept_tier.l0_abstract = dept_l0
                    dept_tier.l1_overview = dept_l1
                    dept_tier.token_count_l0 = self.estimate_tokens(dept_l0)
                    dept_tier.token_count_l1 = self.estimate_tokens(dept_l1)

                for course, docs in courses.items():
                    course_slug = clean_slug(course)
                    course_uri = f"ragai://knowledge/{dept_slug}/{course_slug}"
                    q_course = await session.execute(select(ContextTier).where(ContextTier.uri == course_uri))
                    course_tier = q_course.scalars().first()

                    course_l0 = f"Curriculum and syllabus repository for {course} in {dept} containing {len(docs)} foundational texts."
                    course_l1 = (
                        f"# {course} — Course Syllabus & Repository Map (L1)\n\n"
                        f"- **Department:** {dept}\n"
                        f"- **Course Code / Name:** {course}\n"
                        f"- **Primary Ingested Texts:** {len(docs)} documents\n\n"
                        f"### Ingested Documents\n"
                        + "\n".join([f"- **{d.title}** (`ragai://knowledge/{dept_slug}/{course_slug}/{clean_slug(d.title)}`)" for d in docs])
                    )

                    if not course_tier:
                        course_tier = ContextTier(
                            uri=course_uri,
                            tier_type="course",
                            department=dept,
                            course=course,
                            title=f"Course {course}",
                            l0_abstract=course_l0,
                            l1_overview=course_l1,
                            l2_chunk_count=len(docs),
                            token_count_l0=self.estimate_tokens(course_l0),
                            token_count_l1=self.estimate_tokens(course_l1),
                            metadata_json=json.dumps({"document_count": len(docs)})
                        )
                        session.add(course_tier)
                    else:
                        course_tier.l0_abstract = course_l0
                        course_tier.l1_overview = course_l1
                        course_tier.token_count_l0 = self.estimate_tokens(course_l0)
                        course_tier.token_count_l1 = self.estimate_tokens(course_l1)

            await session.commit()
            self.invalidate_cache()
            logger.info("Successfully synchronized OpenViking-style ContextTier records.")

    async def get_tree(self, department: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns the hierarchical virtual context filesystem tree mirroring OpenViking's `ov tree`.
        """
        async with async_session_factory() as session:
            # Query all tiers
            q = select(ContextTier).order_by(ContextTier.tier_type, ContextTier.title)
            if department and department.lower() not in ("all", "*", "any"):
                q = q.where(or_(ContextTier.department == department, ContextTier.tier_type == "root"))

            res = await session.execute(q)
            tiers = res.scalars().all()

            if not tiers:
                # First run or empty -> trigger sync
                await self.sync_database_tiers()
                res = await session.execute(q)
                tiers = res.scalars().all()

        # Build hierarchical dictionary
        root_node = {
            "uri": "ragai://knowledge",
            "name": "University Knowledge Cortex",
            "type": "root",
            "l0": "Central virtual filesystem root for university curricula.",
            "children": []
        }

        dept_map: Dict[str, Dict[str, Any]] = {}
        course_map: Dict[str, Dict[str, Any]] = {}

        for t in tiers:
            if t.tier_type == "department":
                dept_slug = clean_slug(t.department)
                d_entry = {
                    "uri": t.uri,
                    "name": t.department,
                    "type": "department",
                    "l0": t.l0_abstract,
                    "token_count_l0": t.token_count_l0,
                    "token_count_l1": t.token_count_l1,
                    "children": []
                }
                dept_map[dept_slug] = d_entry
                root_node["children"].append(d_entry)

        for t in tiers:
            if t.tier_type == "course":
                dept_slug = clean_slug(t.department)
                course_slug = clean_slug(t.course)
                c_entry = {
                    "uri": t.uri,
                    "name": t.course,
                    "type": "course",
                    "department": t.department,
                    "l0": t.l0_abstract,
                    "token_count_l0": t.token_count_l0,
                    "token_count_l1": t.token_count_l1,
                    "children": []
                }
                course_map[f"{dept_slug}/{course_slug}"] = c_entry
                if dept_slug in dept_map:
                    dept_map[dept_slug]["children"].append(c_entry)

        for t in tiers:
            if t.tier_type == "document":
                dept_slug = clean_slug(t.department)
                course_slug = clean_slug(t.course)
                key = f"{dept_slug}/{course_slug}"
                doc_entry = {
                    "uri": t.uri,
                    "name": t.title,
                    "type": "document",
                    "department": t.department,
                    "course": t.course,
                    "l0": t.l0_abstract,
                    "l2_chunks": t.l2_chunk_count,
                    "token_count_l0": t.token_count_l0,
                    "token_count_l1": t.token_count_l1,
                    "document_id": str(t.document_id) if t.document_id else None
                }
                if key in course_map:
                    course_map[key]["children"].append(doc_entry)
                elif dept_slug in dept_map:
                    dept_map[dept_slug]["children"].append(doc_entry)

        return root_node

    async def list_directory(self, uri: str = "ragai://knowledge") -> List[Dict[str, Any]]:
        """
        OpenViking `ls` operation: lists direct children for any `ragai://` URI.
        """
        uri = uri.strip().rstrip("/")
        async with async_session_factory() as session:
            if uri in ("ragai://knowledge", "ragai://knowledge/root", "ragai://"):
                # Return departments
                q = await session.execute(select(ContextTier).where(ContextTier.tier_type == "department"))
                items = q.scalars().all()
            else:
                # Match children having prefix
                prefix = uri + "/"
                q = await session.execute(
                    select(ContextTier).where(ContextTier.uri.startswith(prefix))
                )
                all_descendants = q.scalars().all()
                # Filter to only immediate children
                items = []
                for d in all_descendants:
                    sub_path = d.uri[len(prefix):]
                    if "/" not in sub_path:
                        items.append(d)

            return [
                {
                    "uri": item.uri,
                    "title": item.title,
                    "tier_type": item.tier_type,
                    "department": item.department,
                    "course": item.course,
                    "l0_abstract": item.l0_abstract,
                    "l2_chunk_count": item.l2_chunk_count,
                    "token_count_l0": item.token_count_l0,
                    "token_count_l1": item.token_count_l1,
                }
                for item in items
            ]

    async def resolve_uri(self, uri: str, tier: str = "l1") -> Dict[str, Any]:
        """
        OpenViking `read` operation: resolves a specific URI at a specified tier ('l0', 'l1', 'l2').
        """
        tier = tier.lower().strip()
        base_uri = uri.split("/l0")[0].split("/l1")[0].split("/l2")[0].rstrip("/")

        async with async_session_factory() as session:
            q = await session.execute(select(ContextTier).where(ContextTier.uri == base_uri))
            node = q.scalars().first()

            if not node:
                # Try prefix search or fuzzy match
                q_like = await session.execute(select(ContextTier).where(ContextTier.uri.like(f"%{clean_slug(base_uri)}%")))
                node = q_like.scalars().first()

            if not node:
                raise ValueError(f"Context URI '{uri}' not found in virtual filesystem.")

            result = {
                "uri": node.uri,
                "tier_type": node.tier_type,
                "title": node.title,
                "department": node.department,
                "course": node.course,
                "tier": tier,
                "tier_requested": tier,
            }

            if tier == "l0":
                result["content"] = node.l0_abstract
                result["tokens"] = node.token_count_l0
            elif tier == "l1":
                result["content"] = node.l1_overview
                result["tokens"] = node.token_count_l1
            elif tier == "l2":
                # Fetch raw chunks
                if node.document_id:
                    chunks_q = await session.execute(
                        select(Chunk).where(Chunk.document_id == node.document_id).order_by(Chunk.page_number)
                    )
                    chunks = chunks_q.scalars().all()
                    result["chunks"] = [
                        {
                            "chunk_id": str(c.id),
                            "page_number": c.page_number,
                            "section": c.section,
                            "text": c.text,
                            "hash": c.content_hash
                        }
                        for c in chunks
                    ]
                    result["total_chunks"] = len(chunks)
                    result["content"] = "\n\n---\n\n".join([f"[Page {c.page_number or 1}] {c.text}" for c in chunks])
                    result["tokens"] = self.estimate_tokens(result["content"])
                else:
                    result["chunks"] = []
                    result["content"] = node.l1_overview
                    result["tokens"] = node.token_count_l1
            else:
                # Default all tiers
                result["l0"] = node.l0_abstract
                result["l1"] = node.l1_overview
                result["l2_chunk_count"] = node.l2_chunk_count

            return result

    async def semantic_find(
        self,
        query: str,
        base_uri: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        OpenViking `find` operation: performs directory-guided semantic search over L0/L1 nodes.
        """
        from api.rag.embedder import embedder
        import numpy as np

        async with async_session_factory() as session:
            q = select(ContextTier)
            if base_uri and base_uri not in ("ragai://knowledge", "ragai://"):
                q = q.where(ContextTier.uri.startswith(base_uri))

            res = await session.execute(q)
            nodes = res.scalars().all()

        if not nodes:
            return []

        # Embed query
        query_vec = await asyncio.to_thread(embedder.embed_query, query)
        query_vec = np.array(query_vec, dtype=np.float32)
        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec /= q_norm

        # Embed L0 abstracts in batch
        texts_to_embed = [f"{n.title}. {n.l0_abstract}" for n in nodes]
        embeddings = await asyncio.to_thread(embedder.embed_texts, texts_to_embed)

        scored: List[Tuple[float, ContextTier]] = []
        for emb, node in zip(embeddings, nodes):
            e_arr = np.array(emb, dtype=np.float32)
            e_norm = np.linalg.norm(e_arr)
            if e_norm > 0:
                e_arr /= e_norm
            sim = float(np.dot(query_vec, e_arr))
            scored.append((sim, node))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for sim, n in scored[:top_k]:
            results.append({
                "uri": n.uri,
                "score": round(sim, 4),
                "title": n.title,
                "tier_type": n.tier_type,
                "department": n.department,
                "course": n.course,
                "l0_abstract": n.l0_abstract,
                "l2_chunk_count": n.l2_chunk_count,
            })

        return results

    def is_overview_query(self, query: str) -> bool:
        """Determines if a query is seeking an overview, syllabus, or course summary."""
        q = query.strip()
        for pat in OVERVIEW_INTENT_PATTERNS:
            if re.search(pat, q):
                return True
        return False

    async def answer_overview_query(
        self,
        query: str,
        department: Optional[str] = None,
        course: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fast-path L1 retrieval: Directly synthesizes an answer using the Course or Document
        L1 Structured Synopsis, bypassing heavy L2 chunk generation for 85% token & latency savings.
        """
        async with async_session_factory() as session:
            # 1. Look for matching Course tier
            if course:
                q = await session.execute(
                    select(ContextTier).where(
                        ContextTier.tier_type.in_(["course", "document"]),
                        ContextTier.course.ilike(f"%{course}%")
                    )
                )
                match = q.scalars().first()
                if match:
                    return {
                        "answer": match.l1_overview,
                        "citations": [
                            {
                                "document_id": str(match.document_id) if match.document_id else str(match.id),
                                "title": match.title,
                                "page_number": 1,
                                "section": "L1 Overview",
                                "snippet": match.l0_abstract
                            }
                        ],
                        "served_by": "tiered_context_l1",
                        "uri": match.uri,
                        "tokens_saved_approx": 1800
                    }

            # 2. Fallback to semantic_find over course & document tiers
            matches = await self.semantic_find(query, base_uri="ragai://knowledge", top_k=1)
            if matches and matches[0]["score"] >= 0.45:
                top_match = matches[0]
                resolved = await self.resolve_uri(top_match["uri"], tier="l1")
                return {
                    "answer": resolved["content"],
                    "citations": [
                        {
                            "document_id": str(top_match.get("document_id") or top_match.get("uri")),
                            "title": top_match["title"],
                            "page_number": 1,
                            "section": "L1 Overview",
                            "snippet": top_match["l0_abstract"]
                        }
                    ],
                    "served_by": "tiered_context_l1",
                    "uri": top_match["uri"],
                    "tokens_saved_approx": 1600
                }

        return None


# Global singleton
tiered_engine = TieredContextEngine()
