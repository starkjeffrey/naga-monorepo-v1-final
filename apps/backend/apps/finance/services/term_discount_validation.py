"""
Term Discount Validation Service

Validates legacy discount rates against canonical discount rates for each term.
Identifies discrepancies and provides recommendations for business rule creation.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from apps.curriculum.models import Term
from apps.finance.models.ar_reconstruction import LegacyReceiptMapping
from apps.finance.models.discounts import DiscountRule


class DiscountValidationStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING_CANONICAL = "missing_canonical"
    SUSPICIOUS = "suspicious"
    REQUIRES_REVIEW = "requires_review"


@dataclass
class DiscountValidationResult:
    """Result of discount validation for a specific term and discount type."""

    term_code: str
    discount_type: str
    legacy_rate: Decimal
    canonical_rate: Decimal | None
    status: DiscountValidationStatus
    variance: Decimal | None
    variance_percentage: float | None
    sample_count: int
    confidence_score: float
    notes: str
    examples: list[dict[str, Any]]
    recommendations: list[str]


class TermDiscountValidator:
    """
    Validates discount rates across terms and provides canonical rate recommendations.
    """

    def __init__(self):
        self.validation_results = []
        self.term_analysis = {}
        self.discount_type_analysis = {}

        # Standard discount thresholds
        self.variance_thresholds = {
            "early_bird": Decimal("2.0"),  # 2% variance allowed
            "monk": Decimal("5.0"),  # 5% variance for special pricing
            "staff": Decimal("3.0"),  # 3% variance for employee discounts
            "sibling": Decimal("2.0"),  # 2% variance for family discounts
            "default": Decimal("1.0"),  # 1% default variance
        }

        # Expected canonical rates (can be configured)
        self.canonical_rates = {
            "early_bird": Decimal("10.0"),  # 10% early bird
            "monk": Decimal("15.0"),  # 15% monastic discount
            "staff": Decimal("20.0"),  # 20% employee discount
            "sibling": Decimal("5.0"),  # 5% sibling discount
        }

    def validate_all_terms(self) -> list[DiscountValidationResult]:
        """Validate discount rates for all terms with legacy data."""
        self.validation_results = []

        # Get all terms with legacy receipt mappings
        terms_with_data = LegacyReceiptMapping.objects.values_list("legacy_term_id", flat=True).distinct()

        for term_code in terms_with_data:
            self.validate_term_discounts(term_code)

        # Generate overall analysis
        self._generate_analysis_summary()

        return self.validation_results

    def validate_term_discounts(self, term_code: str) -> list[DiscountValidationResult]:
        """Validate discount rates for a specific term."""
        term_results = []

        # Get all discount records for this term
        discount_mappings = LegacyReceiptMapping.objects.filter(
            legacy_term_id=term_code,
            parsed_note_type__in=[
                "discount_percentage",
                "discount_early_bird",
                "discount_monk",
                "discount_staff",
                "discount_sibling",
            ],
            parsed_percentage_adjustment__isnull=False,
        ).exclude(parsed_percentage_adjustment="0")

        # Group by discount type
        discount_types = discount_mappings.values_list("parsed_note_type", flat=True).distinct()

        for discount_type in discount_types:
            result = self._validate_discount_type_for_term(term_code, discount_type, discount_mappings)
            if result:
                term_results.append(result)
                self.validation_results.append(result)

        return term_results

    def _validate_discount_type_for_term(
        self, term_code: str, discount_type: str, all_mappings
    ) -> DiscountValidationResult | None:
        """Validate a specific discount type for a term."""

        # Filter mappings for this discount type
        type_mappings = all_mappings.filter(parsed_note_type=discount_type)

        if not type_mappings.exists():
            return None

        # Calculate statistics
        rates = [
            float(mapping.parsed_percentage_adjustment)
            for mapping in type_mappings
            if mapping.parsed_percentage_adjustment
        ]

        if not rates:
            return None

        # Statistical analysis
        avg_rate = Decimal(str(sum(rates) / len(rates)))
        sample_count = len(rates)
        rate_variance = max(rates) - min(rates) if len(rates) > 1 else 0

        # Get canonical rate
        canonical_rate = self._get_canonical_rate(discount_type)

        # Determine validation status
        status, variance, variance_pct = self._determine_validation_status(
            avg_rate, canonical_rate, discount_type, rate_variance
        )

        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(sample_count, rate_variance, status)

        # Generate examples
        examples = self._get_validation_examples(type_mappings, limit=5)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            term_code, discount_type, avg_rate, canonical_rate, status, rate_variance
        )

        # Generate notes
        notes = self._generate_validation_notes(avg_rate, canonical_rate, rate_variance, sample_count)

        return DiscountValidationResult(
            term_code=term_code,
            discount_type=discount_type,
            legacy_rate=avg_rate,
            canonical_rate=canonical_rate,
            status=status,
            variance=variance,
            variance_percentage=variance_pct,
            sample_count=sample_count,
            confidence_score=confidence_score,
            notes=notes,
            examples=examples,
            recommendations=recommendations,
        )

    def _get_canonical_rate(self, discount_type: str) -> Decimal | None:
        """Get canonical discount rate for a discount type."""
        # Check if we have a configured DiscountRule
        try:
            rule = DiscountRule.objects.filter(
                rule_type=self._map_discount_type_to_rule_type(discount_type),
                is_active=True,
            ).first()

            if rule and rule.discount_percentage:
                return rule.discount_percentage
        except Exception:
            pass

        # Fall back to default canonical rates
        discount_key = discount_type.replace("discount_", "")
        return self.canonical_rates.get(discount_key)

    def _map_discount_type_to_rule_type(self, discount_type: str) -> str:
        """Map parsed note type to DiscountRule type."""
        mapping = {
            "discount_early_bird": "EARLY_BIRD",
            "discount_monk": "MONK",
            "discount_staff": "STAFF",
            "discount_sibling": "SIBLING",
            "discount_percentage": "CUSTOM",
        }
        return mapping.get(discount_type, "CUSTOM")

    def _determine_validation_status(
        self,
        legacy_rate: Decimal,
        canonical_rate: Decimal | None,
        discount_type: str,
        rate_variance: float,
    ) -> tuple[DiscountValidationStatus, Decimal | None, float | None]:
        """Determine validation status based on rates comparison."""

        if canonical_rate is None:
            return DiscountValidationStatus.MISSING_CANONICAL, None, None

        variance = abs(legacy_rate - canonical_rate)
        variance_pct = float(variance / canonical_rate * 100) if canonical_rate > 0 else 0

        # Get threshold for this discount type
        discount_key = discount_type.replace("discount_", "")
        threshold = self.variance_thresholds.get(discount_key, self.variance_thresholds["default"])

        # High internal variance suggests inconsistent application
        if rate_variance > 5.0:  # More than 5% variance within term
            return DiscountValidationStatus.SUSPICIOUS, variance, variance_pct

        # Check against threshold
        if variance <= threshold:
            return DiscountValidationStatus.VALID, variance, variance_pct
        elif variance <= threshold * 2:
            return DiscountValidationStatus.REQUIRES_REVIEW, variance, variance_pct
        else:
            return DiscountValidationStatus.INVALID, variance, variance_pct

    def _calculate_confidence_score(
        self, sample_count: int, rate_variance: float, status: DiscountValidationStatus
    ) -> float:
        """Calculate confidence score for validation result."""
        base_score = 0.5

        # Sample size factor (more samples = higher confidence)
        sample_factor = min(sample_count / 10, 1.0) * 0.3

        # Consistency factor (less variance = higher confidence)
        consistency_factor = max(0, (10 - rate_variance) / 10) * 0.2

        # Status factor
        status_factors = {
            DiscountValidationStatus.VALID: 0.3,
            DiscountValidationStatus.REQUIRES_REVIEW: 0.1,
            DiscountValidationStatus.INVALID: -0.1,
            DiscountValidationStatus.SUSPICIOUS: -0.2,
            DiscountValidationStatus.MISSING_CANONICAL: 0.0,
        }
        status_factor = status_factors.get(status, 0.0)

        confidence = base_score + sample_factor + consistency_factor + status_factor
        return max(0.0, min(1.0, confidence))

    def _get_validation_examples(self, mappings, limit: int = 5) -> list[dict[str, Any]]:
        """Get example records for validation result."""
        examples = []

        for mapping in mappings[:limit]:
            examples.append(
                {
                    "receipt_number": mapping.legacy_receipt_number,
                    "student_id": mapping.legacy_student_id,
                    "percentage": float(mapping.parsed_percentage_adjustment or 0),
                    "authority": mapping.parsed_authority or "Unknown",
                    "notes": (
                        mapping.legacy_notes[:100] + "..."
                        if len(mapping.legacy_notes or "") > 100
                        else mapping.legacy_notes
                    ),
                    "confidence": float(mapping.notes_processing_confidence or 0),
                }
            )

        return examples

    def _generate_recommendations(
        self,
        term_code: str,
        discount_type: str,
        legacy_rate: Decimal,
        canonical_rate: Decimal | None,
        status: DiscountValidationStatus,
        rate_variance: float,
    ) -> list[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        if status == DiscountValidationStatus.MISSING_CANONICAL:
            recommendations.append(f"Create DiscountRule for {discount_type} with rate {legacy_rate}%")
            recommendations.append(f"Set term-specific discount_end_date for {term_code}")

        elif status == DiscountValidationStatus.INVALID:
            if canonical_rate:
                recommendations.append(
                    f"Review {discount_type} rate: legacy {legacy_rate}% vs canonical {canonical_rate}%"
                )
                recommendations.append("Consider updating canonical rate or investigating historical context")

        elif status == DiscountValidationStatus.SUSPICIOUS:
            recommendations.append(f"High variance ({rate_variance:.1f}%) suggests inconsistent application")
            recommendations.append("Review individual receipts for authority and approval patterns")

        elif status == DiscountValidationStatus.REQUIRES_REVIEW:
            recommendations.append("Minor variance detected - review for term-specific adjustments")

        if rate_variance > 3.0:
            recommendations.append("Consider implementing stricter approval workflows")

        # Term-specific recommendations
        try:
            term = Term.objects.get(code=term_code)
            if not term.discount_end_date:
                recommendations.append(f"Set discount_end_date for term {term_code}")
        except Term.DoesNotExist:
            recommendations.append(f"Ensure term {term_code} exists in system")

        return recommendations

    def _generate_validation_notes(
        self,
        legacy_rate: Decimal,
        canonical_rate: Decimal | None,
        rate_variance: float,
        sample_count: int,
    ) -> str:
        """Generate descriptive notes for validation result."""
        notes_parts = []

        notes_parts.append(f"Based on {sample_count} legacy receipt(s)")

        if canonical_rate:
            notes_parts.append(f"Legacy average: {legacy_rate}%, Canonical: {canonical_rate}%")
        else:
            notes_parts.append(f"Legacy average: {legacy_rate}% (no canonical rate defined)")

        if rate_variance > 0:
            notes_parts.append(f"Internal variance: {rate_variance:.1f}%")

        return " | ".join(notes_parts)

    def _generate_analysis_summary(self):
        """Generate overall analysis summary."""
        self.term_analysis = {}
        self.discount_type_analysis = {}

        # Group by term
        for result in self.validation_results:
            term = result.term_code
            if term not in self.term_analysis:
                self.term_analysis[term] = {
                    "total_discount_types": 0,
                    "valid_types": 0,
                    "invalid_types": 0,
                    "missing_canonical": 0,
                    "requires_review": 0,
                    "avg_confidence": 0.0,
                }

            analysis = self.term_analysis[term]
            analysis["total_discount_types"] += 1

            if result.status == DiscountValidationStatus.VALID:
                analysis["valid_types"] += 1
            elif result.status == DiscountValidationStatus.INVALID:
                analysis["invalid_types"] += 1
            elif result.status == DiscountValidationStatus.MISSING_CANONICAL:
                analysis["missing_canonical"] += 1
            elif result.status == DiscountValidationStatus.REQUIRES_REVIEW:
                analysis["requires_review"] += 1

            analysis["avg_confidence"] += result.confidence_score

        # Calculate averages
        for _term, analysis in self.term_analysis.items():
            if analysis["total_discount_types"] > 0:
                analysis["avg_confidence"] /= analysis["total_discount_types"]

    def get_term_summary(self, term_code: str) -> dict[str, Any]:
        """Get validation summary for a specific term."""
        term_results = [r for r in self.validation_results if r.term_code == term_code]

        if not term_results:
            return {}

        return {
            "term_code": term_code,
            "total_discount_types": len(term_results),
            "validation_results": term_results,
            "overall_status": self._get_overall_term_status(term_results),
            "priority_actions": self._get_priority_actions(term_results),
        }

    def _get_overall_term_status(self, results: list[DiscountValidationResult]) -> str:
        """Get overall validation status for a term."""
        if any(r.status == DiscountValidationStatus.INVALID for r in results):
            return "CRITICAL"
        elif any(r.status == DiscountValidationStatus.SUSPICIOUS for r in results):
            return "WARNING"
        elif any(r.status == DiscountValidationStatus.REQUIRES_REVIEW for r in results):
            return "REVIEW_NEEDED"
        elif any(r.status == DiscountValidationStatus.MISSING_CANONICAL for r in results):
            return "SETUP_REQUIRED"
        else:
            return "VALID"

    def _get_priority_actions(self, results: list[DiscountValidationResult]) -> list[str]:
        """Get priority actions for a term."""
        actions = []

        for result in results:
            if result.status == DiscountValidationStatus.MISSING_CANONICAL:
                actions.append(f"Create {result.discount_type} rule ({result.legacy_rate}%)")
            elif result.status == DiscountValidationStatus.INVALID:
                actions.append(f"Review {result.discount_type} rate variance")

        return actions[:3]  # Top 3 priority actions

    def generate_comprehensive_report(self) -> dict[str, Any]:
        """Generate comprehensive validation report."""
        return {
            "validation_summary": {
                "total_terms_analyzed": len(self.term_analysis),
                "total_validation_results": len(self.validation_results),
                "status_breakdown": self._get_status_breakdown(),
                "confidence_metrics": self._get_confidence_metrics(),
            },
            "term_analysis": self.term_analysis,
            "validation_results": [
                {
                    "term_code": r.term_code,
                    "discount_type": r.discount_type,
                    "legacy_rate": float(r.legacy_rate),
                    "canonical_rate": (float(r.canonical_rate) if r.canonical_rate else None),
                    "status": r.status.value,
                    "variance": float(r.variance) if r.variance else None,
                    "variance_percentage": r.variance_percentage,
                    "sample_count": r.sample_count,
                    "confidence_score": r.confidence_score,
                    "notes": r.notes,
                    "recommendations": r.recommendations,
                    "examples": r.examples,
                }
                for r in self.validation_results
            ],
            "recommendations": self._get_global_recommendations(),
        }

    def _get_status_breakdown(self) -> dict[str, int]:
        """Get breakdown of validation statuses."""
        breakdown = {}
        for status in DiscountValidationStatus:
            breakdown[status.value] = sum(1 for r in self.validation_results if r.status == status)
        return breakdown

    def _get_confidence_metrics(self) -> dict[str, float]:
        """Get confidence metrics."""
        if not self.validation_results:
            return {}

        confidences = [r.confidence_score for r in self.validation_results]
        return {
            "average_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "max_confidence": max(confidences),
        }

    def _get_global_recommendations(self) -> list[str]:
        """Get global recommendations for discount system."""
        recommendations = []

        # Missing canonical rates
        missing_canonical = [
            r for r in self.validation_results if r.status == DiscountValidationStatus.MISSING_CANONICAL
        ]
        if missing_canonical:
            recommendations.append(f"Create {len(missing_canonical)} missing DiscountRule configurations")

        # High variance issues
        suspicious = [r for r in self.validation_results if r.status == DiscountValidationStatus.SUSPICIOUS]
        if suspicious:
            recommendations.append(f"Review {len(suspicious)} discount types with high variance")

        # Term setup
        terms_without_dates = []
        for result in self.validation_results:
            try:
                term = Term.objects.get(code=result.term_code)
                if not term.discount_end_date:
                    terms_without_dates.append(result.term_code)
            except Term.DoesNotExist:
                pass

        if terms_without_dates:
            recommendations.append(f"Set discount_end_date for {len(set(terms_without_dates))} terms")

        return recommendations
