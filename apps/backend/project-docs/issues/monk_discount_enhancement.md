# Find more elegant way to trigger Monk discount on Discount model

**Issue to be created on GitHub when repository access is available**

## Current Implementation Issue

The current discount rules engine relies on pattern matching in the Notes field to trigger discounts (e.g., "Monk" text triggers a $50 discount). This approach is not elegant and doesn't leverage the actual data model.

## Problem

- Pattern matching on free-text notes is fragile and error-prone
- Doesn't use the `is_monk` field on StudentProfile 
- Not visible/transparent to users until after the fact
- Requires manual text entry to trigger automatic discounts

## Desired Solution

Create a smarter rules engine that can:
1. Automatically apply discounts based on student attributes (e.g., `is_monk=True`)
2. Make discount eligibility visible before payment
3. Support various discount conditions without hardcoding each case

## Potential Approaches

### 1. Attribute-Based Rules
```python
class DiscountRule(models.Model):
    # ... existing fields ...
    
    # New field for attribute-based conditions
    eligibility_conditions = models.JSONField(
        help_text="Python-evaluable conditions using student attributes",
        default=dict,
        blank=True
    )
    # Example: {"student.is_monk": True, "student.is_foreign": False}
```

### 2. Discount Eligibility Service
```python
class DiscountEligibilityService:
    def get_eligible_discounts(self, student, term, context=None):
        """Determine which discounts a student is eligible for."""
        eligible = []
        
        # Check attribute-based rules
        if student.is_monk:
            eligible.append(monk_discount_rule)
            
        # Check other conditions
        # ... 
        
        return eligible
```

### 3. Declarative Rules Engine
Use a lightweight rules engine or expression evaluator that can handle conditions like:
- `student.is_monk == True`
- `student.program.cycle == 'BA' AND student.is_foreign == False`
- `payment_date <= term.early_bird_date`

## Implementation Priority

Medium - Current pattern matching works but should be improved before next academic year

## Related Components
- `apps.finance.models.discounts.DiscountRule`
- `apps.finance.services.automatic_discount_service.AutomaticDiscountService`
- `apps.people.models.StudentProfile`

## Labels
- enhancement
- technical-debt  
- finance