"""
Self-Improving RAG Prompt Optimization Engine
Inspired by Shubhamsaboo/awesome-llm-apps (Self-Improving Agent Skills)
Implements Karpathy's autoresearch optimization loop for RAG prompts:
1. Harvest: Gathers failed queries, low-confidence responses, and evaluation test cases.
2. Analyst: Diagnoses failure patterns (missing constraint, ambiguity, hallucination risk).
3. Mutator: Applies exactly ONE targeted prompt mutation.
4. Evaluator: Re-scores the modified prompt against benchmark scenarios.
5. Decision Gate: Commits if performance improves/holds; rolls back if it regresses.
"""

import os
import json
import time
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "system_prompt_rules.json")

DEFAULT_SYSTEM_RULES = [
    "Base your factual academic answers ONLY on the verified context below. Do not hallucinate or invent facts.",
    "TEMPORAL & RECENCY AWARENESS: Use the provided current date to evaluate current academic status, upcoming vs past events, and whether deadlines have passed or been extended. When multiple notices exist, prioritize the latest extension notices, updated circulars, and current session guidelines.",
    "LANGUAGE ADAPTATION (CRITICAL FOR INDIA & MDU ROHTAK): Always match the language or dialect used by the student. If the user asks in Hindi (Devanagari script), reply in clear, polite Hindi. If the user asks in Hinglish (Hindi written in Roman script, e.g. 'admission kaise karein', 'exam kab hai', 'datesheet kahan milegi'), reply in natural, polite Hinglish or Hindi. If the user asks in English, reply in English. Keep degree names, course codes, and web portals clear and recognizable (e.g. MDU Rohtak, B.Tech, MCA, www.mdu.ac.in).",
    "If the user greets you or includes conversational courtesies in English, Hindi, or Hinglish (e.g. 'hi', 'namaste', 'kaise ho', 'how are you'), respond warmly and politely as the official AI Academic Assistant for Maharshi Dayanand University (MDU), Rohtak in that language.",
    "If the user asks who you are or who developed you in English, Hindi, or Hinglish (e.g. 'who are you', 'tum kon ho', 'aap kaun ho'), clearly identify yourself as the official AI Academic Assistant developed for Maharshi Dayanand University (MDU), Rohtak in the matching language.",
    "State key academic facts directly and clearly (dates, meeting numbers, course codes, exam schedules, rules).",
    "Do NOT include bracketed source tags, citation numbers, or markdown links like '[Source 1]', '[Source 1](...)', or '(Page X)' in your response text. Source citations and document badges are already displayed automatically by the user interface below your answer.",
    "If the context does not contain sufficient information to answer an academic question, state politely in the user's language:\n- English: 'I do not have sufficient verified course material to answer this question. Please refer to your faculty or syllabus.'\n- Hindi / Hinglish: 'मेरे पास इस प्रश्न का उत्तर देने के लिए पर्याप्त सत्यापित विश्वविद्यालय सामग्री उपलब्ध नहीं है। कृपया अपने संबंधित विभाग, संकाय (Faculty) या सिलेबस का संदर्भ लें।'",
    "Never mention internal software development plans, requirements planning, document ingestion pipelines, administrative dashboards, or technical code to the user. You are an academic assistant communicating with university students.",
    "When asked about university admissions, summarize the verified guidelines, programs, submission deadlines, and official portal (www.mdu.ac.in) found in the documents.",
    "Provide a complete, fully formed answer. Always finish your thoughts, sentences, and lists cleanly without cutting off abruptly."
]

