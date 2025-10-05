"""
MCP Server per chess coaching.
Espone tools per analizzare partite di scacchi con Stockfish.
"""
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
from typing import Any
import logging

from .stockfish_wrapper import StockfishWrapper
import sys
from pathlib import Path

# Aggiungi root al path se eseguito come modulo
if __name__ == "__main__":
    root_path = Path(__file__).parent.parent
    sys.path.insert(0, str(root_path))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inizializza server MCP
app = Server("chess-coach")

# Inizializza Stockfish wrapper (global per ora)
stockfish = StockfishWrapper(default_depth=20)


# --- Pydantic Models per input validation ---

class AnalyzePositionInput(BaseModel):
    """Input per analyze_position tool."""
    fen: str = Field(description="Position in FEN notation")
    player_rating: int = Field(
        default=1500,
        ge=800,
        le=3000,
        description="Player's ELO rating (800-3000)"
    )
    depth: int | None = Field(
        default=None,
        description="Analysis depth (if None, adapts to player_rating)"
    )


class EvaluateMoveInput(BaseModel):
    """Input per evaluate_move tool."""
    fen_before: str = Field(description="Position before the move (FEN)")
    move_played: str = Field(description="Move in UCI notation (e.g., 'e2e4')")
    player_rating: int = Field(default=1500, ge=800, le=3000)


# --- Helper functions ---

def get_depth_for_rating(rating: int) -> int:
    """
    Ritorna depth appropriata per il rating del giocatore.
    
    Logica:
    - Beginner (800-1200): depth 12
    - Intermediate (1200-1800): depth 18
    - Advanced (1800-2200): depth 22
    - Expert (2200+): depth 25
    """
    if rating < 1200:
        return 12
    elif rating < 1800:
        return 18
    elif rating < 2200:
        return 22
    else:
        return 25


def format_evaluation(eval_value: float) -> str:
    """Formatta evaluation in modo human-readable."""
    if abs(eval_value) > 50:
        # Mate detected
        return "Mate detected"
    elif eval_value > 0:
        return f"+{eval_value:.2f}"
    else:
        return f"{eval_value:.2f}"


def classify_move_quality(eval_loss: float) -> str:
    """
    Classifica qualità della mossa basandosi su eval loss.
    
    Thresholds:
    - 0 to -0.1: excellent
    - -0.1 to -0.3: good
    - -0.3 to -1.0: inaccuracy
    - -1.0 to -3.0: mistake
    - < -3.0: blunder
    """
    if eval_loss >= -0.1:
        return "excellent"
    elif eval_loss >= -0.3:
        return "good"
    elif eval_loss >= -1.0:
        return "inaccuracy"
    elif eval_loss >= -3.0:
        return "mistake"
    else:
        return "blunder"


# --- MCP Tools ---

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Lista dei tools disponibili."""
    return [
        Tool(
            name="analyze_position",
            description=(
                "Analyze a chess position comprehensively. "
                "Returns evaluation, best moves, and key positional features. "
                "Analysis depth adapts to player's rating."
            ),
            inputSchema=AnalyzePositionInput.model_json_schema()
        ),
        Tool(
            name="evaluate_move",
            description=(
                "Evaluate the quality of a specific move played. "
                "Compares it to the best move and returns evaluation loss. "
                "Useful for identifying mistakes and explaining why a move is suboptimal."
            ),
            inputSchema=EvaluateMoveInput.model_json_schema()
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handler per chiamate ai tools."""
    
    if name == "analyze_position":
        # Validate input
        input_data = AnalyzePositionInput(**arguments)
        
        # Determine depth
        if input_data.depth is None:
            depth = get_depth_for_rating(input_data.player_rating)
        else:
            depth = input_data.depth
        
        logger.info(f"Analyzing position (rating={input_data.player_rating}, depth={depth})")
        
        # Analizza con Stockfish
        result = stockfish.analyze_position(input_data.fen, depth=depth)
        
        # Format response
        response = {
            "evaluation": format_evaluation(result["evaluation"]),
            "best_move": result["best_move"],
            "mate_in": result["mate_in"],
            "principal_variation": " ".join(result["pv"][:8]),  # Prime 8 mosse
            "analysis_depth": depth,
            "player_rating": input_data.player_rating
        }
        
        return [TextContent(
            type="text",
            text=str(response)
        )]
    
    elif name == "evaluate_move":
        # Validate input
        input_data = EvaluateMoveInput(**arguments)
        
        depth = get_depth_for_rating(input_data.player_rating)
        
        logger.info(f"Evaluating move {input_data.move_played}")
        
        # Valuta mossa
        result = stockfish.evaluate_move(
            input_data.fen_before,
            input_data.move_played,
            depth=depth
        )
        
        # Classify quality
        quality = classify_move_quality(result["eval_loss"])
        
        # Format response
        response = {
            "move_played": result["move"],
            "move_quality": quality,
            "evaluation_after_move": format_evaluation(result["move_eval"]),
            "best_move": result["best_move"],
            "best_move_evaluation": format_evaluation(result["best_move_eval"]),
            "evaluation_loss": f"{result['eval_loss']:+.2f}",
            "analysis_depth": depth
        }
        
        return [TextContent(
            type="text",
            text=str(response)
        )]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


# --- Entry point ---

def main():
    """Avvia il server MCP."""
    logger.info("Starting Chess Coach MCP Server...")
    
    # Start Stockfish
    stockfish.start()
    
    if not stockfish.is_ready():
        raise RuntimeError("Stockfish failed to start")
    
    logger.info("Stockfish ready!")
    
    # Run server
    import asyncio
    from mcp.server.stdio import stdio_server
    
    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    
    asyncio.run(run())


if __name__ == "__main__":
    main()