"""
Plan Detector - Identifica pattern strategici applicabili in una posizione.
"""
import chess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class PlanDetector:
    """Rileva pattern strategici in posizioni scacchistiche."""
    
    def __init__(self, patterns_file: str = None):
        """
        Inizializza il detector.
        
        Args:
            patterns_file: Path al file JSON con i pattern.
                          Se None, usa config/strategic_patterns.json
        """
        if patterns_file is None:
            project_root = Path(__file__).parent.parent.parent
            patterns_file = project_root / "config" / "strategic_patterns.json"
        
        with open(patterns_file, 'r') as f:
            data = json.load(f)
            self.patterns = data["patterns"]
    
    def detect_patterns(
        self,
        fen: str,
        player_rating: int = 1500
    ) -> List[Dict[str, Any]]:
        """
        Rileva tutti i pattern applicabili in una posizione.
        
        Args:
            fen: Posizione in FEN
            player_rating: Rating del giocatore (filtra per skill level)
            
        Returns:
            Lista di pattern applicabili con metadata
        """
        board = chess.Board(fen)
        applicable_patterns = []
        
        for pattern in self.patterns:
            # Check skill level appropriateness
            min_rating, max_rating = pattern["typical_rating_range"]
            
            # Allow ±200 rating flexibility
            if not (min_rating - 200 <= player_rating <= max_rating + 200):
                continue
            
            # Check preconditions
            if self._check_preconditions(board, pattern):
                applicable_patterns.append({
                    "pattern_id": pattern["id"],
                    "pattern_name": pattern["name"],
                    "description": pattern["description"],
                    "complexity": pattern["complexity"],
                    "typical_moves": pattern["typical_moves"],
                    "key_ideas": pattern["key_ideas"],
                    "skill_appropriate": min_rating <= player_rating <= max_rating,
                    "confidence": self._calculate_confidence(board, pattern)
                })
        
        # Sort by confidence
        applicable_patterns.sort(key=lambda x: x["confidence"], reverse=True)
        
        return applicable_patterns
    
    def _check_preconditions(
        self,
        board: chess.Board,
        pattern: Dict[str, Any]
    ) -> bool:
        """
        Verifica se le precondizioni di un pattern sono soddisfatte.
        
        Args:
            board: Scacchiera chess.Board
            pattern: Pattern da verificare
            
        Returns:
            True se precondizioni soddisfatte
        """
        preconditions = pattern["preconditions"]
        prerequisites = pattern.get("prerequisites", {})
        
        # Check phase
        if "phase" in prerequisites:
            current_phase = self._determine_phase(board)
            if current_phase not in prerequisites["phase"]:
                return False
        
        # Check minimum pieces
        if "min_pieces_on_board" in prerequisites:
            piece_count = len(board.piece_map())
            if piece_count < prerequisites["min_pieces_on_board"]:
                return False
        
        # Check specific preconditions
        for precondition in preconditions:
            if not self._check_single_precondition(board, precondition):
                return False
        
        return True
    
    def _check_single_precondition(
        self,
        board: chess.Board,
        precondition: str
    ) -> bool:
        """
        Verifica una singola precondizione.
        
        Args:
            board: Scacchiera
            precondition: Nome della precondizione
            
        Returns:
            True se soddisfatta
        """
        # Opposite side castling
        if precondition == "opposite_side_castling":
            return self._has_opposite_castling(board)
        
        # Queenside pawn structures
        elif precondition == "opponent_has_queenside_pawn_majority":
            return self._check_queenside_pawn_majority(board, opponent=True)
        
        elif precondition == "player_has_queenside_pawn_minority":
            return self._check_queenside_pawn_majority(board, opponent=False, minority=True)
        
        # File pressure
        elif precondition == "semi_open_or_open_file_available":
            return self._has_open_files(board)
        
        # Material advantage
        elif precondition == "player_is_material_ahead":
            return self._is_material_ahead(board)
        
        # Central tension
        elif precondition == "central_tension_exists":
            return self._has_central_tension(board)
        
        # Outpost squares
        elif precondition == "strong_square_exists":
            return self._has_strong_squares(board)
        
        # Default: assume satisfied (for patterns we haven't fully implemented)
        return True
    
    def _determine_phase(self, board: chess.Board) -> str:
        """
        Determina la fase della partita.
        
        Logic:
        - Opening: < 10 moves, queens on board
        - Middlegame: queens on board, many pieces
        - Endgame: few pieces or no queens
        """
        piece_count = len(board.piece_map())
        has_queens = (
            bool(board.pieces(chess.QUEEN, chess.WHITE)) and
            bool(board.pieces(chess.QUEEN, chess.BLACK))
        )
        
        if board.fullmove_number < 10 and has_queens:
            return "opening"
        elif piece_count <= 12 or not has_queens:
            return "endgame"
        else:
            return "middlegame"
    
    def _has_opposite_castling(self, board: chess.Board) -> bool:
        """Verifica se i giocatori hanno arroccato su lati opposti."""
        # Simplified: check king positions
        white_king_sq = board.king(chess.WHITE)
        black_king_sq = board.king(chess.BLACK)
        
        if white_king_sq is None or black_king_sq is None:
            return False
        
        white_king_file = chess.square_file(white_king_sq)
        black_king_file = chess.square_file(black_king_sq)
        
        # Opposite sides: one king on a-d files, other on e-h files
        white_queenside = white_king_file < 4
        black_queenside = black_king_file < 4
        
        return white_queenside != black_queenside
    
    def _check_queenside_pawn_majority(
        self,
        board: chess.Board,
        opponent: bool = False,
        minority: bool = False
    ) -> bool:
        """Verifica maggioranza/minoranza di pedoni sul lato di donna."""
        color = not board.turn if opponent else board.turn
        
        # Count pawns on queenside (a-d files, 0-indexed: 0-3)
        queenside_files = [0, 1, 2, 3]
        
        player_pawns = 0
        opponent_pawns = 0
        
        for file in queenside_files:
            for rank in range(8):
                sq = chess.square(file, rank)
                piece = board.piece_at(sq)
                if piece and piece.piece_type == chess.PAWN:
                    if piece.color == color:
                        player_pawns += 1
                    else:
                        opponent_pawns += 1
        
        if minority:
            return player_pawns < opponent_pawns and player_pawns >= 2
        else:
            return player_pawns > opponent_pawns
    
    def _has_open_files(self, board: chess.Board) -> bool:
        """Verifica presenza di colonne aperte o semi-aperte."""
        color = board.turn
        
        for file in range(8):
            white_pawns = 0
            black_pawns = 0
            
            for rank in range(8):
                sq = chess.square(file, rank)
                piece = board.piece_at(sq)
                if piece and piece.piece_type == chess.PAWN:
                    if piece.color == chess.WHITE:
                        white_pawns += 1
                    else:
                        black_pawns += 1
            
            # Open file: no pawns
            if white_pawns == 0 and black_pawns == 0:
                return True
            
            # Semi-open for player
            if color == chess.WHITE and white_pawns == 0 and black_pawns > 0:
                return True
            if color == chess.BLACK and black_pawns == 0 and white_pawns > 0:
                return True
        
        return False
    
    def _is_material_ahead(self, board: chess.Board) -> bool:
        """Verifica se il giocatore ha vantaggio materiale."""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9
        }
        
        white_material = 0
        black_material = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.piece_type != chess.KING:
                value = piece_values[piece.piece_type]
                if piece.color == chess.WHITE:
                    white_material += value
                else:
                    black_material += value
        
        if board.turn == chess.WHITE:
            return white_material > black_material + 1
        else:
            return black_material > white_material + 1
    
    def _has_central_tension(self, board: chess.Board) -> bool:
        """Verifica tensione centrale (pedoni che si confrontano)."""
        central_squares = [
            chess.D4, chess.D5, chess.E4, chess.E5,
            chess.C4, chess.C5, chess.F4, chess.F5
        ]
        
        white_central_pawns = 0
        black_central_pawns = 0
        
        for sq in central_squares:
            piece = board.piece_at(sq)
            if piece and piece.piece_type == chess.PAWN:
                if piece.color == chess.WHITE:
                    white_central_pawns += 1
                else:
                    black_central_pawns += 1
        
        # Tension exists if both sides have central pawns
        return white_central_pawns > 0 and black_central_pawns > 0
    
    def _has_strong_squares(self, board: chess.Board) -> bool:
        """Verifica presenza di case forti per avamposti."""
        color = board.turn
        
        # Strong squares are typically on 4th-6th rank for White, 3rd-5th for Black
        if color == chess.WHITE:
            target_ranks = [3, 4, 5]  # 4th, 5th, 6th rank (0-indexed)
        else:
            target_ranks = [2, 3, 4]  # 5th, 4th, 3rd rank (0-indexed)
        
        # Check central files (c-f, 0-indexed: 2-5) for strong squares
        for file in [2, 3, 4, 5]:
            for rank in target_ranks:
                sq = chess.square(file, rank)
                
                # Check if square can be attacked by opponent pawns
                if not self._can_be_attacked_by_pawn(board, sq, not color):
                    # This is a potential outpost
                    return True
        
        return False
    
    def _can_be_attacked_by_pawn(
        self,
        board: chess.Board,
        square: int,
        pawn_color: bool
    ) -> bool:
        """Verifica se una casa può essere attaccata da pedoni avversari."""
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        # Direction depends on pawn color
        direction = 1 if pawn_color == chess.WHITE else -1
        
        # Check diagonals where attacking pawns would be
        for file_offset in [-1, 1]:
            attack_file = file + file_offset
            attack_rank = rank - direction
            
            if 0 <= attack_file < 8 and 0 <= attack_rank < 8:
                attack_sq = chess.square(attack_file, attack_rank)
                piece = board.piece_at(attack_sq)
                if piece and piece.piece_type == chess.PAWN and piece.color == pawn_color:
                    return True
        
        return False
    
    def _calculate_confidence(
        self,
        board: chess.Board,
        pattern: Dict[str, Any]
    ) -> float:
        """
        Calcola confidence score (0-1) per un pattern.
        
        Più precondizioni soddisfatte = confidence più alta.
        """
        total_conditions = len(pattern["preconditions"])
        if total_conditions == 0:
            return 0.5
        
        satisfied = sum(
            1 for cond in pattern["preconditions"]
            if self._check_single_precondition(board, cond)
        )
        
        return satisfied / total_conditions


