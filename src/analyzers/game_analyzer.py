"""
Game Analyzer - Analizza partite complete identificando critical moments e pattern.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import chess

try:
    # Import relativi (quando usato come modulo)
    from ..stockfish_wrapper import StockfishWrapper
    from ..utils.pgn_parser import PGNParser, ParsedGame, GameMove
    from .plan_detector import PlanDetector
except ImportError:
    # Import assoluti (quando eseguito come script)
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from src.stockfish_wrapper import StockfishWrapper
    from src.utils.pgn_parser import PGNParser, ParsedGame, GameMove
    from src.analyzers.plan_detector import PlanDetector


@dataclass
class CriticalMoment:
    """Rappresenta un momento critico nella partita."""
    move_number: int
    player: str
    move_san: str
    move_uci: str
    fen_before: str
    type: str  # "blunder" | "mistake" | "missed_opportunity" | "brilliant" | "critical_position"
    eval_before: float
    eval_after: float
    eval_swing: float
    best_move: Optional[str] = None
    explanation: str = ""


@dataclass
class GameAnalysisResult:
    """Risultato completo dell'analisi di una partita."""
    game_info: Dict[str, str]
    critical_moments: List[CriticalMoment]
    phase_summaries: Dict[str, Any]
    patterns_detected: List[Dict[str, Any]]
    overall_statistics: Dict[str, Any]


