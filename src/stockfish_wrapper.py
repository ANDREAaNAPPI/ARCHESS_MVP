"""
Wrapper per gestire il processo Stockfish via UCI protocol.
"""
import subprocess
from typing import Optional, List, Dict, Any
import os
import re


class StockfishWrapper:
    def __init__(self, stockfish_path: str = None, default_depth: int = 20):
        """
        Inizializza wrapper Stockfish.
        
        Args:
            stockfish_path: Path al binario Stockfish. 
                           Se None, usa bin/stockfish.exe
            default_depth: Profondità di analisi di default
        """
        if stockfish_path is None:
            # Default: bin/stockfish.exe nella root del progetto
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            stockfish_path = os.path.join(project_root, "bin", "stockfish.exe")
        
        if not os.path.exists(stockfish_path):
            raise FileNotFoundError(f"Stockfish not found at {stockfish_path}")
        
        self.stockfish_path = stockfish_path
        self.default_depth = default_depth
        self.process: Optional[subprocess.Popen] = None
        
    def start(self):
        """Avvia il processo Stockfish."""
        if self.process is not None:
            return  # Già avviato
        
        self.process = subprocess.Popen(
            self.stockfish_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Inizializza UCI mode
        self._send_command("uci")
        self._wait_for("uciok")
        self._send_command("ucinewgame")
        
    def _send_command(self, command: str):
        """Invia comando a Stockfish."""
        if self.process is None:
            raise RuntimeError("Stockfish process not started")
        
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
    
    def _wait_for(self, expected: str) -> List[str]:
        """
        Legge output fino a trovare la stringa attesa.
        Ritorna tutte le linee lette.
        """
        lines = []
        while True:
            line = self.process.stdout.readline().strip()
            if line:  # Ignora linee vuote
                lines.append(line)
            if expected in line:
                break
        return lines
    
    def is_ready(self) -> bool:
        """Verifica se Stockfish è pronto."""
        self._send_command("isready")
        response = self._wait_for("readyok")
        return any("readyok" in line for line in response)
    
    def set_position(self, fen: str):
        """
        Imposta la posizione da analizzare.
        
        Args:
            fen: Posizione in notazione FEN
        """
        self._send_command(f"position fen {fen}")
    
    def analyze_position(self, fen: str, depth: int = None) -> Dict[str, Any]:
        """
        Analizza una posizione e ritorna evaluation e best move.
        
        Args:
            fen: Posizione in notazione FEN
            depth: Profondità di analisi (se None, usa default)
            
        Returns:
            Dict con:
            - best_move: str (es. "e2e4")
            - evaluation: float (in pawns, prospettiva bianco)
            - mate_in: int | None (se c'è matto forzato)
            - pv: List[str] (principal variation - linea principale)
        """
        if depth is None:
            depth = self.default_depth
        
        self.set_position(fen)
        self._send_command(f"go depth {depth}")
        
        lines = self._wait_for("bestmove")
        
        # Parse output
        result = {
            "best_move": None,
            "evaluation": 0.0,
            "mate_in": None,
            "pv": []
        }
        
        # Trova la linea con info finale (quella prima di bestmove)
        info_lines = [l for l in lines if l.startswith("info") and "pv" in l]
        
        if info_lines:
            last_info = info_lines[-1]  # Ultima linea info = analisi completa
            
            # Parse evaluation
            if "score cp" in last_info:
                # Centipawns (100 cp = 1 pawn)
                match = re.search(r"score cp (-?\d+)", last_info)
                if match:
                    result["evaluation"] = int(match.group(1)) / 100.0
            
            elif "score mate" in last_info:
                # Matto forzato
                match = re.search(r"score mate (-?\d+)", last_info)
                if match:
                    result["mate_in"] = int(match.group(1))
                    # Convention: eval molto alta se mate positivo
                    result["evaluation"] = 100.0 if result["mate_in"] > 0 else -100.0
            
            # Parse principal variation
            pv_match = re.search(r"pv (.+)$", last_info)
            if pv_match:
                result["pv"] = pv_match.group(1).split()
        
        # Parse best move
        bestmove_line = [l for l in lines if l.startswith("bestmove")]
        if bestmove_line:
            parts = bestmove_line[0].split()
            if len(parts) >= 2:
                result["best_move"] = parts[1]
        
        return result
    
    def get_top_moves(self, fen: str, num_moves: int = 3, depth: int = None) -> List[Dict[str, Any]]:
        """
        Ottiene le top N mosse migliori per una posizione.
        
        Args:
            fen: Posizione FEN
            num_moves: Numero di mosse da ritornare
            depth: Profondità analisi
            
        Returns:
            Lista di dict, ognuno con best_move, evaluation, pv
        """
        # Nota: per ottenere multipv serve configurare Stockfish
        # Per ora ritorniamo solo la best move come lista di 1 elemento
        # TODO: implementare MultiPV quando serve
        
        analysis = self.analyze_position(fen, depth)
        return [analysis]
    
    def evaluate_move(self, fen: str, move: str, depth: int = None) -> Dict[str, Any]:
        """
        Valuta la qualità di una specifica mossa.
        
        Args:
            fen: Posizione FEN prima della mossa
            move: Mossa in notazione UCI (es. "e2e4")
            depth: Profondità analisi
            
        Returns:
            Dict con:
            - move_eval: evaluation dopo la mossa
            - best_move_eval: evaluation della mossa migliore
            - eval_loss: differenza (negativo = mossa peggiore)
        """
        if depth is None:
            depth = self.default_depth
        
        # 1. Analizza posizione originale per trovare best move
        best_analysis = self.analyze_position(fen, depth)
        
        # 2. Gioca la mossa dell'utente e valuta
        self.set_position(fen)
        self._send_command(f"position fen {fen} moves {move}")
        self._send_command(f"go depth {depth}")
        
        lines = self._wait_for("bestmove")
        
        # Parse evaluation dopo la mossa
        move_eval = 0.0
        info_lines = [l for l in lines if l.startswith("info") and "score" in l]
        
        if info_lines:
            last_info = info_lines[-1]
            if "score cp" in last_info:
                match = re.search(r"score cp (-?\d+)", last_info)
                if match:
                    # Importante: inverti segno perché è il turno dell'avversario
                    move_eval = -int(match.group(1)) / 100.0
            elif "score mate" in last_info:
                match = re.search(r"score mate (-?\d+)", last_info)
                if match:
                    mate_in = -int(match.group(1))
                    move_eval = 100.0 if mate_in > 0 else -100.0
        
        return {
            "move": move,
            "move_eval": move_eval,
            "best_move": best_analysis["best_move"],
            "best_move_eval": best_analysis["evaluation"],
            "eval_loss": move_eval - best_analysis["evaluation"]
        }
    
    def quit(self):
        """Chiude processo Stockfish."""
        if self.process is not None:
            self._send_command("quit")
            self.process.wait(timeout=5)
            self.process = None


# Test rapido
if __name__ == "__main__":
    print("Testing Stockfish wrapper...")
    sf = StockfishWrapper(default_depth=15)
    sf.start()
    
    if sf.is_ready():
        print("✓ Stockfish is ready!")
    
    # Test 1: Analizza posizione iniziale dopo 1.e4
    print("\n--- Test 1: Analyze position after 1.e4 ---")
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    result = sf.analyze_position(fen, depth=15)
    print(f"Best move: {result['best_move']}")
    print(f"Evaluation: {result['evaluation']:+.2f}")
    print(f"PV (first 5): {' '.join(result['pv'][:5])}")
    
    # Test 2: Valuta una mossa specifica
    print("\n--- Test 2: Evaluate move Nc6 ---")
    eval_result = sf.evaluate_move(fen, "b8c6", depth=15)
    print(f"Move played: {eval_result['move']}")
    print(f"Eval after move: {eval_result['move_eval']:+.2f}")
    print(f"Best move was: {eval_result['best_move']}")
    print(f"Best eval: {eval_result['best_move_eval']:+.2f}")
    print(f"Eval loss: {eval_result['eval_loss']:+.2f}")
    
    sf.quit()
    print("\n✓ All tests completed")