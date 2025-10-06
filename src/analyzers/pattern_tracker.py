"""
Pattern Tracker - Identifica pattern ricorrenti negli errori del giocatore.
"""
from typing import List, Dict, Any
from collections import Counter, defaultdict


class PatternTracker:
    """Traccia e identifica pattern ricorrenti."""
    
    def analyze_recurring_patterns(
        self,
        critical_moments: List[Any],
        patterns_detected: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analizza pattern ricorrenti negli errori.
        
        Args:
            critical_moments: Momenti critici dalla partita
            patterns_detected: Pattern strategici rilevati
            
        Returns:
            Dict con pattern ricorrenti identificati
        """
        # 1. Analizza tipi di errori
        error_types = Counter(m.type for m in critical_moments if m.type in ["blunder", "mistake", "inaccuracy"])
        
        # 2. Analizza pattern strategici mancati
        missed_patterns = [p for p in patterns_detected if not p.get('followed')]
        pattern_names = Counter(p['pattern_name'] for p in missed_patterns)
        
        # 3. Analizza fasi con più problemi
        phase_issues = defaultdict(int)
        for moment in critical_moments:
            if moment.type in ["blunder", "mistake"]:
                # Simplified phase detection
                if moment.move_number <= 12:
                    phase_issues["opening"] += 1
                elif moment.move_number <= 30:
                    phase_issues["middlegame"] += 1
                else:
                    phase_issues["endgame"] += 1
        
        # 4. Genera insights
        insights = self._generate_insights(error_types, pattern_names, phase_issues)
        
        return {
            "error_types": dict(error_types),
            "missed_patterns": dict(pattern_names),
            "phase_issues": dict(phase_issues),
            "insights": insights
        }
    
    def _generate_insights(
        self,
        error_types: Counter,
        pattern_names: Counter,
        phase_issues: Dict[str, int]
    ) -> List[str]:
        """Genera insights basati sui pattern."""
        insights = []
        
        # Error type insights
        if error_types.get("blunder", 0) >= 2:
            insights.append("⚠️ Multiple blunders detected - focus on tactical awareness and calculation")
        
        if error_types.get("inaccuracy", 0) >= 3:
            insights.append("📊 Several inaccuracies - consider spending more time on positional evaluation")
        
        # Pattern insights
        if pattern_names:
            most_missed = pattern_names.most_common(1)[0]
            insights.append(f"🎯 Pattern to study: {most_missed[0]} (missed {most_missed[1]} times)")
        
        # Phase insights
        if phase_issues:
            weakest_phase = max(phase_issues.items(), key=lambda x: x[1])
            if weakest_phase[1] >= 2:
                insights.append(f"📚 Focus area: {weakest_phase[0]} ({weakest_phase[1]} mistakes)")
        
        if not insights:
            insights.append("✓ Good game overall - few recurring issues detected")
        
        return insights
    
    def format_recurring_patterns(self, analysis: Dict[str, Any]) -> str:
        """Formatta analisi pattern ricorrenti."""
        lines = [
            "",
            "RECURRING PATTERNS ANALYSIS",
            "=" * 60
        ]
        
        # Error distribution
        if analysis["error_types"]:
            lines.append("Error Distribution:")
            for error_type, count in analysis["error_types"].items():
                lines.append(f"  - {error_type}: {count}")
            lines.append("")
        
        # Missed patterns
        if analysis["missed_patterns"]:
            lines.append("Most Frequently Missed Patterns:")
            for pattern, count in sorted(
                analysis["missed_patterns"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]:
                lines.append(f"  - {pattern}: {count} times")
            lines.append("")
        
        # Phase weaknesses
        if analysis["phase_issues"]:
            lines.append("Mistakes by Phase:")
            for phase, count in analysis["phase_issues"].items():
                lines.append(f"  - {phase}: {count}")
            lines.append("")
        
        # Key insights
        lines.append("KEY INSIGHTS:")
        for insight in analysis["insights"]:
            lines.append(f"  {insight}")
        
        return "\n".join(lines)


# Test
if __name__ == "__main__":
    print("Testing Pattern Tracker...\n")
    
    from dataclasses import dataclass
    
    @dataclass
    class MockMoment:
        move_number: int
        type: str
    
    tracker = PatternTracker()
    
    # Mock data
    critical_moments = [
        MockMoment(5, "blunder"),
        MockMoment(8, "mistake"),
        MockMoment(15, "blunder"),
        MockMoment(25, "inaccuracy"),
        MockMoment(28, "inaccuracy")
    ]
    
    patterns = [
        {"pattern_name": "Central Pawn Break", "followed": False},
        {"pattern_name": "Kingside Storm", "followed": True},
        {"pattern_name": "Central Pawn Break", "followed": False},
    ]
    
    analysis = tracker.analyze_recurring_patterns(critical_moments, patterns)
    
    print(tracker.format_recurring_patterns(analysis))
    
    print("\n✓ Pattern Tracker tests completed")