"""
Output Formatter - Formatta output dei tools in modo human-friendly.
"""
from typing import Dict, List, Any
import json


class OutputFormatter:
    """Formatta output per essere facilmente consumato da LLM."""
    
    @staticmethod
    def format_position_analysis(data: Dict[str, Any]) -> str:
        """Formatta analisi posizione."""
        lines = [
            "POSITION ANALYSIS",
            "=" * 50,
            f"Evaluation: {data['evaluation']}",
            f"Best move: {data['best_move']}",
            f"Analysis depth: {data['analysis_depth']}",
            f"Player rating: {data['player_rating']}",
            ""
        ]
        
        if data.get('principal_variation'):
            lines.append(f"Principal variation: {data['principal_variation']}")
        
        if data.get('mate_in'):
            lines.append(f"⚠️ Mate in {data['mate_in']} moves!")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_move_evaluation(data: Dict[str, Any]) -> str:
        """Formatta valutazione mossa."""
        quality_emoji = {
            "excellent": "✓",
            "good": "✓",
            "inaccuracy": "⚠️",
            "mistake": "❌",
            "blunder": "❌❌"
        }
        
        emoji = quality_emoji.get(data['move_quality'], "")
        
        lines = [
            "MOVE EVALUATION",
            "=" * 50,
            f"{emoji} Move: {data['move_played']} - Quality: {data['move_quality'].upper()}",
            "",
            f"Evaluation after move: {data['evaluation_after_move']}",
            f"Best move was: {data['best_move']} (eval: {data['best_move_evaluation']})",
            f"Evaluation loss: {data['evaluation_loss']}",
            "",
            f"Analysis depth: {data['analysis_depth']}"
        ]
        
        return "\n".join(lines)
    
    @staticmethod
    def format_strategic_plans(data: Dict[str, Any]) -> str:
        """Formatta pattern strategici rilevati."""
        lines = [
            "STRATEGIC PATTERNS DETECTED",
            "=" * 50,
            f"Position rating: {data['player_rating']}",
            f"Patterns found: {data['patterns_found']}",
            ""
        ]
        
        for i, pattern in enumerate(data['patterns'], 1):
            skill_note = "✓ Appropriate" if pattern['skill_appropriate'] else "⚠️ Advanced"
            
            lines.extend([
                f"{i}. {pattern['name']} (confidence: {pattern['confidence']})",
                f"   {skill_note} | Complexity: {pattern['complexity']}/10",
                f"   {pattern['description']}",
                f"   Typical moves: {', '.join(pattern['typical_moves'][:3])}",
                ""
            ])
            
            if i >= 3:  # Limit to top 3
                break
        
        return "\n".join(lines)
    
    @staticmethod
    def format_plan_evaluation(data: Dict[str, Any]) -> str:
        """Formatta valutazione piano."""
        soundness_emoji = {
            "excellent": "✓✓",
            "good": "✓",
            "dubious": "⚠️",
            "bad": "❌"
        }
        
        emoji = soundness_emoji.get(data['soundness'], "")
        
        lines = [
            "PLAN EVALUATION",
            "=" * 50,
            f"Plan: {data['plan_description']}",
            f"{emoji} Soundness: {data['soundness'].upper()}",
            "",
            f"Evaluation change: {data.get('evaluation_change', 'N/A')}",
            f"Final evaluation: {data.get('final_evaluation', 'N/A')}",
            f"Stockfish agrees: {'Yes' if data.get('stockfish_agrees') else 'No'}",
            f"Execution difficulty: {data.get('execution_difficulty', 'N/A')}",
            f"Moves in plan: {data.get('move_count', 0)}",
            ""
        ]
        
        if data.get('risks'):
            lines.append("⚠️ Risks:")
            for risk in data['risks']:
                lines.append(f"  - {risk}")
            lines.append("")
        
        if data.get('alternatives'):
            lines.append("Alternative moves:")
            for alt in data['alternatives'][:3]:
                lines.append(f"  - {alt.get('move', 'N/A')}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_game_analysis(data: Dict[str, Any]) -> str:
        """Formatta analisi partita completa."""
        stats = data['statistics']
        
        lines = [
            "GAME ANALYSIS REPORT",
            "=" * 60,
            f"Event: {data['game_info'].get('Event', 'Unknown')}",
            f"White: {data['game_info'].get('White', 'Player')}",
            f"Black: {data['game_info'].get('Black', 'Opponent')}",
            f"Result: {stats['result']}",
            "",
            "STATISTICS",
            "-" * 60,
            f"Total moves: {stats['total_moves']}",
            f"Critical moments: {stats['critical_moments_count']}",
            f"  ❌❌ Blunders: {stats['blunders']}",
            f"  ❌ Mistakes: {stats['mistakes']}",
            f"  ⭐ Brilliancies: {stats['brilliancies']}",
            "",
            "CRITICAL MOMENTS",
            "-" * 60
        ]
        
        for i, moment in enumerate(data['critical_moments'][:5], 1):
            type_emoji = {
                "blunder": "❌❌",
                "mistake": "❌",
                "brilliant": "⭐",
                "inaccuracy": "⚠️",
                "critical_position": "🔥"
            }
            
            emoji = type_emoji.get(moment['type'], "")
            
            lines.extend([
                f"{i}. Move {moment['move']} ({moment['player']})",
                f"   {emoji} {moment['type'].upper()}",
                f"   Eval swing: {moment['eval_swing']}",
                f"   {moment['explanation']}",
                ""
            ])
        
        # Phase summaries
        lines.extend([
            "",
            "PHASE BREAKDOWN",
            "-" * 60
        ])
        
        for phase_name in ['opening', 'middlegame', 'endgame']:
            phase = data['phases'][phase_name]
            lines.append(f"{phase_name.capitalize()}: {phase.get('summary', 'N/A')}")
        
        # Patterns
        if data.get('patterns_detected_count', 0) > 0:
            lines.extend([
                "",
                "STRATEGIC PATTERNS",
                "-" * 60,
                f"Total patterns detected: {data['patterns_detected_count']}"
            ])
            
            for pattern in data.get('patterns_sample', [])[:3]:
                followed = "✓ Applied" if pattern.get('followed') else "⚠️ Missed"
                lines.append(f"  {followed}: {pattern['pattern_name']} (move {pattern['move_number']})")

        # Interaction suggestions
        if data.get('interaction_suggestions'):
            from .interaction_helper import InteractionHelper
            helper = InteractionHelper()
            suggestions_text = helper.format_checkpoint_suggestions(
                data['interaction_suggestions']
            )
            lines.extend([
                "",
                suggestions_text
            ])
        
        # Recurring patterns
        if data.get('recurring_patterns'):
            from ..analyzers.pattern_tracker import PatternTracker
            tracker = PatternTracker()
            recurring_text = tracker.format_recurring_patterns(data['recurring_patterns'])
            lines.append(recurring_text)
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    formatter = OutputFormatter()
    
    # Test position analysis
    print(formatter.format_position_analysis({
        'evaluation': '+0.5',
        'best_move': 'e7e5',
        'principal_variation': 'e7e5 g1f3 b8c6',
        'analysis_depth': 18,
        'player_rating': 1500
    }))
    
    print("\n" + "=" * 60 + "\n")
    
    # Test move evaluation
    print(formatter.format_move_evaluation({
        'move_played': 'Nc6',
        'move_quality': 'good',
        'evaluation_after_move': '+0.2',
        'best_move': 'e5',
        'best_move_evaluation': '+0.3',
        'evaluation_loss': '-0.1',
        'analysis_depth': 18
    }))