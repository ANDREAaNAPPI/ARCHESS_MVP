"""
PGN Parser - Parse e analizza file PGN di partite.
"""
import chess
import chess.pgn
from io import StringIO
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class GameMove:
    """Rappresenta una singola mossa nella partita."""
    move_number: int
    player: str  # "white" or "black"
    move_uci: str
    move_san: str
    fen_before: str
    fen_after: str
    comment: str = ""


@dataclass
class ParsedGame:
    """Rappresenta una partita parsata."""
    headers: Dict[str, str]
    moves: List[GameMove]
    result: str
    total_moves: int
    
    def get_move_at(self, move_number: int, color: str = "white") -> Optional[GameMove]:
        """Ottiene una specifica mossa."""
        for move in self.moves:
            if move.move_number == move_number and move.player == color:
                return move
        return None
    
    def get_position_at_move(self, move_number: int, color: str = "white") -> Optional[str]:
        """Ottiene FEN dopo una specifica mossa."""
        move = self.get_move_at(move_number, color)
        return move.fen_after if move else None


class PGNParser:
    """Parser per file PGN."""
    
    def parse_pgn(self, pgn_string: str) -> ParsedGame:
        """
        Parse una stringa PGN e ritorna struttura analizzabile.
        
        Args:
            pgn_string: Stringa contenente il PGN
            
        Returns:
            ParsedGame con moves e metadata
        """
        pgn_io = StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)
        
        if game is None:
            raise ValueError("Invalid PGN format")
        
        # Extract headers
        headers = dict(game.headers)
        
        # Parse moves
        moves = []
        board = game.board()
        move_number = 1
        
        for node in game.mainline():
            move = node.move
            
            # FEN prima della mossa
            fen_before = board.fen()
            
            # Player (white o black)
            player = "white" if board.turn == chess.WHITE else "black"
            
            # Esegui mossa
            move_san = board.san(move)
            move_uci = move.uci()
            board.push(move)
            
            # FEN dopo la mossa
            fen_after = board.fen()
            
            # Comment (se presente)
            comment = node.comment if node.comment else ""
            
            # Crea GameMove
            game_move = GameMove(
                move_number=move_number,
                player=player,
                move_uci=move_uci,
                move_san=move_san,
                fen_before=fen_before,
                fen_after=fen_after,
                comment=comment
            )
            
            moves.append(game_move)
            
            # Incrementa move number dopo mossa nera
            if player == "black":
                move_number += 1
        
        result = headers.get("Result", "*")
        
        return ParsedGame(
            headers=headers,
            moves=moves,
            result=result,
            total_moves=len(moves)
        )
    
    def parse_pgn_file(self, filepath: str) -> ParsedGame:
        """Parse un file PGN."""
        with open(filepath, 'r', encoding='utf-8') as f:
            pgn_string = f.read()
        
        return self.parse_pgn(pgn_string)
    
    def get_phase_boundaries(self, parsed_game: ParsedGame) -> Dict[str, int]:
        """
        Identifica boundaries delle fasi (opening/middlegame/endgame).
        
        Logic semplificata:
        - Opening: mosse 1-12
        - Middlegame: 13-30 (o fino a quando restano poche pezzi)
        - Endgame: da quando si entra in finale
        
        Returns:
            Dict con move numbers: {"opening_end": 12, "middlegame_end": 28}
        """
        # Simplified heuristic
        opening_end = min(12, parsed_game.total_moves // 3)
        
        # Endgame detection: quando ci sono <= 12 pezzi o regine scambiate
        endgame_start = None
        
        for i, move in enumerate(parsed_game.moves):
            board = chess.Board(move.fen_after)
            piece_count = len(board.piece_map())
            
            has_queens = (
                bool(board.pieces(chess.QUEEN, chess.WHITE)) or
                bool(board.pieces(chess.QUEEN, chess.BLACK))
            )
            
            if piece_count <= 12 or not has_queens:
                # Conta mosse vere (non ply)
                endgame_start = (i // 2) + 1
                break
        
        if endgame_start is None:
            endgame_start = parsed_game.total_moves
        
        return {
            "opening_end": opening_end,
            "middlegame_end": endgame_start,
            "endgame_start": endgame_start
        }


# Test
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    print("Testing PGN Parser...\n")
    
    # Sample PGN
    sample_pgn = """
[Event "Test Game"]
[Site "Online"]
[Date "2024.01.15"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5 4. c3 Nf6 5. d4 exd4 6. cxd4 Bb4+ 
7. Nc3 Nxe4 8. O-O Bxc3 9. d5 Bf6 10. Re1 Ne7 11. Rxe4 d6 
12. Bg5 Bxg5 13. Nxg5 O-O 14. Nxh7 Kxh7 15. Qh5+ Kg8 16. Rh4 1-0
"""
    
    parser = PGNParser()
    
    print("=" * 60)
    print("TEST 1: Parse PGN")
    print("=" * 60)
    
    game = parser.parse_pgn(sample_pgn)
    
    print(f"Event: {game.headers.get('Event')}")
    print(f"White: {game.headers.get('White')}")
    print(f"Black: {game.headers.get('Black')}")
    print(f"Result: {game.result}")
    print(f"Total moves: {game.total_moves}")
    print()
    
    print("First 5 moves:")
    for move in game.moves[:5]:
        print(f"  {move.move_number}. {move.move_san} ({move.player})")
    print()
    
    print("=" * 60)
    print("TEST 2: Get specific position")
    print("=" * 60)
    
    fen_at_move_5 = game.get_position_at_move(5, "white")
    print(f"Position after 5.d4:")
    print(f"  {fen_at_move_5}")
    print()
    
    print("=" * 60)
    print("TEST 3: Phase boundaries")
    print("=" * 60)
    
    phases = parser.get_phase_boundaries(game)
    print(f"Opening ends at move: {phases['opening_end']}")
    print(f"Middlegame ends at move: {phases['middlegame_end']}")
    print()
    
    print("✓ PGN Parser tests completed")