class GameAnalyzer:
    """Analizza partite complete."""
    
    def __init__(
        self,
        stockfish: StockfishWrapper,
        plan_detector: PlanDetector
    ):
        """
        Inizializza analyzer.
        
        Args:
            stockfish: Istanza di StockfishWrapper
            plan_detector: Istanza di PlanDetector
        """
        self.stockfish = stockfish
        self.plan_detector = plan_detector
        self.parser = PGNParser()
    
    def analyze_game(
        self,
        pgn_string: str,
        player_rating: int = 1500,
        depth: int = None,
        analyze_all_moves: bool = False
    ) -> GameAnalysisResult:
        """
        Analizza una partita completa.
        
        Args:
            pgn_string: PGN della partita
            player_rating: Rating del giocatore
            depth: Profondità analisi Stockfish
            analyze_all_moves: Se True, analizza ogni mossa (costoso).
                              Se False, analizza solo critical moments.
        
        Returns:
            GameAnalysisResult con analisi completa
        """
        if depth is None:
            depth = self._get_depth_for_rating(player_rating)
        
        # Parse PGN
        game = self.parser.parse_pgn(pgn_string)
        
        # Identify critical moments
        critical_moments = self._identify_critical_moments(
            game,
            depth,
            analyze_all_moves,
            player_rating
        )
        
        # Detect patterns throughout game
        patterns_detected = self._detect_patterns_in_game(game, player_rating)
        
        # Phase summaries
        phases = self.parser.get_phase_boundaries(game)
        phase_summaries = {
            "opening": self._summarize_phase(
                game.moves[:phases["opening_end"] * 2],
                "opening"
            ),
            "middlegame": self._summarize_phase(
                game.moves[phases["opening_end"] * 2:phases["middlegame_end"] * 2],
                "middlegame"
            ),
            "endgame": self._summarize_phase(
                game.moves[phases["middlegame_end"] * 2:],
                "endgame"
            )
        }
        
        # Overall statistics
        stats = self._calculate_statistics(game, critical_moments)
        
        return GameAnalysisResult(
            game_info=game.headers,
            critical_moments=critical_moments,
            phase_summaries=phase_summaries,
            patterns_detected=patterns_detected,
            overall_statistics=stats
        )
    
    def _identify_critical_moments(
        self,
        game: ParsedGame,
        depth: int,
        analyze_all: bool,
        player_rating: int
    ) -> List[CriticalMoment]:
        """
        Identifica momenti critici nella partita.
        
        Strategy:
        1. Quick scan: analizza ogni N mosse con depth bassa
        2. Identifica eval swings > threshold
        3. Deep analysis sui momenti critici
        """
        critical_moments = []
        
        if analyze_all:
            # Analizza ogni mossa (costoso)
            step = 1
            quick_depth = depth
        else:
            # Quick scan: ogni 3 mosse
            step = 3
            quick_depth = max(12, depth - 8)
        
        prev_eval = 0.0
        
        for i in range(0, len(game.moves), step):
            move = game.moves[i]
            
            # Analizza posizione prima della mossa
            analysis_before = self.stockfish.analyze_position(
                move.fen_before,
                depth=quick_depth
            )
            
            # Analizza posizione dopo la mossa
            analysis_after = self.stockfish.analyze_position(
                move.fen_after,
                depth=quick_depth
            )
            
            eval_before = analysis_before["evaluation"]
            eval_after = -analysis_after["evaluation"]  # Inverti segno (turno cambiato)
            
            eval_swing = eval_after - eval_before
            
            # Classifica momento
            moment_type = self._classify_moment(eval_swing, player_rating)
            
            if moment_type:
                # È un momento critico - deep analysis
                if not analyze_all and quick_depth < depth:
                    # Re-analizza con depth piena
                    analysis_before = self.stockfish.analyze_position(
                        move.fen_before,
                        depth=depth
                    )
                
                critical_moment = CriticalMoment(
                    move_number=move.move_number,
                    player=move.player,
                    move_san=move.move_san,
                    move_uci=move.move_uci,
                    fen_before=move.fen_before,
                    type=moment_type,
                    eval_before=eval_before,
                    eval_after=eval_after,
                    eval_swing=eval_swing,
                    best_move=analysis_before["best_move"],
                    explanation=self._generate_moment_explanation(
                        move,
                        eval_swing,
                        moment_type,
                        analysis_before
                    )
                )
                
                critical_moments.append(critical_moment)
            
            prev_eval = eval_after
        
        return critical_moments
    
    def _classify_moment(self, eval_swing: float, rating: int) -> Optional[str]:
        """
        Classifica un momento basandosi su eval swing.
        
        Thresholds si adattano al rating (principianti: più permissivi).
        """
        # Adjust thresholds
        if rating < 1400:
            blunder_threshold = -2.0
            mistake_threshold = -1.2
            inaccuracy_threshold = -0.6
        else:
            blunder_threshold = -1.5
            mistake_threshold = -0.8
            inaccuracy_threshold = -0.4
        
        if eval_swing < blunder_threshold:
            return "blunder"
        elif eval_swing < mistake_threshold:
            return "mistake"
        elif eval_swing < inaccuracy_threshold:
            return "inaccuracy"
        elif eval_swing > 1.0:
            return "brilliant"
        elif abs(eval_swing) > 0.8:
            return "critical_position"
        
        return None
    
    def _generate_moment_explanation(
        self,
        move: GameMove,
        eval_swing: float,
        moment_type: str,
        analysis: Dict[str, Any]
    ) -> str:
        """Genera spiegazione human-readable del momento."""
        if moment_type in ["blunder", "mistake"]:
            return (
                f"This move loses {abs(eval_swing):.1f} pawns of advantage. "
                f"Better was {analysis['best_move']}."
            )
        elif moment_type == "brilliant":
            return f"Excellent move! Gained {eval_swing:.1f} pawns."
        elif moment_type == "critical_position":
            return "Critical moment - position evaluation changed significantly."
        else:
            return f"Inaccuracy - lost {abs(eval_swing):.1f} pawns."
    
    def _detect_patterns_in_game(
        self,
        game: ParsedGame,
        player_rating: int
    ) -> List[Dict[str, Any]]:
        """
        Rileva pattern strategici applicati (o mancati) durante la partita.
        
        Strategy:
        - Analizza posizioni chiave (ogni 5-10 mosse)
        - Identifica pattern applicabili
        - Verifica se il giocatore ha seguito il pattern
        """
        patterns_found = []
        
        # Analizza ogni 5 mosse
        for i in range(0, len(game.moves), 5):
            if i >= len(game.moves):
                break
            
            move = game.moves[i]
            
            # Rileva pattern applicabili
            patterns = self.plan_detector.detect_patterns(
                move.fen_before,
                player_rating
            )
            
            if patterns:
                # Verifica se il giocatore ha seguito qualche pattern
                # nelle prossime 3-5 mosse
                next_moves = game.moves[i:min(i+5, len(game.moves))]
                
                for pattern in patterns[:2]:  # Top 2 pattern
                    followed = self._check_pattern_followed(
                        next_moves,
                        pattern
                    )
                    
                    patterns_found.append({
                        "move_number": move.move_number,
                        "pattern_name": pattern["pattern_name"],
                        "confidence": pattern["confidence"],
                        "followed": followed,
                        "fen": move.fen_before
                    })
        
        return patterns_found
    
    def _check_pattern_followed(
        self,
        moves: List[GameMove],
        pattern: Dict[str, Any]
    ) -> bool:
        """
        Verifica (semplificato) se le mosse seguono il pattern.
        
        TODO: logica più sofisticata per matching mosse.
        """
        # Simplified: check se almeno una mossa tipica è stata giocata
        typical_moves = pattern.get("typical_moves", [])
        
        for move in moves:
            for typical in typical_moves:
                # Match SAN o UCI (approssimativo)
                if typical.lower() in move.move_san.lower() or typical == move.move_uci:
                    return True
        
        return False
    
    def _summarize_phase(
        self,
        moves: List[GameMove],
        phase_name: str
    ) -> Dict[str, Any]:
        """Genera summary di una fase della partita."""
        if not moves:
            return {
                "phase": phase_name,
                "move_count": 0,
                "summary": "Phase not reached"
            }
        
        return {
            "phase": phase_name,
            "move_count": len(moves),
            "start_move": moves[0].move_number,
            "end_move": moves[-1].move_number,
            "summary": f"{phase_name.capitalize()} phase with {len(moves)} moves"
        }
    
    def _calculate_statistics(
        self,
        game: ParsedGame,
        critical_moments: List[CriticalMoment]
    ) -> Dict[str, Any]:
        """Calcola statistiche generali sulla partita."""
        blunders = [m for m in critical_moments if m.type == "blunder"]
        mistakes = [m for m in critical_moments if m.type == "mistake"]
        brilliancies = [m for m in critical_moments if m.type == "brilliant"]
        
        return {
            "total_moves": game.total_moves,
            "blunders": len(blunders),
            "mistakes": len(mistakes),
            "brilliancies": len(brilliancies),
            "critical_moments_count": len(critical_moments),
            "result": game.result
        }
    
    def _get_depth_for_rating(self, rating: int) -> int:
        """Depth per rating."""
        if rating < 1200:
            return 12
        elif rating < 1800:
            return 18
        elif rating < 2200:
            return 22
        else:
            return 25


