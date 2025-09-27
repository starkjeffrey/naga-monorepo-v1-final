"""AI Predictions API v2 for machine learning insights.

This module provides AI-powered prediction endpoints with:
- Student success prediction models
- Risk assessment algorithms
- Grade prediction and early warning systems
- Scholarship matching algorithms
- Academic pathway recommendations
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from ninja import Query, Router

from ..v1.auth import jwt_auth
from .schemas import PredictionRequest, PredictionResult

logger = logging.getLogger(__name__)

router = Router(auth=jwt_auth, tags=["ai-predictions"])


@router.post("/predict/", response=PredictionResult)
def make_prediction(request, prediction_request: PredictionRequest):
    """Make AI predictions based on input data and model type."""

    model_type = prediction_request.model_type
    input_data = prediction_request.input_data
    confidence_threshold = prediction_request.confidence_threshold

    if model_type == "success_prediction":
        # Mock student success prediction
        # In production, this would call a trained ML model

        # Extract features from input data
        gpa = input_data.get("gpa", 3.0)
        attendance_rate = input_data.get("attendance_rate", 0.85)
        engagement_score = input_data.get("engagement_score", 0.7)
        financial_stress = input_data.get("financial_stress", False)
        family_support = input_data.get("family_support", True)

        # Simple prediction algorithm (would be ML model in production)
        success_score = 0.0

        # GPA contribution (40% weight)
        success_score += (gpa / 4.0) * 0.4

        # Attendance contribution (30% weight)
        success_score += attendance_rate * 0.3

        # Engagement contribution (20% weight)
        success_score += engagement_score * 0.2

        # Stress factors (negative impact)
        if financial_stress:
            success_score -= 0.15

        # Support factors (positive impact)
        if family_support:
            success_score += 0.1

        # Clamp to 0-1 range
        success_score = max(0.0, min(1.0, success_score))

        confidence = 0.85  # Mock confidence score

        features_used = ["gpa", "attendance_rate", "engagement_score", "financial_stress", "family_support"]

        # Generate explanation
        if success_score >= 0.8:
            explanation = "High likelihood of academic success based on strong GPA, good attendance, and engagement."
        elif success_score >= 0.6:
            explanation = "Moderate likelihood of success. Consider additional support for improvement."
        else:
            explanation = "Low likelihood of success. Immediate intervention recommended."

        recommendations = []
        if attendance_rate < 0.8:
            recommendations.append("Improve attendance through scheduling support")
        if gpa < 3.0:
            recommendations.append("Academic tutoring and study skills support")
        if financial_stress:
            recommendations.append("Financial aid counseling and emergency assistance")
        if engagement_score < 0.6:
            recommendations.append("Increase engagement through extracurricular activities")

        return PredictionResult(
            prediction=success_score,
            confidence=confidence,
            model_version="success_predictor_v2.1",
            features_used=features_used,
            explanation=explanation,
            recommendations=recommendations
        )

    elif model_type == "risk_assessment":
        # Mock risk assessment
        academic_risk = input_data.get("failing_courses", 0) / max(input_data.get("total_courses", 1), 1)
        financial_risk = 1.0 if input_data.get("overdue_payments", 0) > 0 else 0.0
        attendance_risk = 1.0 - input_data.get("attendance_rate", 0.9)

        overall_risk = (academic_risk * 0.4 + financial_risk * 0.3 + attendance_risk * 0.3)

        risk_level = "low"
        if overall_risk > 0.7:
            risk_level = "high"
        elif overall_risk > 0.4:
            risk_level = "medium"

        return PredictionResult(
            prediction=risk_level,
            confidence=0.82,
            model_version="risk_assessor_v1.5",
            features_used=["failing_courses", "overdue_payments", "attendance_rate"],
            explanation=f"Risk level: {risk_level} (score: {overall_risk:.2f})",
            recommendations=[
                "Monitor academic progress closely",
                "Provide financial counseling if needed",
                "Attendance intervention if below 80%"
            ]
        )

    elif model_type == "grade_prediction":
        # Mock grade prediction for next assignment/exam
        current_average = input_data.get("current_average", 75.0)
        study_hours = input_data.get("study_hours_per_week", 10)
        assignment_difficulty = input_data.get("assignment_difficulty", 0.5)  # 0-1 scale

        # Simple prediction model
        base_prediction = current_average

        # Adjust based on study effort
        if study_hours > 15:
            base_prediction += 5
        elif study_hours < 5:
            base_prediction -= 10

        # Adjust based on difficulty
        base_prediction -= (assignment_difficulty * 10)

        # Add some randomness for realism
        import random
        variance = random.uniform(-3, 3)
        predicted_grade = max(0, min(100, base_prediction + variance))

        return PredictionResult(
            prediction=predicted_grade,
            confidence=0.78,
            model_version="grade_predictor_v1.3",
            features_used=["current_average", "study_hours_per_week", "assignment_difficulty"],
            explanation=f"Predicted grade: {predicted_grade:.1f}% based on current performance and study patterns",
            recommendations=[
                f"Maintain {study_hours} hours of study per week" if study_hours >= 10 else "Increase study time to at least 10 hours per week",
                "Review difficult concepts with instructor" if assignment_difficulty > 0.7 else "Continue current study approach"
            ]
        )

    else:
        return {"error": f"Unknown model type: {model_type}"}


@router.get("/models/available/")
def get_available_models(request):
    """Get list of available AI prediction models."""

    models = [
        {
            "id": "success_prediction",
            "name": "Student Success Predictor",
            "description": "Predicts likelihood of academic success based on multiple factors",
            "version": "v2.1",
            "accuracy": 0.84,
            "last_updated": "2023-11-15T10:30:00Z",
            "input_features": [
                "gpa",
                "attendance_rate",
                "engagement_score",
                "financial_stress",
                "family_support"
            ],
            "output_type": "probability",
            "confidence_range": [0.7, 0.95]
        },
        {
            "id": "risk_assessment",
            "name": "Student Risk Assessor",
            "description": "Assesses risk level for student dropout or academic failure",
            "version": "v1.5",
            "accuracy": 0.79,
            "last_updated": "2023-10-20T14:15:00Z",
            "input_features": [
                "failing_courses",
                "overdue_payments",
                "attendance_rate",
                "engagement_metrics"
            ],
            "output_type": "categorical",
            "confidence_range": [0.6, 0.9]
        },
        {
            "id": "grade_prediction",
            "name": "Grade Predictor",
            "description": "Predicts expected grade for upcoming assignments or exams",
            "version": "v1.3",
            "accuracy": 0.72,
            "last_updated": "2023-11-01T09:45:00Z",
            "input_features": [
                "current_average",
                "study_hours_per_week",
                "assignment_difficulty",
                "previous_performance"
            ],
            "output_type": "numeric",
            "confidence_range": [0.5, 0.85]
        },
        {
            "id": "scholarship_matching",
            "name": "Scholarship Matcher",
            "description": "Matches students with suitable scholarship opportunities",
            "version": "v1.0",
            "accuracy": 0.88,
            "last_updated": "2023-09-30T16:20:00Z",
            "input_features": [
                "gpa",
                "financial_need",
                "program",
                "extracurricular_activities",
                "demographic_factors"
            ],
            "output_type": "ranked_list",
            "confidence_range": [0.6, 0.95]
        }
    ]

    return {
        "models": models,
        "total_count": len(models),
        "api_version": "v2.0",
        "last_updated": max(model["last_updated"] for model in models)
    }


@router.get("/models/{model_id}/performance/")
def get_model_performance(request, model_id: str):
    """Get detailed performance metrics for a specific model."""

    # Mock performance data
    performance_data = {
        "success_prediction": {
            "accuracy": 0.84,
            "precision": 0.81,
            "recall": 0.87,
            "f1_score": 0.84,
            "confusion_matrix": {
                "true_positive": 145,
                "false_positive": 24,
                "true_negative": 132,
                "false_negative": 19
            },
            "feature_importance": {
                "gpa": 0.35,
                "attendance_rate": 0.28,
                "engagement_score": 0.22,
                "financial_stress": 0.10,
                "family_support": 0.05
            },
            "training_data": {
                "total_samples": 2500,
                "training_samples": 2000,
                "validation_samples": 500,
                "last_retrained": "2023-11-15T10:30:00Z"
            }
        },
        "risk_assessment": {
            "accuracy": 0.79,
            "precision": 0.76,
            "recall": 0.83,
            "f1_score": 0.79,
            "confusion_matrix": {
                "true_positive": 98,
                "false_positive": 31,
                "true_negative": 156,
                "false_negative": 25
            },
            "feature_importance": {
                "failing_courses": 0.40,
                "overdue_payments": 0.30,
                "attendance_rate": 0.25,
                "engagement_metrics": 0.05
            },
            "training_data": {
                "total_samples": 1800,
                "training_samples": 1440,
                "validation_samples": 360,
                "last_retrained": "2023-10-20T14:15:00Z"
            }
        }
    }

    model_performance = performance_data.get(model_id)
    if not model_performance:
        return {"error": f"Model {model_id} not found"}

    return {
        "model_id": model_id,
        "performance": model_performance,
        "evaluation_date": datetime.now().isoformat(),
        "next_evaluation": (datetime.now() + timedelta(days=30)).isoformat()
    }


@router.post("/batch-predict/")
def batch_prediction(
    request,
    model_type: str,
    predictions: List[Dict[str, Any]],
    include_explanations: bool = True
):
    """Perform batch predictions for multiple data points."""

    results = []

    for i, input_data in enumerate(predictions):
        try:
            # Create individual prediction request
            prediction_request = PredictionRequest(
                model_type=model_type,
                input_data=input_data,
                confidence_threshold=0.7
            )

            # Get prediction (reuse the single prediction logic)
            result = make_prediction(request, prediction_request)

            # Add index for tracking
            result_dict = {
                "index": i,
                "prediction": result.prediction,
                "confidence": result.confidence,
                "model_version": result.model_version
            }

            if include_explanations:
                result_dict["explanation"] = result.explanation
                result_dict["recommendations"] = result.recommendations

            results.append(result_dict)

        except Exception as e:
            results.append({
                "index": i,
                "error": str(e),
                "status": "failed"
            })

    return {
        "model_type": model_type,
        "total_predictions": len(predictions),
        "successful_predictions": len([r for r in results if "error" not in r]),
        "failed_predictions": len([r for r in results if "error" in r]),
        "results": results,
        "processed_at": datetime.now().isoformat()
    }


@router.get("/insights/feature-analysis/")
def get_feature_analysis(
    request,
    model_id: str,
    student_segment: Optional[str] = Query(None, description="all, high_risk, high_performing")
):
    """Analyze feature importance and correlations for model insights."""

    # Mock feature analysis data
    analysis = {
        "success_prediction": {
            "feature_correlations": {
                "gpa_vs_success": 0.78,
                "attendance_vs_success": 0.65,
                "engagement_vs_success": 0.52,
                "financial_stress_vs_success": -0.43,
                "family_support_vs_success": 0.31
            },
            "feature_distributions": {
                "gpa": {"mean": 3.2, "std": 0.8, "min": 1.0, "max": 4.0},
                "attendance_rate": {"mean": 0.87, "std": 0.12, "min": 0.3, "max": 1.0},
                "engagement_score": {"mean": 0.73, "std": 0.18, "min": 0.1, "max": 1.0}
            },
            "segment_insights": {
                "high_performing": {
                    "avg_gpa": 3.8,
                    "avg_attendance": 0.95,
                    "key_factors": ["consistent_attendance", "high_engagement", "strong_study_habits"]
                },
                "at_risk": {
                    "avg_gpa": 2.1,
                    "avg_attendance": 0.67,
                    "key_factors": ["poor_attendance", "financial_stress", "low_engagement"]
                }
            }
        }
    }

    model_analysis = analysis.get(model_id, {})

    return {
        "model_id": model_id,
        "student_segment": student_segment or "all",
        "analysis": model_analysis,
        "generated_at": datetime.now().isoformat(),
        "insights": [
            "GPA shows strongest correlation with success outcomes",
            "Attendance rate is a key predictor of academic performance",
            "Financial stress significantly impacts success probability",
            "Early intervention for attendance issues can improve outcomes"
        ]
    }


# Export router
__all__ = ["router"]