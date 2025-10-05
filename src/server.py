"""
MCP Server per chess coaching.
Espone tools per analizzare partite di scacchi con Stockfish.
"""
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel, Field
from typing import Any, List  
import logging
import sys
from pathlib import Path

from .analyzers.plan_detector import PlanDetector
from .analyzers.plan_evaluator import PlanEvaluator
from .stockfish_wrapper import StockfishWrapper
from .analyzers.game_analyzer import GameAnalyzer
from .utils.pgn_parser import PGNParser

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

plan_detector = PlanDetector()
plan_evaluator = None

game_analyzer = None
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

class DetectStrategicPlansInput(BaseModel):
    """Input per detect_strategic_plans tool."""
    fen: str = Field(description="Position in FEN notation")
    player_rating: int = Field(
        default=1500,
        ge=800,
        le=3000,
        description="Player's ELO rating"
    )


class EvaluatePlanInput(BaseModel):
    """Input per evaluate_plan tool."""
    fen: str = Field(description="Starting position (FEN)")
    plan_description: str = Field(description="Text description of the plan")
    candidate_moves: List[str] = Field(
        description="List of moves (UCI format) representing the plan"
    )
    player_rating: int = Field(default=1500, ge=800, le=3000)


class AnalyzeGameInput(BaseModel):
    """Input per analyze_game tool."""
    pgn: str = Field(description="Complete PGN of the game to analyze")
    player_rating: int = Field(
        default=1500,
        ge=800,
        le=3000,
        description="Player's ELO rating"
    )
    analyze_all_moves: bool = Field(
        default=False,
        description="If true, analyze every move (slower but more thorough)"
    )

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
        Tool(
            name="detect_strategic_plans",
            description=(
                "Detect applicable strategic plans/patterns in a position. "
                "Returns patterns like 'minority attack', 'kingside storm', etc. "
                "Filters by player rating to suggest skill-appropriate plans."
            ),
            inputSchema=DetectStrategicPlansInput.model_json_schema()
        ),
        Tool(
            name="evaluate_plan",
            description=(
                "Evaluate the soundness of a strategic plan. "
                "Takes a sequence of moves representing a plan and validates it with Stockfish. "
                "Returns soundness rating, risks, and alternatives if the plan is dubious."
            ),
            inputSchema=EvaluatePlanInput.model_json_schema()
        ),
        Tool(
            name="analyze_game",
            description=(
                "Analyze a complete chess game from PGN. "
                "Identifies critical moments (blunders, mistakes, brilliancies), "
                "detects strategic patterns, and provides phase-by-phase summary. "
                "Use analyze_all_moves=false for quick scan, true for thorough analysis."
            ),
            inputSchema=AnalyzeGameInput.model_json_schema()
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
    
    elif name == "detect_strategic_plans":
        # Validate input
        input_data = DetectStrategicPlansInput(**arguments)
        
        logger.info(f"Detecting strategic plans (rating={input_data.player_rating})")
        
        # Rileva pattern
        patterns = plan_detector.detect_patterns(
            input_data.fen,
            input_data.player_rating
        )
        
        # Format response
        response = {
            "position": input_data.fen,
            "player_rating": input_data.player_rating,
            "patterns_found": len(patterns),
            "patterns": [
                {
                    "name": p["pattern_name"],
                    "description": p["description"],
                    "confidence": f"{p['confidence']:.2f}",
                    "complexity": p["complexity"],
                    "typical_moves": p["typical_moves"][:5],
                    "key_ideas": p["key_ideas"],
                    "skill_appropriate": p["skill_appropriate"]
                }
                for p in patterns[:5]  # Top 5 patterns
            ]
        }
        
        return [TextContent(
            type="text",
            text=str(response)
        )]
    
    elif name == "evaluate_plan":
        # Validate input
        input_data = EvaluatePlanInput(**arguments)
        
        logger.info(f"Evaluating plan: {input_data.plan_description}")
        
        # Valuta piano
        result = plan_evaluator.evaluate_plan(
            input_data.fen,
            input_data.plan_description,
            input_data.candidate_moves,
            input_data.player_rating
        )
        
        # Check se c'è stato un errore
        if "error" in result:
            response = {
                "plan_description": input_data.plan_description,
                "soundness": result["soundness"],
                "error": result["error"],
                "note": "Plan could not be executed - check move validity"
            }
        else:
            # Format response normale
            response = {
                "plan_description": input_data.plan_description,
                "soundness": result["soundness"],
                "evaluation_change": f"{result['eval_change']:+.2f}",
                "final_evaluation": format_evaluation(result["evaluation"]),
                "stockfish_agrees": result["stockfish_agrees"],
                "execution_difficulty": result["execution_difficulty"],
                "move_count": result["move_count"],
                "risks": result["risks"],
                "alternatives": result.get("alternatives", [])
            }
        
        return [TextContent(
            type="text",
            text=str(response)
        )]
    
    elif name == "analyze_game":
        # Validate input
        input_data = AnalyzeGameInput(**arguments)
        
        logger.info(f"Analyzing game (rating={input_data.player_rating}, all_moves={input_data.analyze_all_moves})")
        
        # Analizza partita
        result = game_analyzer.analyze_game(
            input_data.pgn,
            input_data.player_rating,
            analyze_all_moves=input_data.analyze_all_moves
        )
        
        # Format response
        response = {
            "game_info": result.game_info,
            "statistics": result.overall_statistics,
            "critical_moments": [
                {
                    "move": f"{m.move_number}. {m.move_san}",
                    "player": m.player,
                    "type": m.type,
                    "eval_swing": f"{m.eval_swing:+.2f}",
                    "explanation": m.explanation,
                    "best_move": m.best_move,
                    "fen": m.fen_before
                }
                for m in result.critical_moments[:10]  # Top 10 critical moments
            ],
            "phases": {
                "opening": result.phase_summaries["opening"],
                "middlegame": result.phase_summaries["middlegame"],
                "endgame": result.phase_summaries["endgame"]
            },
            "patterns_detected_count": len(result.patterns_detected),
            "patterns_sample": result.patterns_detected[:3]  # Top 3 patterns
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
    global plan_evaluator  # Aggiungi questa linea
    
    logger.info("Starting Chess Coach MCP Server...")
    
    # Start Stockfish
    stockfish.start()
    
    if not stockfish.is_ready():
        raise RuntimeError("Stockfish failed to start")
    
    logger.info("Stockfish ready!")
    
    # Inizializza plan evaluator (richiede stockfish avviato)
    plan_evaluator = PlanEvaluator(stockfish)
    logger.info("Plan evaluator initialized!")
    
    # Inizializza game analyzer
    game_analyzer = GameAnalyzer(stockfish, plan_detector)
    logger.info("Game analyzer initialized!")

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