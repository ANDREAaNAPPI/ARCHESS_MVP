"""
Test standalone dei tools MCP.
Simula chiamate che Claude farebbe al server.
"""
import sys
import os

# Aggiungi src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.stockfish_wrapper import StockfishWrapper
from src.server import (
    get_depth_for_rating,
    classify_move_quality,
    format_evaluation
)


def test_stockfish_integration():
    """Test integrazione base con Stockfish."""
    print("=" * 60)
    print("TEST 1: Stockfish Integration")
    print("=" * 60)
    
    sf = StockfishWrapper(default_depth=15)
    sf.start()
    
    assert sf.is_ready(), "Stockfish should be ready"
    print("✓ Stockfish started successfully")
    
    # Test analyze_position
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    result = sf.analyze_position(fen, depth=12)
    
    assert result["best_move"] is not None, "Should return a best move"
    assert "evaluation" in result, "Should return evaluation"
    print(f"✓ Position analyzed: best move = {result['best_move']}, eval = {result['evaluation']:.2f}")
    
    # Test evaluate_move
    eval_result = sf.evaluate_move(fen, "e7e5", depth=12)
    assert "eval_loss" in eval_result, "Should calculate eval loss"
    print(f"✓ Move evaluated: e7e5, eval loss = {eval_result['eval_loss']:.2f}")
    
    sf.quit()
    print("✓ Stockfish closed cleanly\n")


def test_skill_adaptation():
    """Test skill adaptation logic."""
    print("=" * 60)
    print("TEST 2: Skill Adaptation")
    print("=" * 60)
    
    ratings = [900, 1300, 1700, 2100, 2500]
    expected_depths = [12, 18, 18, 22, 25]
    
    for rating, expected in zip(ratings, expected_depths):
        depth = get_depth_for_rating(rating)
        assert depth == expected, f"Rating {rating} should get depth {expected}, got {depth}"
        print(f"✓ Rating {rating} → depth {depth}")
    
    print()


def test_move_classification():
    """Test move quality classification."""
    print("=" * 60)
    print("TEST 3: Move Classification")
    print("=" * 60)
    
    test_cases = [
        (0.0, "excellent"),
        (-0.05, "excellent"),
        (-0.15, "good"),
        (-0.5, "inaccuracy"),
        (-1.5, "mistake"),
        (-3.5, "blunder")
    ]
    
    for eval_loss, expected_quality in test_cases:
        quality = classify_move_quality(eval_loss)
        assert quality == expected_quality, f"Eval loss {eval_loss} should be {expected_quality}, got {quality}"
        print(f"✓ Eval loss {eval_loss:+.2f} → {quality}")
    
    print()


def test_full_analysis_workflow():
    """Test workflow completo: analizza posizione + valuta mosse."""
    print("=" * 60)
    print("TEST 4: Full Analysis Workflow")
    print("=" * 60)
    
    sf = StockfishWrapper(default_depth=15)
    sf.start()
    
    # Posizione dopo 1.e4 e5 2.Nf3
    fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
    player_rating = 1500
    
    print(f"Position: After 1.e4 e5 2.Nf3")
    print(f"Player rating: {player_rating}")
    
    # Step 1: Analyze position
    depth = get_depth_for_rating(player_rating)
    analysis = sf.analyze_position(fen, depth=depth)
    
    print(f"\nAnalysis (depth {depth}):")
    print(f"  Best move: {analysis['best_move']}")
    print(f"  Evaluation: {format_evaluation(analysis['evaluation'])}")
    print(f"  PV: {' '.join(analysis['pv'][:5])}")
    
    # Step 2: Evaluate different candidate moves
    candidate_moves = ["b8c6", "g8f6", "f8c5"]
    move_names = ["Nc6", "Nf6", "Bc5"]
    
    print(f"\nEvaluating candidate moves:")
    for move_uci, move_name in zip(candidate_moves, move_names):
        eval_result = sf.evaluate_move(fen, move_uci, depth=depth)
        quality = classify_move_quality(eval_result['eval_loss'])
        
        print(f"  {move_name}: {quality} (eval loss: {eval_result['eval_loss']:+.2f})")
    
    sf.quit()
    print("\n✓ Full workflow completed successfully\n")


def test_rating_boundaries():
    """Test edge cases per rating."""
    print("=" * 60)
    print("TEST 5: Rating Boundaries")
    print("=" * 60)
    
    sf = StockfishWrapper()
    sf.start()
    
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    
    # Test con rating molto basso
    depth_low = get_depth_for_rating(800)
    print(f"Rating 800 → depth {depth_low}")
    result_low = sf.analyze_position(fen, depth=depth_low)
    print(f"  Analysis completed in ~{depth_low} ply")
    
    # Test con rating molto alto
    depth_high = get_depth_for_rating(2800)
    print(f"Rating 2800 → depth {depth_high}")
    result_high = sf.analyze_position(fen, depth=depth_high)
    print(f"  Analysis completed in ~{depth_high} ply")
    
    sf.quit()
    print("✓ Boundary tests passed\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CHESS COACH MCP - TEST SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_stockfish_integration()
        test_skill_adaptation()
        test_move_classification()
        test_full_analysis_workflow()
        test_rating_boundaries()
        
        print("=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)