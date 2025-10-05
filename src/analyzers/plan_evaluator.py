"""
Plan Evaluator - Valuta la soundness di piani strategici usando Stockfish.
"""
import chess
import chess.pgn
from typing import Dict, Any, List, Optional
from ..stockfish_wrapper import StockfishWrapper


class PlanEvaluator:
    """Valuta piani strategici con Stockfish."""
    
    def __init__(self, stockfish_wrapper: StockfishWrapper):
        """
        Inizializza evaluator.
        
        Args:
            stockfish_wrapper: Istanza di StockfishWrapper già inizializzata
        """
        self.stockfish = stockfish_wrapper
    
    def evaluate_plan(
        self,
        fen: str,
        plan_description: str,
        candidate_moves: List[str],
        player_rating: int = 1500,
        depth: int = None
    ) -> Dict[str, Any]:
        """
        Valuta un piano strategico.
        
        Args:
            fen: Posizione di partenza (FEN)
            plan_description: Descrizione testuale del piano
            candidate_moves: Lista di mosse UCI che rappresentano il piano
            player_rating: Rating del giocatore
            depth: Profondità analisi (se None, usa depth per rating)
            
        Returns:
            Dict con:
            - soundness: "excellent" | "good" | "dubious" | "bad"
            - evaluation: eval finale dopo il piano
            - eval_trajectory: lista di eval ad ogni mossa
            - stockfish_agrees: bool
            - execution_difficulty: rating
            - risks: lista di rischi
            - alternatives: piani alternativi migliori
        """
        if depth is None:
            depth = self._get_depth_for_rating(player_rating)
        
        board = chess.Board(fen)
        initial_eval = self.stockfish.analyze_position(fen, depth=depth)
        
        # Simula esecuzione del piano
        eval_trajectory = [initial_eval["evaluation"]]
        positions = [fen]
        
        for move_uci in candidate_moves:
            try:
                move = chess.Move.from_uci(move_uci)
                if move not in board.legal_moves:
                    # Mossa illegale - piano non eseguibile
                    return {
                        "soundness": "bad",
                        "error": f"Illegal move: {move_uci}",
                        "evaluation": initial_eval["evaluation"],
                        "stockfish_agrees": False
                    }
                
                board.push(move)
                current_fen = board.fen()
                positions.append(current_fen)
                
                # Valuta posizione dopo mossa
                eval_result = self.stockfish.analyze_position(current_fen, depth=depth)
                # Inverti segno perché è il turno dell'avversario
                eval_trajectory.append(-eval_result["evaluation"])
                
            except ValueError:
                return {
                    "soundness": "bad",
                    "error": f"Invalid move format: {move_uci}",
                    "evaluation": initial_eval["evaluation"],
                    "stockfish_agrees": False
                }
        
        final_eval = eval_trajectory[-1]
        eval_change = final_eval - initial_eval["evaluation"]
        
        # Classifica soundness
        soundness = self._classify_soundness(eval_change, player_rating)
        
        # Verifica se Stockfish preferirebbe mosse diverse
        stockfish_agreement = self._check_stockfish_agreement(
            fen,
            candidate_moves[0] if candidate_moves else None,
            initial_eval["best_move"],
            depth
        )
        
        # Calcola difficoltà di esecuzione
        execution_difficulty = self._assess_execution_difficulty(
            candidate_moves,
            eval_trajectory,
            player_rating
        )
        
        # Identifica rischi
        risks = self._identify_risks(eval_trajectory, board)
        
        # Trova alternative migliori se il piano è subottimale
        alternatives = []
        if soundness in ["dubious", "bad"]:
            alternatives = self._find_alternatives(fen, depth)
        
        return {
            "soundness": soundness,
            "evaluation": final_eval,
            "eval_change": eval_change,
            "eval_trajectory": eval_trajectory,
            "positions": positions,
            "stockfish_agrees": stockfish_agreement,
            "execution_difficulty": execution_difficulty,
            "risks": risks,
            "alternatives": alternatives,
            "move_count": len(candidate_moves)
        }
    
    def evaluate_pattern_application(
        self,
        fen: str,
        pattern: Dict[str, Any],
        player_rating: int = 1500,
        depth: int = None
    ) -> Dict[str, Any]:
        """
        Valuta l'applicazione di un pattern strategico rilevato.
        
        Args:
            fen: Posizione FEN
            pattern: Pattern dict dal PlanDetector
            player_rating: Rating giocatore
            depth: Profondità analisi
            
        Returns:
            Valutazione del pattern con raccomandazioni
        """
        if depth is None:
            depth = self._get_depth_for_rating(player_rating)
        
        # Usa typical_moves del pattern come candidate moves
        typical_moves = pattern.get("typical_moves", [])
        
        # Filtra solo mosse UCI valide (alcune potrebbero essere descrittive tipo "g4")
        candidate_moves = self._extract_uci_moves(fen, typical_moves[:3])
        
        if not candidate_moves:
            # Pattern non ha mosse concrete - valutazione generica
            current_eval = self.stockfish.analyze_position(fen, depth=depth)
            return {
                "pattern_name": pattern["pattern_name"],
                "soundness": "good",  # Assumiamo buono se passa preconditions
                "evaluation": current_eval["evaluation"],
                "note": "Pattern detected but requires specific move selection",
                "key_ideas": pattern["key_ideas"]
            }
        
        # Valuta piano concreto
        evaluation = self.evaluate_plan(
            fen,
            pattern["description"],
            candidate_moves,
            player_rating,
            depth
        )
        
        # Aggiungi context del pattern
        evaluation["pattern_name"] = pattern["pattern_name"]
        evaluation["pattern_description"] = pattern["description"]
        evaluation["key_ideas"] = pattern["key_ideas"]
        evaluation["complexity"] = pattern["complexity"]
        
        return evaluation
    
    def _get_depth_for_rating(self, rating: int) -> int:
        """Ritorna depth appropriata per rating."""
        if rating < 1200:
            return 12
        elif rating < 1800:
            return 18
        elif rating < 2200:
            return 22
        else:
            return 25
    
    def _classify_soundness(self, eval_change: float, player_rating: int) -> str:
        """
        Classifica soundness del piano basandosi su eval change.
        
        Thresholds sono più permissivi per rating bassi.
        """
        # Adjust thresholds based on rating
        if player_rating < 1400:
            # Beginners: più permissivi
            if eval_change >= -0.2:
                return "excellent"
            elif eval_change >= -0.5:
                return "good"
            elif eval_change >= -1.2:
                return "dubious"
            else:
                return "bad"
        else:
            # Advanced players: più rigorosi
            if eval_change >= -0.1:
                return "excellent"
            elif eval_change >= -0.3:
                return "good"
            elif eval_change >= -0.8:
                return "dubious"
            else:
                return "bad"
    
    def _check_stockfish_agreement(
        self,
        fen: str,
        first_move: Optional[str],
        stockfish_best: str,
        depth: int
    ) -> bool:
        """
        Verifica se la prima mossa del piano è vicina al best move di Stockfish.
        """
        if not first_move:
            return False
        
        # Exact match
        if first_move == stockfish_best:
            return True
        
        # Check if within top 3 moves (MultiPV would be ideal here, but simplified)
        # For now, just check if eval loss is small
        eval_result = self.stockfish.evaluate_move(fen, first_move, depth=depth)
        eval_loss = eval_result.get("eval_loss", -999)
        
        # Agreement if eval loss < 0.3
        return eval_loss > -0.3
    
    def _assess_execution_difficulty(
        self,
        moves: List[str],
        eval_trajectory: List[float],
        player_rating: int
    ) -> str:
        """
        Valuta difficoltà di esecuzione del piano.
        
        Returns: "easy" | "moderate" | "difficult" | "very_difficult"
        """
        factors = 0
        
        # Lungo = più difficile
        if len(moves) > 8:
            factors += 2
        elif len(moves) > 5:
            factors += 1
        
        # Eval volatility = richiede precisione
        if len(eval_trajectory) > 1:
            volatility = max(eval_trajectory) - min(eval_trajectory)
            if volatility > 1.5:
                factors += 2
            elif volatility > 0.8:
                factors += 1
        
        # Mosse quiet (non forcing) = più difficili
        # TODO: implementare detection di quiet moves
        
        if factors <= 1:
            return "easy"
        elif factors <= 2:
            return "moderate"
        elif factors <= 3:
            return "difficult"
        else:
            return "very_difficult"
    
    def _identify_risks(
        self,
        eval_trajectory: List[float],
        final_board: chess.Board
    ) -> List[str]:
        """Identifica rischi nel piano."""
        risks = []
        
        # Eval drop durante esecuzione
        if len(eval_trajectory) > 1:
            for i in range(1, len(eval_trajectory)):
                drop = eval_trajectory[i] - eval_trajectory[i-1]
                if drop < -0.5:
                    risks.append(f"Significant eval drop at move {i} (-{abs(drop):.2f})")
        
        # King safety compromessa
        if final_board.is_check():
            risks.append("King in check after plan execution")
        
        # TODO: altri rischi (material sacrifice, weakened pawn structure, etc.)
        
        return risks
    
    def _find_alternatives(self, fen: str, depth: int) -> List[Dict[str, Any]]:
        """Trova piani alternativi migliori."""
        # Per ora, ritorna solo best move di Stockfish
        analysis = self.stockfish.analyze_position(fen, depth=depth)
        
        return [{
            "move": analysis["best_move"],
            "evaluation": analysis["evaluation"],
            "type": "stockfish_recommendation"
        }]
    
    def _extract_uci_moves(self, fen: str, move_list: List[str]) -> List[str]:
        """
        Estrae mosse UCI valide da una lista che potrebbe contenere notazione algebrica.
        
        Args:
            fen: Posizione corrente
            move_list: Lista di mosse (possono essere UCI o algebriche tipo "g4")
            
        Returns:
            Lista di mosse in formato UCI
        """
        board = chess.Board(fen)
        uci_moves = []
        
        for move_str in move_list:
            # Try as UCI first
            try:
                move = chess.Move.from_uci(move_str)
                if move in board.legal_moves:
                    uci_moves.append(move_str)
                    continue
            except ValueError:
                pass
            
            # Try as SAN (Standard Algebraic Notation)
            try:
                move = board.parse_san(move_str)
                if move in board.legal_moves:
                    uci_moves.append(move.uci())
            except (ValueError, chess.IllegalMoveError, chess.InvalidMoveError):
                # Skip invalid moves
                continue
        
        return uci_moves


