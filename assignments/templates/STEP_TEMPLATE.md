# Step [X]: [Step Name]

**Phase**: [Parent Phase Name]
**Supervisors**: `@architect-supervisor`, `@[specific-worker]`
**Estimated Time**: [X hours/days]
**Status**: [Not Started / In Progress / Blocked / Complete]

## Objective
Clear, one-sentence description of what this step accomplishes.

## Context
Why is this step necessary? How does it fit into the broader phase?

## Prerequisites
- [ ] Previous step completed: [Step X-1]
- [ ] Dependencies available: [list]
- [ ] Test environment set up
- [ ] Database migrations applied (if applicable)

## Tasks

### Task 1: [Task Name]
**Description**: What needs to be done.

**Implementation Details**:
```python
# Pseudocode or example implementation
class Example:
    def method(self):
        pass
```

**Files to Modify**:
- `src/[module]/[file].py` - [what changes]

**Tests Required**:
- `tests/[test_file].py::test_[specific_test]`

---

### Task 2: [Task Name]
**Description**: What needs to be done.

**Implementation Details**:
[Describe approach, patterns to use, etc.]

**Files to Create**:
- `src/[new_file].py` - [purpose]

**Tests Required**:
- Unit tests for [specific functionality]

---

### Task 3: [Task Name]
[Continue pattern...]

---

## Success Criteria

### Automated Validation
- [ ] Unit tests pass: `pytest tests/[specific_tests].py -v`
- [ ] Code coverage >= 80%: `pytest --cov=src/[module]`
- [ ] No linting errors: `ruff check src/[module]`
- [ ] Type checking passes: `mypy src/[module]`

### Manual Validation
- [ ] Manual test 1: [describe test]
  - **Setup**: [initial conditions]
  - **Action**: [what to do]
  - **Expected**: [expected result]
  - **Actual**: [fill in after testing]

- [ ] Manual test 2: [describe test]
  - **Setup**: [initial conditions]
  - **Action**: [what to do]
  - **Expected**: [expected result]
  - **Actual**: [fill in after testing]

### Integration Validation
- [ ] Integrates with [related component]
- [ ] No breaking changes to existing functionality
- [ ] Events emitted correctly (if applicable)

## Implementation Notes

### Code Patterns to Follow
```python
# Example pattern for this step
# (Copy from relevant MDC file)
```

### Common Pitfalls to Avoid
- ❌ Pitfall 1: [description and why to avoid]
- ❌ Pitfall 2: [description and why to avoid]

### Dependencies to Inject
- `EventStore` - for event logging
- `AIManager` - for AI calls (if applicable)
- `Renderer` - for rendering (if applicable)

## Testing Strategy

### Unit Tests
```python
# Test template
def test_[functionality]():
    """Test that [specific behavior]."""
    # Arrange
    setup = ...
    
    # Act
    result = ...
    
    # Assert
    assert result == expected
```

### Mock Dependencies
```python
# Example mocks needed
from unittest.mock import Mock

mock_event_store = Mock(spec=EventStore)
mock_ai_manager = Mock(spec=AIManager)
```

## Files Modified/Created

### Created
- [ ] `src/[module]/[file].py` - [description]
- [ ] `tests/[test_file].py` - [description]

### Modified
- [ ] `src/[existing_file].py` - [what changed]
- [ ] `tests/[existing_test].py` - [what changed]

## Commit Strategy
Each task should be a separate commit:

1. `feat([module]): implement [task 1]`
   - Include: implementation + tests
   
2. `feat([module]): add [task 2]`
   - Include: implementation + tests

3. `docs([module]): update documentation for [step]`
   - Include: README updates, docstrings

## Blockers & Issues
Document any blockers encountered:

**Blocker 1**: [Description]
- **Impact**: [How it blocks progress]
- **Possible Solutions**: [Ideas for unblocking]
- **Status**: [Open / Resolved]

## Constitution Compliance

**Quick Check** - Verify this step follows `.cursor/rules/CONSTITUTION.md`:

- [ ] Events emitted for state changes (if applicable)
- [ ] Dependencies injected, not global
- [ ] Type hints on all new functions
- [ ] Specific exception handling
- [ ] Google-style docstrings added
- [ ] Tests written (>= 80% coverage)
- [ ] No rendering in game logic (if applicable)
- [ ] AI calls are async (if applicable)
- [ ] AI fallbacks exist (if applicable)

**Deviations**:
[If ANY principle violated, document in phase's `decisions.md`]

## Questions & Decisions

**Question 1**: [Technical question that arose]
- **Answer**: [Decision made]
- **Rationale**: [Why this decision]
- **Document In**: [Link to decisions.md if significant]

**Question 2**: [Technical question that arose]
- **Answer**: [Decision made]
- **Rationale**: [Why this decision]
- **Document In**: [Link to decisions.md if significant]

## References
- Constitution: `.cursor/rules/CONSTITUTION.md`
- MDC Rules: `@[specific-worker]`
- Phase Decisions: `../decisions.md`
- Phase Research: `../research.md`
- Related Code: `src/[related_file].py`
- Design Docs: [link or path]
- External Resources: [links]

## Completion Checklist
- [ ] All tasks completed
- [ ] All automated tests pass
- [ ] All manual tests pass
- [ ] Code reviewed (self-review at minimum)
- [ ] Documentation updated
- [ ] Commits pushed
- [ ] Ready for next step

**Completed By**: [Name/AI]
**Completion Date**: [Date]
**Time Spent**: [Actual time vs estimate]

