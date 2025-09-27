"""
Data Pipeline Django App

A robust 6-stage data pipeline system for migrating legacy SIS data
from MSSQL/CSV format into clean, validated, and transformed PostgreSQL data
with complete audit trails.

Stages:
1. Raw Import - Import all data as TEXT preserving original values
2. Data Profiling - Analyze patterns and data quality issues
3. Data Cleaning - Standardize formats, parse complex fields, fix encoding
4. Validation - Apply business rules via Pydantic models
5. Transform - Apply domain-specific transformations (Limon→Unicode, etc.)
6. Split - Generate multiple output records from single input (headers/lines)
"""

default_app_config = "apps.data_pipeline.apps.DataPipelineConfig"
