"""
Discount Pattern Inference Service

Intelligently infers discount types from legacy notes patterns.
Used during AR reconstruction to classify percentage discounts as Early Bird,
special discounts, etc. based on context clues and historical patterns.
"""

import re
from datetime import date
from decimal import Decimal
from typing import Any


class DiscountPatternInference:
    """
    Service to infer discount types from legacy notes patterns.

    This service analyzes legacy receipt notes to determine whether
    percentage discounts are Early Bird, special discounts, or other types
    based on contextual patterns, timing, and business rules.
    """

    def __init__(self) -> None:
        """Initialize pattern inference with common patterns."""
        self.early_bird_indicators = [
            # Direct mentions
            r"early\s*bird",
            r"pay\s*by",
            r"before\s*\d+",
            r"deadline",
            r"on\s*time",
            r"advance",
            r"prompt",
            # Date-based patterns (common early bird patterns)
            r"\d+%.*pay.*by",
            r"\d+%.*before",
            r"\d+%.*deadline",
            r"pay.*\d+%.*by",
            # Common percentage + timing combinations
            r"10%.*all.*pay\s*by",
            r"15%.*students.*pay\s*by",
            r"5%.*pay.*before",
        ]

        self.special_discount_indicators = [
            # Identity-based discounts
            r"monk",
            r"staff",
            r"employee",
            r"teacher",
            r"sibling",
            r"alumni",
            r"scholarship",
            r"sponsor",
            # Financial hardship
            r"hardship",
            r"special\s*case",
            r"exception",
            r"approved\s*by",
            # Academic performance
            r"honor",
            r"academic",
            r"merit",
        ]

        self.admin_fee_indicators = [
            r"admin\s*fee",
            r"administrative",
            r"processing\s*fee",
            r"registration\s*fee",
            r"late\s*fee",
            r"penalty",
        ]

        self.cash_plan_indicators = [
            r"cash\s*plan",
            r"payment\s*plan",
            r"installment",
            r"monthly",
            r"full\s*payment",
        ]

    def infer_discount_type(
        self,
        note: str,
        percentage: Decimal | None = None,
        receipt_date: date | None = None,
        term_start_date: date | None = None,
        student_type: str | None = None,
    ) -> tuple[str, float]:
        """
        Infer discount type from note patterns and context.

        Args:
            note: The legacy notes text
            percentage: Extracted percentage (if any)
            receipt_date: Date of the receipt
            term_start_date: Start date of the academic term
            student_type: Known student characteristics (monk, staff, etc.)

        Returns:
            Tuple of (discount_type, confidence_score)
            confidence_score is 0.0-1.0 indicating certainty
        """
        if not note:
            return "UNKNOWN", 0.0

        note_lower = note.lower().strip()

        # Check for explicit special discount indicators first
        special_score = self._check_special_patterns(note_lower, student_type)
        if special_score > 0.7:
            return self._determine_special_type(note_lower, student_type), special_score

        # Check for admin fee patterns
        admin_score = self._check_admin_patterns(note_lower)
        if admin_score > 0.6:
            return "ADMIN_FEE", admin_score

        # Check for cash plan patterns
        cash_score = self._check_cash_patterns(note_lower)
        if cash_score > 0.6:
            return "CASH_PLAN", cash_score

        # Check for early bird patterns
        early_bird_score = self._check_early_bird_patterns(note_lower, percentage, receipt_date, term_start_date)

        # If we have a percentage and timing context, likely early bird
        if percentage and early_bird_score > 0.3:
            return "EARLY_BIRD", early_bird_score

        # Default inference based on percentage patterns
        if percentage:
            return self._infer_from_percentage_context(note_lower, percentage, receipt_date, term_start_date)

        return "CUSTOM", 0.2

    def _check_early_bird_patterns(
        self, note: str, percentage: Decimal | None, receipt_date: date | None, term_start_date: date | None
    ) -> float:
        """Check for early bird discount patterns."""
        score = 0.0

        # Direct pattern matching
        for pattern in self.early_bird_indicators:
            if re.search(pattern, note, re.IGNORECASE):
                score += 0.3

        # Timing-based inference
        if receipt_date and term_start_date:
            days_before_term = (term_start_date - receipt_date).days
            if 10 <= days_before_term <= 60:  # Reasonable early bird window
                score += 0.4
            elif days_before_term > 60:  # Very early payment
                score += 0.6

        # Common early bird percentages
        if percentage:
            common_early_bird = [5, 10, 15, 20]
            if int(percentage) in common_early_bird:
                score += 0.2

        # Mass discount patterns (likely early bird campaigns)
        mass_patterns = [
            r"all\s+students",
            r"everyone\s+who",
            r"all\s+who\s+pay",
            r"students\s+pay\s+by",
        ]
        for pattern in mass_patterns:
            if re.search(pattern, note):
                score += 0.3

        return min(score, 1.0)

    def _check_special_patterns(self, note: str, student_type: str | None) -> float:
        """Check for special discount patterns."""
        score = 0.0

        # Direct pattern matching
        for pattern in self.special_discount_indicators:
            if re.search(pattern, note, re.IGNORECASE):
                score += 0.4

        # Student type correlation
        if student_type:
            if student_type.lower() in note:
                score += 0.5

        # Authority/approval patterns (indicates special case)
        authority_patterns = [
            r"approved\s+by",
            r"director\s+approval",
            r"dean\s+approval",
            r"special\s+approval",
        ]
        for pattern in authority_patterns:
            if re.search(pattern, note):
                score += 0.4

        return min(score, 1.0)

    def _determine_special_type(self, note: str, student_type: str | None) -> str:
        """Determine specific special discount type."""
        if re.search(r"monk", note):
            return "MONK"
        elif re.search(r"staff|employee|teacher", note):
            return "STAFF"
        elif re.search(r"sibling", note):
            return "SIBLING"
        elif re.search(r"scholarship|sponsor", note):
            return "SCHOLARSHIP"
        else:
            return "SPECIAL"

    def _check_admin_patterns(self, note: str) -> float:
        """Check for administrative fee patterns."""
        score = 0.0

        for pattern in self.admin_fee_indicators:
            if re.search(pattern, note, re.IGNORECASE):
                score += 0.5

        return min(score, 1.0)

    def _check_cash_patterns(self, note: str) -> float:
        """Check for cash payment plan patterns."""
        score = 0.0

        for pattern in self.cash_plan_indicators:
            if re.search(pattern, note, re.IGNORECASE):
                score += 0.4

        return min(score, 1.0)

    def _infer_from_percentage_context(
        self, note: str, percentage: Decimal, receipt_date: date | None, term_start_date: date | None
    ) -> tuple[str, float]:
        """
        Infer discount type from percentage and context when no clear patterns exist.

        This is the fallback logic for classifying percentage discounts.
        """
        # High percentages often indicate special circumstances
        if percentage >= 50:
            return "SPECIAL", 0.6

        # Common early bird percentages with timing context
        if percentage in [5, 10, 15, 20]:
            if receipt_date and term_start_date:
                days_before = (term_start_date - receipt_date).days
                if days_before > 7:  # Payment well before term starts
                    return "EARLY_BIRD", 0.7

        # Medium percentages without clear context
        if 20 <= percentage <= 50:
            return "SPECIAL", 0.4

        # Small percentages likely early bird or cash discounts
        if percentage <= 20:
            return "EARLY_BIRD", 0.5

        return "CUSTOM", 0.3

    def create_inferred_discount_rule(
        self,
        note: str,
        percentage: Decimal,
        discount_type: str,
        confidence: float,
        applies_to_cycle: str = "",
        applies_to_terms: list[str] | None = None,
    ) -> dict:
        """
        Create a DiscountRule configuration based on inference.

        Returns a dictionary that can be used to create or update a DiscountRule.
        """
        applies_to_terms = applies_to_terms or []

        # Generate rule name based on type and percentage
        if discount_type == "EARLY_BIRD":
            rule_name = f"Inferred Early Bird {percentage}%"
        elif discount_type in ["MONK", "STAFF", "SIBLING"]:
            rule_name = f"Inferred {discount_type.title()} {percentage}%"
        else:
            rule_name = f"Inferred {discount_type.title()} {percentage}%"

        # Create pattern text for future matching
        pattern_text = self._create_pattern_text(note, percentage, discount_type)

        return {
            "rule_name": rule_name,
            "rule_type": discount_type,
            "pattern_text": pattern_text,
            "discount_percentage": percentage,
            "applies_to_cycle": applies_to_cycle,
            "applies_to_terms": applies_to_terms,
            "is_active": confidence > 0.6,  # Only activate high-confidence rules
            # Store inference metadata
            "processing_metadata": {
                "inference_confidence": float(confidence),
                "source_note": note,
                "inference_method": "pattern_analysis",
                "created_by": "discount_pattern_inference_service",
            },
        }

    def _create_pattern_text(self, note: str, percentage: Decimal, discount_type: str) -> str:
        """Create a pattern text for future rule matching."""
        # Extract key words from the note
        note_words = re.findall(r"\w+", note.lower())

        # Common words to include in pattern
        key_words = []

        if discount_type == "EARLY_BIRD":
            early_words = ["pay", "by", "before", "deadline", "early", "advance"]
            key_words.extend([w for w in note_words if w in early_words])

        elif discount_type == "MONK":
            key_words.append("monk")

        elif discount_type == "STAFF":
            staff_words = ["staff", "employee", "teacher"]
            key_words.extend([w for w in note_words if w in staff_words])

        # Include percentage and generic terms
        pattern_parts = [f"{percentage}%", *key_words[:3]]  # Limit to avoid overly long patterns

        return " ".join(pattern_parts)

    def batch_infer_from_legacy_notes(self, receipt_data: list[dict]) -> list[dict]:
        """
        Batch process legacy receipt notes to infer discount rules.

        Args:
            receipt_data: List of dictionaries with receipt information
                Each should contain: note, amount, net_amount, receipt_date, term_id

        Returns:
            List of inferred discount rule configurations
        """
        inferred_rules = []
        seen_patterns = set()

        for receipt in receipt_data:
            note = receipt.get("Notes", "")
            amount = receipt.get("Amount", 0)
            net_amount = receipt.get("NetAmount", 0)
            receipt_date = receipt.get("receipt_date")

            # Calculate percentage if discount was applied
            if amount and net_amount and amount > net_amount:
                discount_amount = amount - net_amount
                percentage = (discount_amount / amount) * 100
                percentage = Decimal(str(round(percentage, 2)))

                # Infer discount type
                discount_type, confidence = self.infer_discount_type(
                    note=note, percentage=percentage, receipt_date=receipt_date
                )

                # Create rule configuration
                rule_config = self.create_inferred_discount_rule(
                    note=note, percentage=percentage, discount_type=discount_type, confidence=confidence
                )

                # Avoid duplicate patterns
                pattern_key = (discount_type, percentage)
                if pattern_key not in seen_patterns and confidence > 0.5:
                    inferred_rules.append(rule_config)
                    seen_patterns.add(pattern_key)

        return inferred_rules

    def analyze_legacy_discount_patterns(self, receipt_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze legacy data to identify discount patterns and generate a summary report.

        Returns a comprehensive analysis of discount patterns found in legacy data.
        """
        analysis: dict[str, Any] = {
            "total_receipts": len(receipt_data),
            "receipts_with_discounts": 0,
            "discount_patterns": {},
            "inferred_rules": [],
            "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
            "type_distribution": {},
        }

        for receipt in receipt_data:
            note = receipt.get("Notes", "")
            amount = receipt.get("Amount", 0)
            net_amount = receipt.get("NetAmount", 0)

            if amount and net_amount and amount > net_amount:
                current_count = analysis.get("receipts_with_discounts", 0)
                analysis["receipts_with_discounts"] = int(current_count) + 1

                discount_amount = amount - net_amount
                percentage = (discount_amount / amount) * 100
                percentage = Decimal(str(round(percentage, 2)))

                discount_type, confidence = self.infer_discount_type(
                    note=note, percentage=percentage, receipt_date=receipt.get("receipt_date")
                )

                # Track patterns
                pattern_key = f"{discount_type}_{percentage}%"
                patterns_dict = analysis.setdefault("discount_patterns", {})
                if pattern_key not in patterns_dict:
                    patterns_dict[pattern_key] = {"count": 0, "total_amount": 0, "sample_notes": []}

                patterns_dict[pattern_key]["count"] += 1
                patterns_dict[pattern_key]["total_amount"] += float(discount_amount)

                if len(patterns_dict[pattern_key]["sample_notes"]) < 3:
                    patterns_dict[pattern_key]["sample_notes"].append(note)

                # Track confidence distribution
                conf_dist = analysis.setdefault("confidence_distribution", {"high": 0, "medium": 0, "low": 0})
                if confidence >= 0.8:
                    conf_dist["high"] = conf_dist.get("high", 0) + 1
                elif confidence >= 0.5:
                    conf_dist["medium"] = conf_dist.get("medium", 0) + 1
                else:
                    conf_dist["low"] = conf_dist.get("low", 0) + 1

                # Track type distribution
                type_dist = analysis.setdefault("type_distribution", {})
                type_dist[discount_type] = type_dist.get(discount_type, 0) + 1

        # Generate inferred rules
        analysis["inferred_rules"] = self.batch_infer_from_legacy_notes(receipt_data)

        return analysis
