# Phase [X]: [Phase Name]

**Status**: 🔄 In Progress / ✅ Complete / 🔲 Not Started  
**Started**: [Date]  
**Completed**: [Date]  
**Branch**: `feature/phase-[X]-[short-name]`

## Phase Workflow

This phase follows the Spec-Driven Development (SDD) approach:

1. **🔍 Research Phase** (documented in `research.md`)
   - Investigate unknowns, validate assumptions, check dependencies
   - Required before moving to planning

2. **📋 Decision Phase** (documented in `decisions.md`)
   - Make architectural and design decisions based on research
   - Document alternatives and trade-offs

3. **🛠️ Implementation Phase** (this document)
   - Execute steps based on research and decisions
   - Follow constitution principles

4. **✅ Validation Phase**
   - Test, review, and validate all success criteria
   - Ensure constitution compliance

## Objectives
- Primary objective 1
- Primary objective 2
- Primary objective 3

## Prerequisites

### Hard Prerequisites
- [ ] Completed Phase [Y]
- [ ] Dependencies installed: [list dependencies]
- [ ] Environment configured: [list env vars or config]
- [ ] Database schema in place (if applicable)

### Research Prerequisites
- [ ] `research.md` completed and reviewed
- [ ] All high-priority research topics addressed
- [ ] Critical assumptions validated
- [ ] Tech stack versions confirmed

### Decision Prerequisites
- [ ] `decisions.md` created with all major decisions
- [ ] Constitution compliance verified
- [ ] Technical debt documented (if any)
- [ ] Implementation guidance clear

## Context
Brief description of why this phase is important and how it fits into the overall project architecture.

**Related Documents**:
- `research.md` - Research findings for this phase
- `decisions.md` - Decision log for this phase
- `.cursor/rules/CONSTITUTION.md` - Development principles

## Steps

### Step 1: [Step Name]
**Supervisors**: `@architect-supervisor`, `@[specific-worker]`

**Description**: 
What this step accomplishes and why it's necessary.

**Tasks**:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Success Criteria**:
- [ ] Unit tests pass: `pytest tests/[specific_test].py`
- [ ] Integration tests pass (if applicable)
- [ ] Code coverage >= 80% for new code
- [ ] No linting errors: `make lint`
- [ ] Manual validation: [describe manual test]
- [ ] Documentation updated

**Files to Create/Modify**:
- `src/[module]/[file].py` - [description]
- `tests/[test_file].py` - [description]

**Estimated Time**: [X hours/days]

---

### Step 2: [Step Name]
**Supervisors**: `@architect-supervisor`, `@[specific-worker]`

**Description**: 
What this step accomplishes and why it's necessary.

**Tasks**:
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3

**Success Criteria**:
- [ ] [Criteria 1]
- [ ] [Criteria 2]
- [ ] [Criteria 3]

**Files to Create/Modify**:
- `src/[module]/[file].py` - [description]
- `tests/[test_file].py` - [description]

**Estimated Time**: [X hours/days]

---

### Step 3: [Step Name]
[Continue pattern for remaining steps...]

---

## Integration Testing
After all steps are complete:

**Test Scenarios**:
1. **Scenario 1**: [Description]
   - Setup: [initial state]
   - Action: [what to do]
   - Expected: [expected result]

2. **Scenario 2**: [Description]
   - Setup: [initial state]
   - Action: [what to do]
   - Expected: [expected result]

## Validation Checklist

### Code Quality
- [ ] All unit tests pass: `make test`
- [ ] Code coverage >= 80%
- [ ] No linting errors: `make lint`
- [ ] Type hints on all functions
- [ ] Docstrings on public methods

### Functional Requirements
- [ ] Objective 1 met
- [ ] Objective 2 met
- [ ] Objective 3 met

### Architecture Compliance
- [ ] Clean separation of concerns maintained
- [ ] Dependencies injected, not instantiated
- [ ] Events emitted for state changes (if applicable)
- [ ] No circular dependencies
- [ ] No game logic in rendering code (if applicable)

### Documentation
- [ ] README updated with new features
- [ ] API documentation generated/updated
- [ ] Example usage provided
- [ ] Migration guide (if breaking changes)

### Performance
- [ ] No performance regressions
- [ ] 60 FPS maintained in game loop (if applicable)
- [ ] AI calls don't block (if applicable)

## Constitution Compliance

Review against `.cursor/rules/CONSTITUTION.md` principles:

### Immutable Principles Check
- [ ] ✅ Events are append-only (no updates/deletes)
- [ ] ✅ Dependencies injected via constructors
- [ ] ✅ Type hints on all functions
- [ ] ✅ Clean separation of concerns (no rendering in logic)
- [ ] ✅ >= 80% test coverage
- [ ] ✅ Specific error handling (no bare except)
- [ ] ✅ Google-style docstrings on public APIs
- [ ] ✅ All AI calls are async/non-blocking
- [ ] ✅ AI fallbacks implemented
- [ ] ✅ Token limits validated (4096 tokens)
- [ ] ✅ Transactions used for multi-step DB operations
- [ ] ✅ SQLite for OLTP, DuckDB for OLAP
- [ ] ✅ 60 FPS target maintained
- [ ] ✅ < 5 second AI response time

### Deviations
If ANY principles were violated, they MUST be documented in `decisions.md`:

- **[Principle Name]**: [Link to decision record justifying deviation]
- [List all deviations]

## Rollback Plan
If this phase needs to be reverted:
1. [Step to revert]
2. [Step to revert]
3. [Files to restore]
4. Revert commits: `git revert <commit-hash>`
5. Update decision log with rollback reason

## Retrospective

### What Went Well
[Document successes for future reference]

### What Could Be Improved
[Document challenges and how to avoid them]

### Metrics
- **Estimated Time**: [X hours]
- **Actual Time**: [Y hours]
- **Test Coverage**: [Z%]
- **Lines of Code**: [N]
- **Decisions Made**: [Count]
- **Constitution Deviations**: [Count]

## Follow-up Phases
What should be done after this phase:
- Phase [X+1]: [Name and brief description]
- Phase [X+2]: [Name and brief description]

## Sign-off
- [ ] All steps completed
- [ ] All tests passing
- [ ] All validation criteria met
- [ ] Documentation complete
- [ ] Ready to move to `assignments/completed/`

**Completed By**: [Name/AI]
**Completion Date**: [Date]
**Review Status**: [Approved/Needs Revision]

