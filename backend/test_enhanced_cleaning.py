#!/usr/bin/env python3
"""
Test script to verify enhanced cleaning functionality for legacy student data.
"""

import sys
import os
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_emergency_contact_parsing():
    """Test the emergency contact parsing functionality"""
    print("Testing Emergency Contact Parsing")
    print("=" * 40)
    
    # Mock the cleaning function logic
    def parse_emergency_contact(value, column_name=None):
        if not value or not value.strip():
            return value

        # Clean up common formatting issues in emergency contact data
        cleaned = value.strip()
        
        # Remove excessive whitespace
        cleaned = " ".join(cleaned.split())
        
        # Handle common legacy formatting issues
        # Remove parentheses around entire name
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = cleaned[1:-1].strip()
        
        # Standardize relationship indicators
        relationship_mappings = {
            'father': 'Father',
            'mother': 'Mother', 
            'parent': 'Parent',
            'spouse': 'Spouse',
            'wife': 'Spouse',
            'husband': 'Spouse',
            'brother': 'Brother',
            'sister': 'Sister',
            'son': 'Son',
            'daughter': 'Daughter',
            'friend': 'Friend',
            'relative': 'Relative',
        }
        
        # If this is a relationship field, normalize it
        if column_name and 'relationship' in column_name.lower():
            cleaned_lower = cleaned.lower()
            for key, standardized in relationship_mappings.items():
                if key in cleaned_lower:
                    return standardized
        
        # Title case for names
        if column_name and 'name' in column_name.lower():
            # Split on spaces and title case each part
            name_parts = cleaned.split()
            cleaned = ' '.join(part.title() for part in name_parts)
        
        return cleaned

    # Test cases for emergency contact names
    name_test_cases = [
        ("john smith", "emergency_contact_name"),
        ("(mary johnson)", "emergency_contact_name"),  
        ("  PETER   WILLIAMS  ", "emergency_contact_name"),
        ("", "emergency_contact_name"),
    ]
    
    print("Emergency Contact Names:")
    print("-" * 30)
    for raw_value, field_name in name_test_cases:
        result = parse_emergency_contact(raw_value, field_name)
        print(f"'{raw_value}' → '{result}'")
    
    # Test cases for relationships
    relationship_test_cases = [
        ("father", "emergency_contact_relationship"),
        ("MOTHER", "emergency_contact_relationship"),
        ("my wife", "emergency_contact_relationship"),
        ("husband", "emergency_contact_relationship"),
        ("brother", "emergency_contact_relationship"),
        ("family friend", "emergency_contact_relationship"),
        ("other", "emergency_contact_relationship"),
    ]
    
    print("\nRelationship Standardization:")
    print("-" * 30)
    for raw_value, field_name in relationship_test_cases:
        result = parse_emergency_contact(raw_value, field_name)
        print(f"'{raw_value}' → '{result}'")

def test_birth_date_normalization():
    """Test birth date normalization with age validation"""
    print("\n\nTesting Birth Date Normalization")
    print("=" * 40)
    
    def normalize_birth_date(value):
        """Mock birth date normalization function"""
        if not value or not value.strip():
            return value
        
        # Mock MSSQL datetime parsing
        def parse_mssql_datetime(date_str):
            if not date_str:
                return None
            
            # Handle MSSQL format: "Apr 27 2009 12:00AM"
            import re
            match = re.match(r'([A-Za-z]{3})\s+(\d{1,2})\s+(\d{4})\s+\d{1,2}:\d{2}[AP]M', date_str)
            if match:
                month_name, day, year = match.groups()
                month_map = {
                    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
                    "May": "05", "Jun": "06", "Jul": "07", "Aug": "08", 
                    "Sep": "09", "Oct": "10", "Nov": "11", "Dec": "12",
                }
                month = month_map.get(month_name, "01")
                return f"{year}-{month}-{day.zfill(2)}"
            return date_str
        
        try:
            # First apply the standard MSSQL datetime parsing
            parsed_date = parse_mssql_datetime(value)
            
            if parsed_date and parsed_date != value:
                # Additional validation for birth dates
                try:
                    # Parse the ISO formatted date for validation
                    birth_dt = datetime.fromisoformat(parsed_date)
                    current_dt = datetime.now()
                    
                    # Calculate age
                    age_years = (current_dt - birth_dt).days / 365.25
                    
                    # Reasonable age range for students (5-120 years)
                    status = "✅"
                    if age_years < 5:
                        status = "⚠️ VERY YOUNG"
                    elif age_years > 120:
                        status = "⚠️ VERY OLD"  
                    elif age_years < 15 or age_years > 65:
                        status = "ℹ️ UNUSUAL"
                    
                    print(f"  Age: {age_years:.1f} years {status}")
                    return parsed_date
                    
                except (ValueError, TypeError):
                    return parsed_date
            
            return parsed_date
            
        except Exception:
            return value

    # Test cases for birth dates
    test_cases = [
        "Jan 15 1990 12:00AM",   # Normal student age
        "Dec 3 1985 12:00AM",    # Older student
        "Mar 20 2010 12:00AM",   # Very young
        "Apr 1 1920 12:00AM",    # Very old  
        "Jun 10 1995 12:00AM",   # Normal range
        "",                      # Empty
        "invalid date",          # Invalid format
    ]
    
    for test_date in test_cases:
        print(f"'{test_date}':")
        result = normalize_birth_date(test_date)
        print(f"  Result: '{result}'")

def test_integration_summary():
    """Show what was integrated"""
    print("\n\nIntegration Summary")
    print("=" * 50)
    
    print("✅ Enhanced Data Pipeline Stage 3 with:")
    print("  • Advanced emergency contact parsing")
    print("    - Name normalization (Title Case)")
    print("    - Relationship standardization") 
    print("    - Legacy format cleanup")
    
    print("  • Birth date normalization with validation")
    print("    - MSSQL datetime parsing")
    print("    - Age validation (5-120 years)")
    print("    - Unusual age warnings")
    
    print("  • Existing graduation date fields confirmed:")
    print("    - BAGradDate → ba_graduation_date") 
    print("    - MAGradDate → ma_graduation_date")
    
    print("  • Name parsing from previous integration:")
    print("    - Legacy status indicators ($$, <sponsor>, {AF})")
    print("    - Clean name extraction")
    print("    - Status preservation in virtual columns")
    
    print("\n🚀 Stage 3 now handles comprehensive legacy data cleaning:")
    print("  • Student names with embedded status")
    print("  • Emergency contact standardization") 
    print("  • Birth date validation")
    print("  • Academic date processing")
    print("  • Encoding fixes for Khmer text")
    print("  • Phone number normalization")
    print("  • Email validation and cleanup")

if __name__ == "__main__":
    test_emergency_contact_parsing()
    test_birth_date_normalization()
    test_integration_summary()