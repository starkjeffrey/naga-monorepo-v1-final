# Discount Rules Documentation

## Overview

The DiscountRule system allows administrators to define discount rules that the AR Reconstruction process will automatically apply based on pattern matching in receipt notes.

## How Discount Rules Work

### 1. Pattern Matching

The `pattern_text` field is the key to how discounts are triggered:

- The reconciliation service looks for the `pattern_text` (case-insensitive) in the legacy receipt notes
- When a match is found, the discount rule is applied
- The reconciliation program can only APPLY existing rules, not create new ones

### 2. Rule Types and Their Patterns

#### MONK Pricing
- **Pattern Text**: `monk` or `Monk`
- **Example Notes that Match**: "Monk 50$", "monk discount", "Monk - special pricing"
- **Discount**: Usually a fixed amount ($50) rather than percentage

#### Early Bird Discounts
- **Pattern Text**: `early bird`, `10% early bird`, etc.
- **Example Notes**: "10% early bird discount", "Early bird until Oct 15"
- **Discount**: Percentage based (10%, 15%, 20%)

#### Cash Payment Plans
- **Pattern Text**: `cash payment`, `cash plan`
- **Example Notes**: "Cash payment plan", "50% cash payment"
- **Discount**: Variable

#### Weekend Classes
- **Pattern Text**: `weekend`
- **Example Notes**: "Weekend class discount"
- **Discount**: Usually percentage based

### 3. Discount Configuration

Each DiscountRule must specify EITHER:
- `discount_percentage`: For percentage-based discounts (e.g., 10% off)
- `fixed_amount`: For fixed dollar discounts (e.g., $50 off)

**Never both!**

### 4. Rule Restrictions

#### Applies to Terms
- Leave empty to apply to all terms
- Specify term codes to restrict (e.g., ["2023T1", "2023T2"])

#### Applies to Programs  
- Leave empty to apply to all programs
- Specify program codes to restrict (e.g., ["BA-TESOL", "BA-BUS"])

#### Applies to Cycle
- Leave empty to apply to all cycles
- Specify cycle to restrict (e.g., "BA" for all Bachelor's programs)

## Creating Discount Rules

### Example 1: Monk Discount
```python
DiscountRule.objects.create(
    rule_name="Monk Special Pricing",
    rule_type="MONK",
    pattern_text="monk",  # Will match "Monk", "monk", "MONK" in notes
    fixed_amount=Decimal("50.00"),  # $50 discount
    discount_percentage=None,  # Not a percentage discount
    applies_to_terms=[],  # All terms
    applies_to_programs=[],  # All programs
    applies_to_cycle="",  # All cycles
    is_active=True
)
```

### Example 2: Early Bird 10%
```python
DiscountRule.objects.create(
    rule_name="Modern 10% Early Bird",
    rule_type="EARLY_BIRD",
    pattern_text="10% early bird",  # Matches this text in notes
    discount_percentage=Decimal("10.00"),  # 10% discount
    fixed_amount=None,  # Not a fixed amount
    applies_to_terms=[],  # All terms from 2023+
    applies_to_programs=[],  # All programs
    applies_to_cycle="",  # All cycles
    is_active=True
)
```

## Important Notes

1. **The reconciliation program is READ-ONLY** for discount rules
   - It can only apply existing rules based on pattern matching
   - It cannot create new rules or modify existing ones

2. **Pattern matching is case-insensitive**
   - "monk" will match "Monk", "MONK", "monk"
   
3. **First match wins**
   - If multiple patterns match, the first matching rule is applied
   
4. **Manual override always possible**
   - Staff can manually adjust discounts in the reconciliation review process

5. **Audit trail maintained**
   - All automatic discount applications are logged with the rule that triggered them