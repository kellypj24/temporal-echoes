# Validation Checklist: [Component/Phase Name]

**Date**: [Date]
**Validator**: [Name/AI]
**Phase**: [Phase Name]
**Status**: [Pass / Fail / Needs Revision]

## Overview
Brief description of what is being validated and why.

---

## 1. Automated Tests

### Unit Tests
- [ ] All unit tests pass: `make test`
- [ ] Coverage >= 80%: `pytest --cov=src --cov-report=term-missing`
- [ ] No skipped tests without justification
- [ ] Tests cover edge cases
- [ ] Tests cover error conditions

**Results**:
```
Test Suite: [name]
Total Tests: [X]
Passed: [X]
Failed: [X]
Coverage: [X]%
```

**Failed Tests** (if any):
- `test_[name]`: [reason for failure]

---

### Integration Tests
- [ ] Integration tests pass
- [ ] Cross-component interactions work
- [ ] Database operations work correctly
- [ ] AI integration works (or fallback triggers)

**Results**:
```
[Output from integration test run]
```

---

### Linting & Type Checking
- [ ] No linting errors: `make lint`
- [ ] Type checking passes: `mypy src/`
- [ ] No security issues: `bandit -r src/` (if applicable)

**Linting Results**:
```
[Output from ruff/flake8]
```

**Type Checking Results**:
```
[Output from mypy]
```

---

## 2. Code Quality

### Code Structure
- [ ] Clean separation of concerns
- [ ] No circular dependencies
- [ ] Dependencies injected, not instantiated
- [ ] No god objects (classes with too many responsibilities)
- [ ] Functions < 50 lines (guideline, not strict rule)
- [ ] Classes < 300 lines (guideline, not strict rule)

**Notes**:
[Any concerns about code structure]

---

### Type Safety
- [ ] Type hints on all function signatures
- [ ] Type hints on class attributes
- [ ] No use of `Any` without justification
- [ ] Proper use of Optional for nullable values

**Missing Type Hints** (if any):
- `[file]:[line]` - [function/method name]

---

### Documentation
- [ ] Docstrings on all public functions
- [ ] Docstrings on all classes
- [ ] Complex algorithms explained
- [ ] Non-obvious behavior documented
- [ ] Examples provided where helpful

**Missing Docs** (if any):
- `[file]:[line]` - [what needs documentation]

---

### Error Handling
- [ ] Specific exception types used
- [ ] No bare `except:` clauses
- [ ] Errors logged appropriately
- [ ] User-facing errors are helpful
- [ ] Retry logic where appropriate (AI calls, network)

**Error Handling Issues** (if any):
[List issues]

---

## 3. Functional Requirements

### Core Functionality
List each requirement and verify:

- [ ] **Requirement 1**: [Description]
  - **Status**: [Pass/Fail]
  - **Evidence**: [Test output, manual validation, etc.]

- [ ] **Requirement 2**: [Description]
  - **Status**: [Pass/Fail]
  - **Evidence**: [Test output, manual validation, etc.]

- [ ] **Requirement 3**: [Description]
  - **Status**: [Pass/Fail]
  - **Evidence**: [Test output, manual validation, etc.]

---

### Edge Cases
- [ ] Empty input handled
- [ ] Null/None values handled
- [ ] Maximum values handled
- [ ] Invalid input rejected gracefully
- [ ] Concurrent access handled (if applicable)

**Edge Case Results**:
[Document results of edge case testing]

---

## 4. Architecture Compliance

### Design Patterns
- [ ] Correct patterns used per MDC guidelines
- [ ] State machine pattern used correctly (if applicable)
- [ ] Events emitted for state changes (if applicable)
- [ ] Dependency injection used (no globals)
- [ ] Command pattern for undo/sourcing (if applicable)

---

### Layer Separation
- [ ] No game logic in rendering code
- [ ] No rendering in game logic code
- [ ] No database queries in UI code
- [ ] No AI calls blocking game loop
- [ ] Clean boundaries between modules

**Separation Issues** (if any):
[List violations]

---

