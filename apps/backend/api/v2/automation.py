"""Automation API v2 for workflow management.

This module provides workflow automation endpoints with:
- Workflow definition and management
- Trigger configuration (schedule, event, manual)
- Step execution and monitoring
- Workflow analytics and optimization
- Template library for common workflows
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from ninja import Query, Router

from ..v1.auth import jwt_auth
from .schemas import WorkflowDefinition, WorkflowExecution

logger = logging.getLogger(__name__)

router = Router(auth=jwt_auth, tags=["automation"])


# Mock workflow storage
WORKFLOWS = {}
EXECUTIONS = {}


@router.get("/workflows/", response=List[WorkflowDefinition])
def get_workflows(
    request,
    is_active: Optional[bool] = Query(None),
    trigger_type: Optional[str] = Query(None)
):
    """Get all workflow definitions."""

    sample_workflows = [
        WorkflowDefinition(
            workflow_id=uuid4(),
            name="Payment Reminder Automation",
            description="Automatically send payment reminders 7, 3, and 1 days before due date",
            trigger_type="schedule",
            steps=[
                {
                    "id": "check_due_invoices",
                    "type": "query",
                    "description": "Find invoices due in next 7 days",
                    "parameters": {"days_ahead": 7}
                },
                {
                    "id": "send_reminders",
                    "type": "notification",
                    "description": "Send email reminders to students",
                    "parameters": {"template": "payment_reminder"}
                }
            ],
            is_active=True,
            last_run=datetime.now() - timedelta(hours=24),
            next_run=datetime.now() + timedelta(hours=24)
        ),
        WorkflowDefinition(
            workflow_id=uuid4(),
            name="Grade Publication Workflow",
            description="Automatically publish grades and notify students",
            trigger_type="event",
            steps=[
                {
                    "id": "validate_grades",
                    "type": "validation",
                    "description": "Validate all grades are entered",
                    "parameters": {"min_completion": 0.95}
                },
                {
                    "id": "publish_grades",
                    "type": "action",
                    "description": "Publish grades to student portal",
                    "parameters": {}
                },
                {
                    "id": "notify_students",
                    "type": "notification",
                    "description": "Send grade availability notifications",
                    "parameters": {"template": "grade_available"}
                }
            ],
            is_active=True,
            last_run=datetime.now() - timedelta(hours=6),
            next_run=None  # Event-triggered
        )
    ]

    # Apply filters
    if is_active is not None:
        sample_workflows = [w for w in sample_workflows if w.is_active == is_active]

    if trigger_type:
        sample_workflows = [w for w in sample_workflows if w.trigger_type == trigger_type]

    return sample_workflows


@router.post("/workflows/", response=WorkflowDefinition)
def create_workflow(
    request,
    name: str,
    description: str,
    trigger_type: str,
    steps: List[Dict[str, Any]],
    trigger_config: Dict[str, Any] = {},
    is_active: bool = True
):
    """Create a new workflow definition."""

    workflow_id = uuid4()

    # Validate steps
    for i, step in enumerate(steps):
        if "id" not in step:
            step["id"] = f"step_{i+1}"
        if "type" not in step:
            return {"error": f"Step {i+1} missing required 'type' field"}

    workflow = WorkflowDefinition(
        workflow_id=workflow_id,
        name=name,
        description=description,
        trigger_type=trigger_type,
        steps=steps,
        is_active=is_active,
        last_run=None,
        next_run=None
    )

    # Calculate next run for scheduled workflows
    if trigger_type == "schedule" and "interval_hours" in trigger_config:
        workflow.next_run = datetime.now() + timedelta(hours=trigger_config["interval_hours"])

    WORKFLOWS[str(workflow_id)] = workflow

    logger.info("Created workflow: %s with %d steps", name, len(steps))

    return workflow


@router.get("/workflows/{workflow_id}/", response=WorkflowDefinition)
def get_workflow(request, workflow_id: UUID):
    """Get a specific workflow definition."""

    workflow = WORKFLOWS.get(str(workflow_id))
    if not workflow:
        return {"error": "Workflow not found"}

    return workflow


@router.post("/workflows/{workflow_id}/execute/", response=WorkflowExecution)
def execute_workflow(
    request,
    workflow_id: UUID,
    input_data: Dict[str, Any] = {},
    dry_run: bool = False
):
    """Execute a workflow manually."""

    workflow = WORKFLOWS.get(str(workflow_id))
    if not workflow:
        return {"error": "Workflow not found"}

    execution_id = uuid4()

    execution = WorkflowExecution(
        execution_id=execution_id,
        workflow_id=workflow_id,
        status="running",
        started_at=datetime.now(),
        completed_at=None,
        steps_completed=0,
        total_steps=len(workflow.steps),
        logs=[]
    )

    EXECUTIONS[str(execution_id)] = execution

    # Simulate step execution
    for i, step in enumerate(workflow.steps):
        step_start = datetime.now()

        try:
            # Simulate step execution
            if step["type"] == "query":
                # Simulate database query
                execution.logs.append({
                    "step_id": step["id"],
                    "timestamp": step_start.isoformat(),
                    "level": "info",
                    "message": f"Executing query: {step['description']}"
                })
                # Simulate processing time
                import time
                if not dry_run:
                    time.sleep(0.1)

            elif step["type"] == "notification":
                # Simulate notification sending
                execution.logs.append({
                    "step_id": step["id"],
                    "timestamp": step_start.isoformat(),
                    "level": "info",
                    "message": f"Sending notifications: {step['description']}"
                })

            elif step["type"] == "action":
                # Simulate action execution
                execution.logs.append({
                    "step_id": step["id"],
                    "timestamp": step_start.isoformat(),
                    "level": "info",
                    "message": f"Executing action: {step['description']}"
                })

            elif step["type"] == "validation":
                # Simulate validation
                execution.logs.append({
                    "step_id": step["id"],
                    "timestamp": step_start.isoformat(),
                    "level": "info",
                    "message": f"Validation passed: {step['description']}"
                })

            execution.steps_completed += 1

            execution.logs.append({
                "step_id": step["id"],
                "timestamp": datetime.now().isoformat(),
                "level": "success",
                "message": f"Step completed successfully"
            })

        except Exception as e:
            execution.status = "failed"
            execution.logs.append({
                "step_id": step["id"],
                "timestamp": datetime.now().isoformat(),
                "level": "error",
                "message": f"Step failed: {str(e)}"
            })
            break

    # Update execution status
    if execution.steps_completed == len(workflow.steps):
        execution.status = "completed"
    elif execution.status != "failed":
        execution.status = "completed"

    execution.completed_at = datetime.now()

    # Update workflow last run
    if not dry_run:
        workflow.last_run = datetime.now()

    logger.info(
        "Workflow execution %s completed with status: %s",
        execution_id,
        execution.status
    )

    return execution


@router.get("/workflows/{workflow_id}/executions/", response=List[WorkflowExecution])
def get_workflow_executions(
    request,
    workflow_id: UUID,
    status: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """Get execution history for a workflow."""

    # Mock execution history
    sample_executions = []
    for i in range(min(limit, 5)):  # Generate up to 5 sample executions
        execution_id = uuid4()
        start_time = datetime.now() - timedelta(hours=i*6, minutes=i*15)

        status_options = ["completed", "failed", "running"]
        exec_status = status if status else status_options[i % len(status_options)]

        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=exec_status,
            started_at=start_time,
            completed_at=start_time + timedelta(minutes=2) if exec_status != "running" else None,
            steps_completed=3 if exec_status == "completed" else 2,
            total_steps=3,
            logs=[
                {
                    "step_id": "step_1",
                    "timestamp": start_time.isoformat(),
                    "level": "info",
                    "message": "Step 1 completed"
                },
                {
                    "step_id": "step_2",
                    "timestamp": (start_time + timedelta(minutes=1)).isoformat(),
                    "level": "info",
                    "message": "Step 2 completed"
                }
            ]
        )
        sample_executions.append(execution)

    return sample_executions


@router.get("/templates/", response=List[Dict[str, Any]])
def get_workflow_templates(request, category: Optional[str] = Query(None)):
    """Get workflow templates for common automation scenarios."""

    templates = [
        {
            "id": "payment_reminder",
            "name": "Payment Reminder Automation",
            "category": "finance",
            "description": "Automatically send payment reminders based on due dates",
            "trigger_type": "schedule",
            "estimated_setup_time": "5 minutes",
            "benefits": [
                "Reduce manual reminder work",
                "Improve payment collection rates",
                "Consistent communication timing"
            ],
            "steps_template": [
                {
                    "type": "query",
                    "description": "Find upcoming due invoices",
                    "configurable_fields": ["days_ahead", "student_filters"]
                },
                {
                    "type": "notification",
                    "description": "Send reminder notifications",
                    "configurable_fields": ["template", "channels"]
                }
            ]
        },
        {
            "id": "enrollment_workflow",
            "name": "Student Enrollment Processing",
            "category": "academic",
            "description": "Automate student enrollment approval and notification",
            "trigger_type": "event",
            "estimated_setup_time": "10 minutes",
            "benefits": [
                "Faster enrollment processing",
                "Automatic prerequisite checking",
                "Immediate student notification"
            ],
            "steps_template": [
                {
                    "type": "validation",
                    "description": "Check prerequisites and capacity",
                    "configurable_fields": ["prerequisite_rules", "capacity_limits"]
                },
                {
                    "type": "action",
                    "description": "Process enrollment",
                    "configurable_fields": ["approval_criteria"]
                },
                {
                    "type": "notification",
                    "description": "Notify student of enrollment status",
                    "configurable_fields": ["success_template", "failure_template"]
                }
            ]
        },
        {
            "id": "grade_publication",
            "name": "Grade Publication Workflow",
            "category": "academic",
            "description": "Automatically publish grades when ready and notify students",
            "trigger_type": "manual",
            "estimated_setup_time": "8 minutes",
            "benefits": [
                "Ensure grade completeness before publication",
                "Immediate student notification",
                "Audit trail for grade publication"
            ],
            "steps_template": [
                {
                    "type": "validation",
                    "description": "Validate grade completeness",
                    "configurable_fields": ["completion_threshold"]
                },
                {
                    "type": "action",
                    "description": "Publish grades",
                    "configurable_fields": ["publication_scope"]
                },
                {
                    "type": "notification",
                    "description": "Notify students",
                    "configurable_fields": ["notification_template"]
                }
            ]
        }
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    return templates


@router.post("/templates/{template_id}/instantiate/", response=WorkflowDefinition)
def create_workflow_from_template(
    request,
    template_id: str,
    name: str,
    configuration: Dict[str, Any] = {}
):
    """Create a workflow instance from a template."""

    template_configs = {
        "payment_reminder": {
            "description": "Automatically send payment reminders based on due dates",
            "trigger_type": "schedule",
            "steps": [
                {
                    "id": "find_due_invoices",
                    "type": "query",
                    "description": "Find invoices due in next 7 days",
                    "parameters": {
                        "days_ahead": configuration.get("days_ahead", 7),
                        "student_filters": configuration.get("student_filters", {})
                    }
                },
                {
                    "id": "send_reminders",
                    "type": "notification",
                    "description": "Send payment reminder notifications",
                    "parameters": {
                        "template": configuration.get("template", "payment_reminder"),
                        "channels": configuration.get("channels", ["email"])
                    }
                }
            ]
        }
    }

    template_config = template_configs.get(template_id)
    if not template_config:
        return {"error": "Template not found"}

    workflow_id = uuid4()

    workflow = WorkflowDefinition(
        workflow_id=workflow_id,
        name=name,
        description=template_config["description"],
        trigger_type=template_config["trigger_type"],
        steps=template_config["steps"],
        is_active=True,
        last_run=None,
        next_run=datetime.now() + timedelta(hours=24) if template_config["trigger_type"] == "schedule" else None
    )

    WORKFLOWS[str(workflow_id)] = workflow

    logger.info("Created workflow from template %s: %s", template_id, name)

    return workflow


@router.get("/analytics/workflow-performance/")
def get_workflow_analytics(
    request,
    date_range: int = Query(30, description="Days to look back"),
    workflow_id: Optional[UUID] = Query(None)
):
    """Get workflow performance analytics."""

    # Mock analytics data
    analytics = {
        "total_executions": 156,
        "successful_executions": 142,
        "failed_executions": 14,
        "success_rate": 0.91,
        "average_execution_time": 45.2,  # seconds
        "most_active_workflows": [
            {"name": "Payment Reminder Automation", "executions": 45},
            {"name": "Grade Publication Workflow", "executions": 32},
            {"name": "Enrollment Processing", "executions": 28}
        ],
        "execution_trends": [
            {"date": "2023-12-01", "executions": 12},
            {"date": "2023-12-02", "executions": 15},
            {"date": "2023-12-03", "executions": 8}
        ],
        "failure_reasons": {
            "validation_failed": 6,
            "network_timeout": 4,
            "permission_denied": 3,
            "other": 1
        },
        "efficiency_metrics": {
            "time_saved_hours": 67.5,
            "manual_tasks_automated": 234,
            "error_reduction_percent": 35
        }
    }

    return {
        "period": {
            "days": date_range,
            "start_date": (datetime.now() - timedelta(days=date_range)).date().isoformat(),
            "end_date": datetime.now().date().isoformat()
        },
        "analytics": analytics,
        "generated_at": datetime.now().isoformat()
    }


# Export router
__all__ = ["router"]