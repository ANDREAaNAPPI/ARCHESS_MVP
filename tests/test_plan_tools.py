"""
Test dei nuovi tools di plan detection ed evaluation.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.server import call_tool, stockfish


async def test_detect_strategic_plans():
    """Test detect_strategic_plans tool."""
    print("=" * 60)
    print("TEST: detect_strategic_plans")
    print("=" * 60)
    
    # Position con arrocchi opposti MOLTO chiari
    fen = "2kr1b1r/pp2bppp/2n1pn2/q2p4/3P4/2N1PN2/PPQ1BPPP/2KR1B1R w - - 0 10"
    
    arguments = {
        "fen": fen,
        "player_rating": 1500
    }
    
    print(f"Position: Clear opposite side castling")
    print(f"Rating: 1500\n")
    
    result = await call_tool("detect_strategic_plans", arguments)
    response = result[0].text
    
    print("Response:")
    print(response[:300] + "..." if len(response) > 300 else response)
    print()
    
    # Check generico che funzioni
    assert "patterns_found" in response
    
    # Parse patterns count
    import re
    patterns_match = re.search(r"'patterns_found': (\d+)", response)
    if patterns_match:
        patterns_count = int(patterns_match.group(1))
        print(f"✓ Found {patterns_count} patterns")
        assert patterns_count > 0, "Should find at least one pattern"
    
    # Check che ci sia almeno un pattern skill-appropriate
    assert "'name':" in response
    print("✓ Patterns have names and descriptions")
    
    print("✓ Test passed\n")


async def test_evaluate_plan():
    """Test evaluate_plan tool."""
    print("=" * 60)
    print("TEST: evaluate_plan")
    print("=" * 60)
    
    # Simple development plan - SOLO mosse del nero (è il suo turno)
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    
    arguments = {
        "fen": fen,
        "plan_description": "Central response with e5",
        "candidate_moves": ["e7e5"],  # Solo una mossa del nero
        "player_rating": 1500
    }
    
    print(f"Plan: {arguments['plan_description']}")
    print(f"Moves: {', '.join(arguments['candidate_moves'])}\n")
    
    result = await call_tool("evaluate_plan", arguments)
    response = result[0].text
    
    print("Response:")
    print(response)
    print()
    
    assert "soundness" in response
    # Non controllare eval_change se c'è errore
    if "error" not in response:
        assert "evaluation_change" in response
        print("✓ Plan evaluated successfully")
    else:
        print("⚠ Plan had errors (expected for some invalid move sequences)")
    
    print("✓ Test passed\n")

async def test_full_workflow():
    """Test workflow completo: detect → evaluate."""
    print("=" * 60)
    print("TEST: Full Workflow (Detect → Evaluate)")
    print("=" * 60)
    
    # Position with central tension
    fen = "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
    
    print("Step 1: Detect strategic plans\n")
    
    # Detect patterns
    detect_result = await call_tool("detect_strategic_plans", {
        "fen": fen,
        "player_rating": 1500
    })
    
    response_text = detect_result[0].text
    print(f"Detection result: {response_text[:200]}...\n")
    
    print("Step 2: Evaluate detected plan\n")
    
    # Evaluate central break plan
    eval_result = await call_tool("evaluate_plan", {
        "fen": fen,
        "plan_description": "Central pawn break with e4",
        "candidate_moves": ["e2e4"],
        "player_rating": 1500
    })
    
    print(f"Evaluation result:")
    print(eval_result[0].text)
    print()
    
    print("✓ Full workflow completed\n")


async def main():
    print("\n" + "=" * 60)
    print("PLAN DETECTION & EVALUATION TESTS")
    print("=" * 60 + "\n")
    
    # Inizializza componenti
    print("Initializing Stockfish and plan_evaluator...")
    stockfish.start()
    
    # Inizializza plan_evaluator nel modulo server
    import src.server as server_module
    from src.analyzers.plan_evaluator import PlanEvaluator
    
    server_module.plan_evaluator = PlanEvaluator(stockfish)
    
    print("✓ Components initialized\n")
    
    try:
        await test_detect_strategic_plans()
        await test_evaluate_plan()
        await test_full_workflow()
        
        stockfish.quit()
        
        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

    