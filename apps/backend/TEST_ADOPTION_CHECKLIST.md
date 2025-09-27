# Test Architecture Adoption Checklist

## Quick Start Guide for Naga SIS Test Migration

This checklist guides the team through adopting the new pytest-based test architecture. Complete items in order for smooth transition.

---

## 🚀 Phase 1: Environment Setup (Day 1)

### 1. Install Test Dependencies
```bash
cd backend
uv pip install -e .[test]
```
**Owner:** All developers  
**Deadline:** Immediate  
✅ **Verify:** Run `uv run pytest --version` (should show 8.0+)

### 2. Archive Legacy Tests
```bash
make archive-old-tests
```
**Owner:** Tech Lead  
**Deadline:** Before any new test creation  
✅ **Verify:** `tests_legacy/` directory exists with old tests

### 3. Verify Test Infrastructure
```bash
make test-fast  # Should run without errors (even if no tests exist yet)
```
**Owner:** All developers  
**Deadline:** Day 1  
✅ **Verify:** Command completes without configuration errors

---

## 🏗️ Phase 2: Core Test Creation (Week 1)

### 4. Create Unit Tests for Critical Apps
**Priority Order:**
1. `finance/` - Invoice, Payment, Pricing models
2. `people/` - StudentProfile, TeacherProfile models  
3. `enrollment/` - Enrollment, CourseOffering models
4. `academic/` - GradeCalculation, Transcript services

**Owner:** App owners  
**Deadline:** End of Week 1  
✅ **Verify:** `make test-app` shows ≥10 tests per critical app

### 5. Create Integration Tests for Key Workflows
**Required Workflows:**
- Student enrollment process
- Payment processing
- Grade calculation
- Transcript generation

**Owner:** Backend team  
**Deadline:** End of Week 1  
✅ **Verify:** `make test-int` runs successfully

### 6. Implement API Contract Tests
```bash
make test-api
```
**Owner:** API team  
**Deadline:** End of Week 1  
✅ **Verify:** OpenAPI schema validates, contract tests pass

---

## 📊 Phase 3: Coverage & Quality Gates (Week 2)

### 7. Achieve Coverage Targets
**Targets:**
- Global: 85% minimum
- Critical modules (finance, academic): 95% minimum

```bash
make coverage-check  # Must pass
make coverage-critical  # Must pass for finance/academic
```
**Owner:** All developers  
**Deadline:** End of Week 2  
✅ **Verify:** Coverage reports meet thresholds

### 8. Enable Pre-commit Hooks
```bash
pre-commit install
```
**Owner:** All developers  
**Deadline:** Before first PR  
✅ **Verify:** Commits automatically run quality checks

### 9. Configure IDE Test Support
**VS Code:** Install Python Test Explorer  
**PyCharm:** Configure pytest as test runner  
**Owner:** Each developer  
**Deadline:** Week 1  
✅ **Verify:** Can run individual tests from IDE

---

## 🚀 Phase 4: CI/CD Integration (Week 2)

### 10. Enable GitHub Actions
1. Merge `.github/workflows/test-suite.yml` to main branch
2. Configure repository secrets if needed
3. Verify first workflow run succeeds

**Owner:** DevOps Lead  
**Deadline:** Week 2, Day 1  
✅ **Verify:** Green checkmark on GitHub commits

### 11. Enforce Branch Protection
**Settings → Branches → main:**
- ✅ Require status checks (test-suite-status)
- ✅ Require branches to be up to date
- ✅ Include administrators

**Owner:** Repository Admin  
**Deadline:** After first successful CI run  
✅ **Verify:** Cannot merge without passing tests

### 12. Setup Coverage Reporting
1. Add repository to Codecov
2. Configure Codecov token in GitHub secrets
3. Add coverage badge to README

**Owner:** DevOps Lead  
**Deadline:** Week 2  
✅ **Verify:** Coverage badge displays in README

---

## 📚 Phase 5: Team Enablement (Week 3)

### 13. Conduct Test Writing Workshop
**Topics:**
- pytest basics and fixtures
- Using conftest.py fixtures
- Writing effective unit tests
- Mocking and patching strategies

**Owner:** Test Architect/Lead  
**Deadline:** Week 3  
✅ **Verify:** All team members attend

### 14. Document Team-Specific Patterns
Create `tests/README.md` with:
- Common test patterns for your domain
- Frequently used fixtures
- Debugging test failures
- Performance testing guidelines

**Owner:** Tech Lead  
**Deadline:** Week 3  
✅ **Verify:** Document reviewed and approved

### 15. Establish Test Review Process
**Requirements:**
- All PRs must include tests
- Test changes require code review
- Coverage must not decrease
- New features require unit + integration tests

**Owner:** Team Lead  
**Deadline:** Ongoing  
✅ **Verify:** Documented in team wiki/confluence

---

## 📈 Success Metrics

Track these KPIs after 30 days:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code Coverage | ≥85% overall, ≥95% critical | `make coverage` |
| Test Execution Time | <5 min for unit tests | CI pipeline metrics |
| Test Reliability | <1% flaky tests | Weekly failure analysis |
| Defect Escape Rate | ↓50% vs previous quarter | Bug tracking system |
| Developer Confidence | ↑30% satisfaction | Team survey |

---

## 🆘 Quick Help

### Common Commands
```bash
make test           # Run all tests
make test-fast      # Quick unit tests only
make test-app       # Test specific app (interactive)
make coverage-html  # Generate and open coverage report
make test-failed    # Re-run only failed tests
make test-watch     # Continuous test mode
```

### Troubleshooting
- **Import errors:** Check `PYTHONPATH` and `conftest.py` location
- **Database errors:** Use `--reuse-db` flag or check migrations
- **Slow tests:** Mark with `@pytest.mark.slow` and exclude in fast runs
- **Flaky tests:** Use `@pytest.mark.flaky` with retry logic

### Resources
- [TEST_PLAN.md](./TEST_PLAN.md) - Complete test strategy
- [pytest.ini](./pytest.ini) - Configuration reference
- [Makefile](./Makefile) - All available test commands
- [tests/conftest.py](./tests/conftest.py) - Available fixtures

---

## ✅ Definition of Done

The test architecture migration is complete when:

1. ✅ All legacy tests archived or migrated
2. ✅ Coverage targets achieved (85% global, 95% critical)
3. ✅ CI/CD pipeline running on all PRs
4. ✅ Team trained on new test framework
5. ✅ Test execution time <5 minutes for unit tests
6. ✅ Zero failing tests in main branch
7. ✅ All developers using test-first approach
8. ✅ Automated test reports in Slack/Teams
9. ✅ Performance benchmarks established
10. ✅ Security tests integrated

---

**Questions?** Contact the Test Architecture team or refer to TEST_PLAN.md for detailed guidance.

**Remember:** Better tests = Better sleep 😴