class PromptRuleManager:
    """Manages active system prompt rules with persistence, versioning, and rollback."""

    @staticmethod
    def get_rules() -> List[str]:
        if os.path.exists(RULES_FILE):
            try:
                with open(RULES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                logger.warning(f"Failed to read prompt rules from {RULES_FILE}: {e}")
        return list(DEFAULT_SYSTEM_RULES)

    @staticmethod
    def save_rules(rules: List[str]):
        from api.core.content_guard import inspect_content_safety
        # Strict AI Safety Governor: filter out any toxic, adversarial, or prohibited rules
        sanitized_rules = []
        for r in rules:
            if not r or not isinstance(r, str):
                continue
            safety = inspect_content_safety(r, context="prompt_rule")
            if safety.is_safe:
                sanitized_rules.append(r)
            else:
                logger.warning(f"Rejected unsafe prompt rule during save: [{safety.category}] {r[:100]}")

        os.makedirs(os.path.dirname(RULES_FILE), exist_ok=True)
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(sanitized_rules, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(sanitized_rules)} verified safe prompt rules to {RULES_FILE}")

    @staticmethod
    def reset_to_defaults():
        PromptRuleManager.save_rules(DEFAULT_SYSTEM_RULES)


class SelfImprovingRAGEngine:
    """
    Autonomous prompt optimization loop.
    Executes benchmark evaluations, identifies weaknesses, applies surgical mutations,
    and guarantees regression-free prompt evolution.
    """

    # Standard evaluation questions used to benchmark prompt changes
    EVAL_SUITE = [
        {
            "query": "What is the university admission process and key requirements?",
            "must_contain": ["eligibility", "application", "mdu"],
            "must_not_contain": ["requirements planning", "ingestion pipeline"],
            "category": "Admissions"
        },
        {
            "query": "When is the B.Tech 4th semester mathematics exam?",
            "must_contain": ["mathematics", "june", "4"],
            "must_not_contain": [],
            "category": "Datesheet"
        },
        {
            "query": "What is the secret recipe for the dining hall pasta sauce?",
            "must_contain": ["not have", "sufficient", "refer"],
            "must_not_contain": ["garlic", "oregano", "olive oil"],
            "category": "Abstention"
        }
    ]

    async def run_optimization_cycle(
        self,
        strategy: Optional[str] = "add_constraint",
        suggested_rule: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs one full Karpathy optimization round:
        1. Measure baseline evaluation score with current active prompt.
        2. Mutator applies candidate rule.
        3. Measure new evaluation score.
        4. If new_score >= baseline_score: KEEP and persist.
        5. If new_score < baseline_score: ROLLBACK immediately.
        6. Persist run record to SQLite prompt_optimization_runs.
        """
        from db.session import async_session_factory
        from db.models import PromptOptimizationRun

        original_rules = PromptRuleManager.get_rules()
        logger.info(f"Self-Improvement: Starting optimization cycle with {len(original_rules)} baseline rules.")

        # Step 0: Pre-flight AI Safety Governor check for suggested candidate rules
        if suggested_rule:
            candidate_rule = suggested_rule.strip()
            from api.core.content_guard import inspect_content_safety
            safety = inspect_content_safety(candidate_rule, context="prompt_rule")
            if not safety.is_safe:
                logger.warning(f"Self-Improvement: Suggested rule rejected by AI Safety Governor [{safety.category}]: {candidate_rule}")
                return {
                    "status": "REJECTED_UNSAFE",
                    "reason": f"Rule violates AI safety and content policy ({safety.category}).",
                    "baseline_score": 0.0,
                    "new_score": 0.0,
                    "mutation_applied": None,
                    "total_active_rules": len(original_rules),
                    "evaluation_details": []
                }
        else:
            candidate_rule = None

        # Step 1: Evaluate baseline
        baseline_score, baseline_details = await self._evaluate_rules(original_rules)
        logger.info(f"Self-Improvement: Baseline score = {baseline_score:.2f}%")

        # Step 2: Mutator generates mutation if not provided
        if not candidate_rule:
            if strategy == "add_constraint":
                candidate_rule = "For examination schedule queries, explicitly state that students must bring their official admit card and verify examination center timings."
            elif strategy == "add_example":
                candidate_rule = "When providing admission requirements, organize qualifications into clear bulleted points for readability."
            else:
                candidate_rule = "Always maintain an encouraging, academic tone suited for higher education scholars."

        # Step 3: Apply mutation temporarily
        mutated_rules = list(original_rules)
        if candidate_rule not in mutated_rules:
            mutated_rules.append(candidate_rule)

        # Step 4: Evaluate mutated prompt
        new_score, new_details = await self._evaluate_rules(mutated_rules)
        logger.info(f"Self-Improvement: Mutated score = {new_score:.2f}% (Baseline was {baseline_score:.2f}%)")

        # Step 5: Acceptance / Rollback Gate
        if new_score >= baseline_score:
            status = "ACCEPTED"
            PromptRuleManager.save_rules(mutated_rules)
            logger.info("Self-Improvement: Mutation ACCEPTED and persisted.")
        else:
            status = "ROLLED_BACK"
            PromptRuleManager.save_rules(original_rules)
            logger.info("Self-Improvement: Mutation ROLLED_BACK due to score regression.")

        # Step 6: Log run to database
        run_record = {
            "timestamp": datetime.utcnow(),
            "baseline_score": baseline_score,
            "new_score": new_score,
            "mutation_strategy": strategy or "custom",
            "mutation_applied": candidate_rule,
            "status": status,
            "diagnostics": json.dumps({
                "baseline_details": baseline_details,
                "new_details": new_details,
                "total_rules": len(mutated_rules) if status == "ACCEPTED" else len(original_rules)
            })
        }

        try:
            async with async_session_factory() as session:
                entry = PromptOptimizationRun(**run_record)
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not record prompt optimization run in database: {e}")

        return {
            "status": status,
            "baseline_score": round(baseline_score, 2),
            "new_score": round(new_score, 2),
            "mutation_applied": candidate_rule,
            "total_active_rules": len(PromptRuleManager.get_rules()),
            "evaluation_details": new_details
        }

    async def _evaluate_rules(self, rules: List[str]) -> Tuple[float, List[Dict[str, Any]]]:
        """Runs evaluation suite against rule set and computes percentage score."""
        from api.rag.retriever import retriever
        from api.core.llm_router import llm_router

        passed = 0
        total = len(self.EVAL_SUITE)
        details = []

        cur_date_str = datetime.now().strftime("%A, %B %d, %Y")
        rules_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(rules)])
        system_instruction = (
            f"You are the official AI Academic Assistant for Maharshi Dayanand University (MDU), Rohtak.\n\n"
            f"RULES YOU MUST FOLLOW STRICTLY:\n{rules_text}"
        )

        for case in self.EVAL_SUITE:
            q = case["query"]
            chunks = await retriever.retrieve(q)

            context_block = "\n\n".join([c.get("text", "") for c in chunks[:3]])
            user_content = f"<context>\n{context_block}\n</context>\n\nQuestion: {q}\n\nAnswer:"
            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ]

            try:
                # Fast evaluation via llm_router
                res = await llm_router.generate_response(messages=messages, temperature=0.1)
                ans = res.get("choices", [{}])[0].get("message", {}).get("content", "").lower()

                has_must = all(m in ans for m in case["must_contain"])
                has_forbidden = any(f in ans for f in case["must_not_contain"])

                if has_must and not has_forbidden:
                    passed += 1
                    status = "PASS"
                else:
                    status = "FAIL"

                details.append({
                    "query": q,
                    "status": status,
                    "matched_keywords": [m for m in case["must_contain"] if m in ans],
                    "forbidden_keywords": [f for f in case["must_not_contain"] if f in ans]
                })
            except Exception as e:
                details.append({"query": q, "status": "ERROR", "error": str(e)})

        score_pct = (passed / total) * 100.0 if total > 0 else 0.0
        return score_pct, details

self_improver = SelfImprovingRAGEngine()
