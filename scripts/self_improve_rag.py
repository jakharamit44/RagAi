"""
Standalone CLI Runner for Self-Improving RAG Prompt Optimization Loop
Inspired by Karpathy's autoresearch & Shubhamsaboo/awesome-llm-apps

Usage:
    python scripts/self_improve_rag.py [--strategy add_constraint|add_example|refine_rule] [--rule "Custom rule text"]
"""

import sys
import json
import asyncio
import argparse
from datetime import datetime

async def main():
    parser = argparse.ArgumentParser(description="Run autonomous self-improving prompt optimization loop.")
    parser.add_argument("--strategy", type=str, default="add_constraint", choices=["add_constraint", "add_example", "refine_rule"], help="Mutation strategy")
    parser.add_argument("--rule", type=str, default=None, help="Optional specific candidate rule text to evaluate")
    args = parser.parse_args()

    print("================================================================")
    print("   RagAi Self-Improving Prompt Auto-Optimization Engine")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Strategy:  {args.strategy}")
    print("================================================================\n")

    from api.rag.self_improver import self_improver, PromptRuleManager

    current_rules = PromptRuleManager.get_rules()
    print(f"[*] Current active prompt rules count: {len(current_rules)}")

    print("[*] Running optimization cycle: evaluating baseline -> applying mutation -> benchmarking...")
    result = await self_improver.run_optimization_cycle(
        strategy=args.strategy,
        suggested_rule=args.rule
    )

    print("\n----------------------------------------------------------------")
    print("   OPTIMIZATION RESULTS:")
    print("----------------------------------------------------------------")
    print(f"Status:            {result['status']}")
    print(f"Baseline Score:    {result['baseline_score']}%")
    print(f"New Score:         {result['new_score']}%")
    print(f"Mutation Applied:  \"{result['mutation_applied']}\"")
    print(f"Total Rules Now:   {result['total_active_rules']}")
    print("----------------------------------------------------------------")

    if result['status'] == "ACCEPTED":
        print("\n[SUCCESS] Candidate prompt mutation successfully verified and accepted!")
    else:
        print("\n[ROLLED_BACK] Candidate prompt mutation did not exceed baseline. Safely rolled back.")

if __name__ == "__main__":
    asyncio.run(main())