# Test
if __name__ == "__main__":
    print("Testing Plan Detector...\n")
    
    detector = PlanDetector()
    
    # Test 1: Starting position
    print("=" * 60)
    print("TEST 1: Starting Position")
    print("=" * 60)
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    patterns = detector.detect_patterns(fen, player_rating=1500)
    print(f"Found {len(patterns)} applicable patterns:")
    for p in patterns:
        print(f"  - {p['pattern_name']} (confidence: {p['confidence']:.2f})")
    print()
    
    # Test 2: Position with opposite castling (kingside storm setup)
    print("=" * 60)
    print("TEST 2: Opposite Side Castling")
    print("=" * 60)
    fen = "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQ - 0 9"
    patterns = detector.detect_patterns(fen, player_rating=1500)
    print(f"Found {len(patterns)} applicable patterns:")
    for p in patterns:
        print(f"  - {p['pattern_name']} (confidence: {p['confidence']:.2f})")
        if p['pattern_id'] == 'kingside_pawn_storm':
            print(f"    Typical moves: {', '.join(p['typical_moves'][:3])}")
    print()
    
    # Test 3: Material advantage (simplification)
    print("=" * 60)
    print("TEST 3: Material Advantage (+2 pawns)")
    print("=" * 60)
    fen = "r3r1k1/5ppp/8/8/8/8/5PPP/R3R1K1 w - - 0 1"  # White up 2 pawns
    patterns = detector.detect_patterns(fen, player_rating=1800)
    print(f"Found {len(patterns)} applicable patterns:")
    for p in patterns:
        print(f"  - {p['pattern_name']} (confidence: {p['confidence']:.2f})")
    print()
    
    print("✓ Plan Detector tests completed")