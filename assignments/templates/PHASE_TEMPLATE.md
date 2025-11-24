# Phase [X]: [Phase Name]

## Objectives
- Primary objective 1
- Primary objective 2
- Primary objective 3

## Prerequisites
- [ ] Completed Phase [Y]
- [ ] Dependencies installed: [list dependencies]
- [ ] Environment configured: [list env vars or config]
- [ ] Database schema in place (if applicable)

## Context
Brief description of why this phase is important and how it fits into the overall project architecture.

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

## Rollback Plan
If this phase needs to be reverted:
1. [Step to revert]
2. [Step to revert]
3. [Files to restore]

## Notes & Decisions
Document key decisions made during this phase:

**Decision 1**: [What was decided]
- **Rationale**: [Why]
- **Alternatives Considered**: [What else was considered]
- **Trade-offs**: [What was gained/lost]

**Decision 2**: [What was decided]
- **Rationale**: [Why]
- **Alternatives Considered**: [What else was considered]
- **Trade-offs**: [What was gained/lost]

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