# Test
if __name__ == "__main__":
    print("Testing Plan Evaluator...\n")
    
    from src.stockfish_wrapper import StockfishWrapper
    
    sf = StockfishWrapper(default_depth=15)
    sf.start()
    
    evaluator = PlanEvaluator(sf)
    
    # Test 1: Evaluate a simple plan
    print("=" * 60)
    print("TEST 1: Evaluate Simple Plan (central pawn push)")
    print("=" * 60)
    
    fen = "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
    plan_moves = ["e2e4", "b1c3", "g1f3"]  # Develop pieces, prepare e4-e5
    
    result = evaluator.evaluate_plan(
        fen,
        "Develop pieces and prepare central advance",
        plan_moves,
        player_rating=1500
    )
    
    print(f"Soundness: {result['soundness']}")
    print(f"Eval change: {result['eval_change']:+.2f}")
    print(f"Stockfish agrees: {result['stockfish_agrees']}")
    print(f"Execution difficulty: {result['execution_difficulty']}")
    print(f"Risks: {result['risks']}")
    print()
    
    # Test 2: Evaluate a dubious plan
    print("=" * 60)
    print("TEST 2: Evaluate Dubious Plan (premature attack)")
    print("=" * 60)
    
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    dubious_plan = ["b8a6", "a6b4"]  # Develop knight to edge, then jump
    
    result = evaluator.evaluate_plan(
        fen,
        "Early knight maneuver to b4",
        dubious_plan,
        player_rating=1500
    )
    
    print(f"Soundness: {result['soundness']}")
    print(f"Eval change: {result['eval_change']:+.2f}")
    print(f"Stockfish agrees: {result['stockfish_agrees']}")
    if result.get('alternatives'):
        print(f"Better alternative: {result['alternatives'][0]['move']}")
    print()
    
    sf.quit()
    print("✓ Plan Evaluator tests completed")