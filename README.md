# ARCHESS MVP - Chess Coaching MCP Server

An intelligent chess coaching system powered by Stockfish and the Model Context Protocol (MCP). Provides AI-assisted game analysis, strategic pattern detection, and personalized feedback.

## 🎯 Features

### Core Analysis Tools
- **Position Analysis** - Deep evaluation with skill-adapted depth
- **Move Evaluation** - Classify moves (excellent/good/inaccuracy/mistake/blunder)
- **Strategic Plan Detection** - Recognize 6+ strategic patterns (minority attack, pawn storms, etc.)
- **Plan Evaluation** - Validate strategic plans with Stockfish
- **Complete Game Analysis** - Analyze full PGN games with critical moments detection

### Intelligent Features
- 🎓 **Skill Adaptation** - Analysis depth adjusts to player rating (800-3000 ELO)
- 🔍 **Pattern Recognition** - Detects missed strategic opportunities
- 💡 **Interactive Suggestions** - Recommends when/what to ask the student
- 📊 **Recurring Patterns** - Identifies weaknesses across games
- ✨ **Human-Readable Output** - Formatted reports with emoji indicators

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Stockfish chess engine

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/mcp-chess-coach.git
cd mcp-chess-coach
```

2. **Install dependencies**
```bash
# With uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv pip install -e .

# Or with pip
pip install -e .
```

3. **Download Stockfish**
- Get it from stockfishchess.org
- Place the executable in bin/stockfish.exe (Windows) or bin/stockfish (Unix)

### Running Tests
```bash
# Test all components
python tests/test_tools.py
python tests/test_mcp_server.py
python tests/test_plan_tools.py
python tests/test_game_analysis.py

# Test individual modules
python src/analyzers/plan_detector.py
python src/utils/pgn_parser.py
python src/utils/output_formatter.py
```

## 📚 MCP Tools
### 1. **analyze_position**
   
Analyze a chess position comprehensively.

**Input:**

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "player_rating": 1500
}
```
**Output:**

Evaluation (numerical)
Best move
Principal variation
Analysis depth used

### 2. **evaluate_move**
Evaluate the quality of a specific move.

**Input:**

```json
{
  "fen_before": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "move_played": "e7e5",
  "player_rating": 1500
}
```
**Output:**
- Move quality (excellent/good/inaccuracy/mistake/blunder)
- Evaluation loss
- Best alternative
- Explanation

### 3. **detect_strategic_plans**

Detect applicable strategic patterns in a position.

**Input:**
```json
{
  "fen": "r1bq1rk1/pp2bppp/2n1pn2/3p4/2PP4/2N1PN2/PP2BPPP/R1BQK2R w KQ - 0 9",
  "player_rating": 1500
}
```
**Output:**

- List of applicable patterns
- Confidence scores
- Typical moves for each pattern
- Skill appropriateness

**Supported Patterns:**

- Minority Attack
- Kingside Pawn Storm
- Central Pawn Break
- File Opening Pressure
- Piece Simplification
- Knight Outpost Establishment


### 4.**evaluate_plan**

Validate a strategic plan with Stockfish.

**Input:**

```json
{
  "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "plan_description": "Central control with e5",
  "candidate_moves": ["e7e5", "g8f6", "f8c5"],
  "player_rating": 1500
}
```
**Output:**

- Soundness rating (excellent/good/dubious/bad)
- Evaluation change
- Stockfish agreement
- Execution difficulty
- Identified risks
- Alternative plans


### 5. **analyze_game**

Analyze a complete game from PGN.

**Input:**

```json
{
  "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4...",
  "player_rating": 1500,
  "analyze_all_moves": false
}
```

**Output:**

- Game statistics (blunders, mistakes, brilliancies)
- Critical moments with explanations
- Phase-by-phase breakdown (opening/middlegame/endgame)
- Strategic patterns detected
- Interactive checkpoint suggestions
- Recurring pattern analysis

**Analysis Modes:**

- analyze_all_moves: false - Quick scan (every 3 moves, ~1-3 seconds)
- analyze_all_moves: true - Thorough analysis (every move, ~10-30 seconds)

## 🎓 Usage with Claude Desktop

### 1. **Configure Claude Desktop**

Create/edit %APPDATA%\Claude\claude_desktop_config.json (Windows) or ~/Library/Application Support/Claude/claude_desktop_config.json (Mac):

```json{
  "mcpServers": {
    "chess-coach": {
      "command": "-venv activation- python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\path\\to\\Archess",
      "env": {
        "PYTHONPATH": "C:\\path\\to\\Archess"
      }
    }
  }
}
```
### 2. **Restart Claude Desktop**
### 3. **Use the tools:**
```
Can you analyze this position: 
rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1
I'm rated 1500.
```

## 🏗️ Architecture
```
mcp-chess-coach/
├── src/
│   ├── server.py                 # MCP server
│   ├── stockfish_wrapper.py      # Stockfish UCI interface
│   ├── analyzers/
│   │   ├── plan_detector.py      # Pattern recognition
│   │   ├── plan_evaluator.py     # Plan validation
│   │   ├── game_analyzer.py      # Full game analysis
│   │   └── pattern_tracker.py    # Recurring patterns
│   └── utils/
│       ├── pgn_parser.py         # PGN parsing
│       ├── output_formatter.py   # Output formatting
│       └── interaction_helper.py # Checkpoint suggestions
├── config/
│   └── strategic_patterns.json   # Pattern definitions
├── tests/                        # Test suite
└── bin/                          # Stockfish binary (not tracked)
```

## 🎯 Skill Adaptation

Analysis adapts to player rating:

| Rating Range | Depth | Complexity | Focus |
|---------------|--------|-------------|---------|
| 800–1200 | 12 | Basic patterns only | Tactics, simple plans |
| 1200–1800 | 18 | Intermediate patterns | Strategy, calculation |
| 1800–2200 | 22 | Advanced patterns | Deep plans, subtlety |
| 2200+ | 25 | All patterns | Expert-level analysis |

## 🧪 Development
### Running the server directly
```bash
python -m src.server
```

### Adding new strategic patterns
Edit config/strategic_patterns.json:

```json
{
  "id": "new_pattern",
  "name": "Pattern Name",
  "description": "What the pattern does",
  "skill_level": "intermediate",
  "typical_rating_range": [1400, 2200],
  "complexity": 5,
  "preconditions": [
    "condition_to_check"
  ],
  "typical_moves": ["e4", "d4"],
  "key_ideas": ["Idea 1", "Idea 2"]
}
```

Implement precondition check in src/analyzers/plan_detector.py.

## 📊 Performance

- **Position Analysis:** ~0.1-0.5s (depth 12-25)
- **Move Evaluation:** ~0.2-0.7s
- **Pattern Detection:** ~0.05s (no Stockfish)
- **Plan Evaluation:** ~0.5-2s (multi-move)
- **Quick Game Analysis:** ~1-3s (10-move game)
- **Thorough Game Analysis:** ~10-30s (20-move game)

## 🤝 Areas for improvement:

- More strategic patterns (20+ total)
- Opening book integration
- Multi-game tracking (database)
- Advanced pattern matching (piece maneuvers)
- Endgame tablebase integration
- Web interface

## 📧 Contact
Andrea Nappi - andi.nappi@gmail.com
Project Link: https://github.com/ANDREAaNAPPI/ARCHESS_MVP

