# Test
# Test
if __name__ == "__main__":
    print("Testing Game Analyzer...\n")
    
    # Import assoluti per test standalone
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    
    from src.stockfish_wrapper import StockfishWrapper
    from src.analyzers.plan_detector import PlanDetector
    
    # Sample PGN con un errore evidente
    sample_pgn = """
[Event "Test Game"]
[White "Player"]
[Black "Opponent"]
[Result "0-1"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Nf6 4. Ng5 d5 5. exd5 Nxd5 6. Nxf7 Kxf7 
7. Qf3+ Ke6 8. Nc3 Nb4 9. a3 Nxc2+ 10. Kd1 Nxa1 0-1
"""
    
    sf = StockfishWrapper(default_depth=15)
    sf.start()
    
    detector = PlanDetector()
    analyzer = GameAnalyzer(sf, detector)
    
    print("=" * 60)
    print("TEST: Analyze Complete Game")
    print("=" * 60)
    print("(This may take 30-60 seconds...)\n")
    
    result = analyzer.analyze_game(
        sample_pgn,
        player_rating=1500,
        analyze_all_moves=False  # Quick scan
    )
    
    print(f"Game: {result.game_info.get('Event')}")
    print(f"Result: {result.overall_statistics['result']}")
    print(f"Total moves: {result.overall_statistics['total_moves']}")
    print()
    
    print(f"Critical moments found: {result.overall_statistics['critical_moments_count']}")
    print(f"  Blunders: {result.overall_statistics['blunders']}")
    print(f"  Mistakes: {result.overall_statistics['mistakes']}")
    print(f"  Brilliancies: {result.overall_statistics['brilliancies']}")
    print()
    
    if result.critical_moments:
        print("First critical moment:")
        moment = result.critical_moments[0]
        print(f"  Move {moment.move_number}. {moment.move_san} ({moment.player})")
        print(f"  Type: {moment.type}")
        print(f"  Eval swing: {moment.eval_swing:+.2f}")
        print(f"  {moment.explanation}")
    
    print()
    print(f"Patterns detected: {len(result.patterns_detected)}")
    
    sf.quit()
    print("\n✓ Game Analyzer tests completed")