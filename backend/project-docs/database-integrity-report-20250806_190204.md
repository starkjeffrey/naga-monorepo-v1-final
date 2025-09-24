# Database Integrity Report
Generated: Wed Aug  6 19:02:04 +07 2025

## Summary
This report validates database schema against Django models.

## Migration Status

### ✓ All migrations applied

## Model Changes

### ❌ Model Changes Without Migrations
```
 Container naga_local_redis  Running
 Container naga_local_postgres  Running
 Container naga_local_mailpit  Running
wait-for-it: waiting 30 seconds for postgres:5432
wait-for-it: postgres:5432 is available after 0 seconds
PostgreSQL is available
```

## Schema Validation

### Detailed Schema Validation

```
 Container naga_local_redis  Running
 Container naga_local_mailpit  Running
 Container naga_local_postgres  Running
wait-for-it: waiting 30 seconds for postgres:5432
wait-for-it: postgres:5432 is available after 0 seconds
PostgreSQL is available
Traceback (most recent call last):
  File "/app/scratchpad/validate_db_schema.py", line 10, in <module>
    django.setup()
    ~~~~~~~~~~~~^^
  File "/usr/local/lib/python3.13/site-packages/django/__init__.py", line 19, in setup
    configure_logging(settings.LOGGING_CONFIG, settings.LOGGING)
                      ^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.13/site-packages/django/conf/__init__.py", line 81, in __getattr__
    self._setup(name)
    ~~~~~~~~~~~^^^^^^
  File "/usr/local/lib/python3.13/site-packages/django/conf/__init__.py", line 68, in _setup
    self._wrapped = Settings(settings_module)
                    ~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.13/site-packages/django/conf/__init__.py", line 166, in __init__
    mod = importlib.import_module(self.SETTINGS_MODULE)
  File "/usr/local/lib/python3.13/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1324, in _find_and_load_unlocked
ModuleNotFoundError: No module named 'config'


```

## Constraint Validation

          table_name           |    column_name     | foreign_table_name | foreign_column_name
-------------------------------+--------------------+--------------------+---------------------
 academic_canonicalrequirement | major_id           | curriculum_major   | id
 academic_canonicalrequirement | required_course_id | curriculum_course  | id
 academic_canonicalrequirement | effective_term_id  | curriculum_term    | id
 academic_canonicalrequirement | end_term_id        | curriculum_term    | id
 academic_courseequivalency    | effective_term_id  | curriculum_term    | id
(5 rows)
