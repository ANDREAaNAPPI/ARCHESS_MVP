"""
Interaction Helper - Genera suggerimenti per checkpoint interattivi.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class InteractionCheckpoint:
    """Rappresenta un punto di interazione suggerito."""
    move_number: int
    question_type: str  # "clarification" | "thinking" | "alternative" | "learning"
    question: str
    context: str
    priority: int  # 1-5, dove 5 = molto importante


class InteractionHelper:
    """Genera suggerimenti per interazioni con l'utente."""
    
    def generate_checkpoints(
        self,
        critical_moments: List[Any],
        patterns_detected: List[Dict[str, Any]],
        player_rating: int
    ) -> List[InteractionCheckpoint]:
        """
        Genera checkpoint suggeriti per interazione.
        
        Args:
            critical_moments: Momenti critici dalla game analysis
            patterns_detected: Pattern strategici rilevati
            player_rating: Rating giocatore
            
        Returns:
            Lista di checkpoint suggeriti, ordinati per priorità
        """
        checkpoints = []
        
        # 1. Checkpoint per blunders/mistakes
        for moment in critical_moments:
            if moment.type in ["blunder", "mistake"]:
                checkpoints.append(self._create_mistake_checkpoint(moment, player_rating))
        
        # 2. Checkpoint per brilliancies
        for moment in critical_moments:
            if moment.type == "brilliant":
                checkpoints.append(self._create_brilliancy_checkpoint(moment))
        
        # 3. Checkpoint per pattern missed
        for pattern in patterns_detected:
            if not pattern.get('followed'):
                checkpoints.append(self._create_pattern_checkpoint(pattern, player_rating))
        
        # 4. Checkpoint per posizioni critiche
        critical_positions = [m for m in critical_moments if m.type == "critical_position"]
        if critical_positions:
            # Prendi la prima critical position
            checkpoints.append(self._create_critical_position_checkpoint(critical_positions[0]))
        
        # Sort by priority (highest first)
        checkpoints.sort(key=lambda x: x.priority, reverse=True)
        
        # Limit to top 5 checkpoints (avoid overwhelming)
        return checkpoints[:5]
    
    def _create_mistake_checkpoint(
        self,
        moment: Any,
        player_rating: int
    ) -> InteractionCheckpoint:
        """Crea checkpoint per un errore."""
        
        # Adjust question complexity based on rating
        if player_rating < 1400:
            question = (
                f"At move {moment.move_number}, you played {moment.move_san}. "
                f"Did you see any immediate threats or tactics here?"
            )
        else:
            question = (
                f"Move {moment.move_number}: {moment.move_san} lost significant evaluation. "
                f"What was your plan with this move? "
                f"Did you consider {moment.best_move}?"
            )
        
        priority = 5 if moment.type == "blunder" else 4
        
        return InteractionCheckpoint(
            move_number=moment.move_number,
            question_type="clarification",
            question=question,
            context=f"Player made a {moment.type} with eval swing {moment.eval_swing}",
            priority=priority
        )
    
    def _create_brilliancy_checkpoint(self, moment: Any) -> InteractionCheckpoint:
        """Checkpoint per mossa brillante."""
        return InteractionCheckpoint(
            move_number=moment.move_number,
            question_type="learning",
            question=(
                f"Excellent move at {moment.move_number}! {moment.move_san} was a great find. "
                f"Can you explain what you saw in this position?"
            ),
            context=f"Player found a brilliant move",
            priority=3
        )
    
    def _create_pattern_checkpoint(
        self,
        pattern: Dict[str, Any],
        player_rating: int
    ) -> InteractionCheckpoint:
        """Checkpoint per pattern strategico mancato."""
        
        pattern_name = pattern['pattern_name']
        move_num = pattern['move_number']
        
        # Adjust question based on skill appropriateness
        if pattern.get('skill_appropriate', True):
            question = (
                f"Around move {move_num}, there was an opportunity for {pattern_name}. "
                f"Did you notice this possibility? If yes, why did you choose a different plan?"
            )
            priority = 4
        else:
            # Advanced pattern - just mention it
            question = (
                f"FYI: Around move {move_num}, there was an advanced tactical theme ({pattern_name}). "
                f"This is typically seen at higher ratings. Would you like me to explain it?"
            )
            priority = 2
        
        return InteractionCheckpoint(
            move_number=move_num,
            question_type="alternative",
            question=question,
            context=f"Pattern {pattern_name} was available but not followed",
            priority=priority
        )
    
    def _create_critical_position_checkpoint(self, moment: Any) -> InteractionCheckpoint:
        """Checkpoint per posizione critica."""
        return InteractionCheckpoint(
            move_number=moment.move_number,
            question_type="thinking",
            question=(
                f"At move {moment.move_number}, the position became very sharp. "
                f"What were you thinking about here? "
                f"What did you consider as the main plan?"
            ),
            context="Critical position with sharp play",
            priority=3
        )
    
    def format_checkpoint_suggestions(
        self,
        checkpoints: List[InteractionCheckpoint]
    ) -> str:
        """Formatta checkpoint in modo human-readable."""
        if not checkpoints:
            return "No interactive checkpoints suggested for this game."
        
        lines = [
            "SUGGESTED INTERACTION CHECKPOINTS",
            "=" * 60,
            "These are key moments where asking the student questions would be valuable:",
            ""
        ]
        
        priority_labels = {
            5: "🔴 CRITICAL",
            4: "🟠 HIGH",
            3: "🟡 MEDIUM",
            2: "🟢 LOW",
            1: "⚪ OPTIONAL"
        }
        
        for i, cp in enumerate(checkpoints, 1):
            label = priority_labels.get(cp.priority, "")
            
            lines.extend([
                f"{i}. Move {cp.move_number} - {label} Priority",
                f"   Type: {cp.question_type}",
                f"   Question: {cp.question}",
                ""
            ])
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    print("Testing Interaction Helper...\n")
    
    from dataclasses import dataclass
    
    # Mock critical moment
    @dataclass
    class MockMoment:
        move_number: int
        type: str
        move_san: str
        eval_swing: float
        best_move: str
    
    helper = InteractionHelper()
    
    # Create mock data
    critical_moments = [
        MockMoment(5, "blunder", "Nxf7", -2.5, "d6"),
        MockMoment(8, "brilliant", "Qh5+", 1.2, "Qh5+"),
        MockMoment(12, "critical_position", "O-O", 0.8, "O-O")
    ]
    
    patterns = [
        {
            "move_number": 7,
            "pattern_name": "Kingside Pawn Storm",
            "confidence": 0.8,
            "followed": False,
            "skill_appropriate": True
        }
    ]
    
    # Generate checkpoints
    checkpoints = helper.generate_checkpoints(critical_moments, patterns, 1500)
    
    print(f"Generated {len(checkpoints)} checkpoints\n")
    print(helper.format_checkpoint_suggestions(checkpoints))
    
    print("\n✓ Interaction Helper tests completed")