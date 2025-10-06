"""
Test del tool analyze_game.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.server import call_tool, stockfish
import src.server as server_module
from src.analyzers.plan_evaluator import PlanEvaluator
from src.analyzers.game_analyzer import GameAnalyzer
from src.analyzers.plan_detector import PlanDetector


async def test_analyze_game_quick():
    """Test quick game analysis."""
    print("=" * 60)
    print("TEST: Analyze Game (Quick Scan)")
    print("=" * 60)
    
    # Sample game with a clear blunder
    pgn = """
[Event "Test Game"]
[White "Player"]
[Black "Opponent"]
[Result "0-1"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 
6. Nxf7 Kxf7 7. Qf3+ Ke6 8. Nc3 Nb4 9. a3 Nxc2+ 10. Kd1 Nxa1 0-1
"""
    
    arguments = {
        "pgn": pgn,
        "player_rating": 1500,
        "analyze_all_moves": False
    }
    
    print("Analyzing short tactical game...")
    print("(Quick scan mode)\n")
    
    result = await call_tool("analyze_game", arguments)
    response = result[0].text
    
    print("Analysis result:")
    print(response[:500] + "..." if len(response) > 500 else response)
    print()
    
    # Verify key elements in formatted output
    assert "GAME ANALYSIS REPORT" in response
    assert "STATISTICS" in response
    assert "CRITICAL MOMENTS" in response
    assert ("blunder" in response.lower() or 
            "mistake" in response.lower() or 
            "inaccuracy" in response.lower())
    
    print("✓ Test passed - formatted output verified\n")


async def test_analyze_game_thorough():
    """Test thorough game analysis (slower)."""
    print("=" * 60)
    print("TEST: Analyze Game (Thorough)")
    print("=" * 60)
    
    # Shorter game for thorough analysis
    pgn = """
[Event "Sample"]
[White "A"]
[Black "B"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 1-0
"""
    
    arguments = {
        "pgn": pgn,
        "player_rating": 1800,
        "analyze_all_moves": True  # Thorough analysis
    }
    
    print("Analyzing with thorough mode...")
    print("(This may take 5-10 seconds)\n")
    
    result = await call_tool("analyze_game", arguments)
    response = result[0].text
    
    print("Analysis result:")
    print(response[:500] + "..." if len(response) > 500 else response)
    print()
    
    # Verify formatted output
    assert "GAME ANALYSIS REPORT" in response
    assert "PHASE BREAKDOWN" in response
    assert "Total moves" in response
    
    print("✓ Test passed - thorough analysis complete\n")


async def main():
    print("\n" + "=" * 60)
    print("GAME ANALYSIS TESTS")
    print("=" * 60 + "\n")
    
    # Initialize components
    print("Initializing components...")
    stockfish.start()
    
    plan_detector = PlanDetector()
    server_module.plan_evaluator = PlanEvaluator(stockfish)
    server_module.game_analyzer = GameAnalyzer(stockfish, plan_detector)
    
    print("✓ Components initialized\n")
    
    try:
        await test_analyze_game_quick()
        await test_analyze_game_thorough()
        
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