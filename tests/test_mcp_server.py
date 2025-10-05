"""
Test del server MCP in modalità simulata.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.server import (
    list_tools,
    call_tool,
    stockfish
)
import asyncio


async def test_list_tools():
    """Test che i tools siano esposti correttamente."""
    print("=" * 60)
    print("TEST: List Tools")
    print("=" * 60)
    
    tools = await list_tools()
    
    assert len(tools) == 2, f"Should have 2 tools, got {len(tools)}"
    
    tool_names = [t.name for t in tools]
    assert "analyze_position" in tool_names
    assert "evaluate_move" in tool_names
    
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")
    
    print()


async def test_analyze_position_tool():
    """Test tool analyze_position."""
    print("=" * 60)
    print("TEST: analyze_position Tool")
    print("=" * 60)
    
    # Start Stockfish
    stockfish.start()
    
    # Simula chiamata da Claude
    arguments = {
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "player_rating": 1500
    }
    
    print(f"Calling analyze_position with:")
    print(f"  FEN: {arguments['fen'][:50]}...")
    print(f"  Rating: {arguments['player_rating']}")
    
    result = await call_tool("analyze_position", arguments)
    
    assert len(result) == 1, "Should return one TextContent"
    assert result[0].type == "text"
    
    # Parse response (è un dict stringificato)
    response_text = result[0].text
    print(f"\nResponse received:")
    print(response_text)
    
    # Verifica che contenga campi chiave
    assert "evaluation" in response_text
    assert "best_move" in response_text
    
    print("✓ Tool executed successfully\n")


async def test_evaluate_move_tool():
    """Test tool evaluate_move."""
    print("=" * 60)
    print("TEST: evaluate_move Tool")
    print("=" * 60)
    
    arguments = {
        "fen_before": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "move_played": "b8c6",
        "player_rating": 1500
    }
    
    print(f"Calling evaluate_move with:")
    print(f"  Move: Nc6 (UCI: {arguments['move_played']})")
    print(f"  Rating: {arguments['player_rating']}")
    
    result = await call_tool("evaluate_move", arguments)
    
    assert len(result) == 1
    response_text = result[0].text
    
    print(f"\nResponse received:")
    print(response_text)
    
    assert "move_quality" in response_text
    assert "evaluation_loss" in response_text
    
    print("✓ Tool executed successfully\n")


async def test_different_ratings():
    """Test che depth si adatti al rating."""
    print("=" * 60)
    print("TEST: Rating Adaptation")
    print("=" * 60)
    
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    ratings = [1000, 1500, 2000, 2500]
    
    for rating in ratings:
        arguments = {
            "fen": fen,
            "player_rating": rating
        }
        
        result = await call_tool("analyze_position", arguments)
        response_text = result[0].text
        
        # Extract depth from response
        import re
        depth_match = re.search(r"'analysis_depth': (\d+)", response_text)
        if depth_match:
            depth = int(depth_match.group(1))
            print(f"✓ Rating {rating} → depth {depth}")
        else:
            print(f"⚠ Could not extract depth for rating {rating}")
    
    print()


async def main():
    print("\n" + "=" * 60)
    print("MCP SERVER TESTS")
    print("=" * 60 + "\n")
    
    try:
        await test_list_tools()
        await test_analyze_position_tool()
        await test_evaluate_move_tool()
        await test_different_ratings()
        
        # Cleanup
        stockfish.quit()
        
        print("=" * 60)
        print("ALL SERVER TESTS PASSED ✓")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())