### Event Sourcing (if applicable)
- [ ] All state changes emit events
- [ ] Events are immutable
- [ ] Events include all necessary data
- [ ] Timeline ID included in events
- [ ] Events can be replayed to rebuild state

---

## 5. Performance

### Benchmarks
- [ ] 60 FPS maintained in game loop (if applicable)
- [ ] AI calls < 5 seconds (if applicable)
- [ ] Database writes < 10ms (p95)
- [ ] UI responsive, no frame drops
- [ ] Memory usage reasonable (no leaks)

**Performance Results**:
```
FPS: [X]
AI Response Time: [X]s
DB Write Time: [X]ms
Memory Usage: [X]MB
```

---

### Optimization
- [ ] No premature optimization
- [ ] Optimization only where profiling shows bottleneck
- [ ] Sprite caching used (if applicable)
- [ ] Database indexes in place
- [ ] Viewport culling used (if applicable)

---

## 6. Manual Testing

### Test Scenario 1: [Name]
**Description**: [What is being tested]

**Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result**: [What should happen]

**Actual Result**: [What actually happened]

**Status**: [Pass / Fail]

---

### Test Scenario 2: [Name]
**Description**: [What is being tested]

**Steps**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Result**: [What should happen]

**Actual Result**: [What actually happened]

**Status**: [Pass / Fail]

---

### Test Scenario 3: [Name]
[Continue pattern...]

---

## 7. Integration Points

### Database Integration
- [ ] Schema migrations applied
- [ ] Queries optimized
- [ ] Transactions used correctly
- [ ] Event store working correctly
- [ ] dbt models updated (if applicable)

---

### AI Integration (if applicable)
- [ ] Ollama connection works
- [ ] Prompts render correctly
- [ ] Responses parse successfully
- [ ] Fallbacks trigger on failure
- [ ] Response caching works

---

### Rendering Integration (if applicable)
- [ ] Sprites render correctly
- [ ] UI components display properly
- [ ] Camera/viewport works
- [ ] Layer ordering correct
- [ ] Animations smooth

---

## 8. Documentation

### Code Documentation
- [ ] README.md updated
- [ ] API documentation generated
- [ ] Examples provided
- [ ] Migration guide (if breaking changes)
- [ ] Changelog updated

---

### Assignment Documentation
- [ ] PLAN.md updated with actual results
- [ ] Decisions documented
- [ ] Blockers resolved and documented
- [ ] Lessons learned captured

---

## 9. Deployment Readiness

### Dependencies
- [ ] All dependencies in `pyproject.toml`
- [ ] Lock file updated: `poetry.lock`
- [ ] Docker images build: `docker-compose build`
- [ ] Environment variables documented

---

### Configuration
- [ ] Config files present
- [ ] Defaults sensible
- [ ] Environment-specific configs
- [ ] Secrets not hardcoded

---

## 10. Issues & Concerns

### Critical Issues (Must Fix)
- [ ] Issue 1: [Description]
  - **Severity**: Critical
  - **Impact**: [What breaks]
  - **Fix**: [What needs to be done]

---

### Non-Critical Issues (Should Fix)
- [ ] Issue 1: [Description]
  - **Severity**: Minor
  - **Impact**: [What's affected]
  - **Fix**: [What should be done]

---

### Technical Debt
- [ ] Debt 1: [Description]
  - **Reason**: [Why incurred]
  - **Plan**: [How/when to address]

---

## 11. Final Assessment

### Overall Status: [PASS / FAIL / NEEDS REVISION]

### Summary
[Brief summary of validation results]

### Strengths
- [What was done well]
- [What was done well]

### Areas for Improvement
- [What needs work]
- [What needs work]

### Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

### Next Steps
- [ ] [Action item 1]
- [ ] [Action item 2]
- [ ] [Action item 3]

---

## Sign-off

**Validated By**: [Name/AI]
**Validation Date**: [Date]
**Approved**: [Yes / No]
**Move to Completed**: [Yes / No]

**Reviewer Comments**:
[Any additional comments from reviewer]

