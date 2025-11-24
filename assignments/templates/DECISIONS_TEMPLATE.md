# Decision Log: [Phase Name]

**Phase**: [Phase Number]  
**Created**: [Date]  
**Status**: 🔄 Active / 📦 Archived  

## Overview
This document logs all significant architectural, design, and implementation decisions made during this phase. Each decision is captured using a lightweight ADR (Architecture Decision Record) format.

**Total Decisions**: [X]  
**Constitution Deviations**: [X]  
**High Impact**: [X]  

---

## Decision Template

For each decision, use this structure:

---

## [DEC-XXXX]: [Decision Title]

**Status**: 🟢 Proposed / 🟡 Accepted / 🔴 Deprecated / ⚫ Superseded  
**Date**: [YYYY-MM-DD]  
**Deciders**: [Names/AI Agents]  
**Impact**: 🔴 Critical / 🟡 High / 🟢 Medium / ⚪ Low  
**Constitution Deviation**: ✅ Yes / ❌ No  

### Context
[Describe the problem or situation requiring a decision. What forces are at play? What constraints exist?]

### Decision
[State the decision clearly and concisely. What was chosen?]

### Alternatives Considered

#### Alternative 1: [Name]
**Description**: [What this alternative would involve]

**Pros**:
- Pro 1
- Pro 2

**Cons**:
- Con 1
- Con 2

**Reason Rejected**: [Why this wasn't chosen]

#### Alternative 2: [Name]
[Same structure...]

#### Alternative 3: [Name]
[Continue for all alternatives considered...]

### Consequences

#### Positive
- Positive consequence 1
- Positive consequence 2

#### Negative  
- Negative consequence 1
- Negative consequence 2

#### Neutral
- Neutral consequence 1
- Neutral consequence 2

### Trade-offs Accepted
[What are you giving up to make this decision?]

### Implementation Notes
[Specific guidance for developers implementing this decision]

```python
# Example code if applicable
def example():
    pass
```

### Success Criteria
How will you know this decision was correct?

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation Strategy | Owner |
|------|-----------|--------|---------------------|-------|
| Risk 1 | 🔴 High / 🟡 Med / 🟢 Low | 🔴 Critical / 🟡 High / 🟢 Med | Strategy | [Name] |

### Related Decisions
- Links to related decision records
- Dependencies on other decisions

### Constitution Compliance
[If this is a deviation, document it here]

**Principle Violated**: [Which principle from CONSTITUTION.md]

**Justification**: [Why deviation is necessary]

**Technical Debt Created**: [Link to GitHub issue]

**Remediation Plan**: [How will this be addressed later]

**Target Date**: [When will this be fixed]

### References
- [Link 1](url)
- [Link 2](url)

### Changelog
- **[Date]**: Decision proposed
- **[Date]**: Decision accepted
- **[Date]**: [Any updates or changes]

---

## Actual Decisions

---

## [DEC-0001]: [First Decision Title]

**Status**: 🟡 Accepted  
**Date**: [YYYY-MM-DD]  
**Deciders**: [Names/AI Agents]  
**Impact**: 🟡 High  
**Constitution Deviation**: ❌ No  

### Context
[Fill in...]

### Decision
[Fill in...]

[Continue with full template structure...]

---

## [DEC-0002]: [Second Decision Title]

[Same structure...]

---

## Decision Index

Quick reference table for all decisions:

| ID | Title | Status | Impact | Date | Deviation | Notes |
|----|-------|--------|--------|------|-----------|-------|
| DEC-0001 | [Title] | 🟡 | 🟡 | [Date] | ❌ | [Summary] |
| DEC-0002 | [Title] | 🟢 | 🟢 | [Date] | ❌ | [Summary] |

---

## Constitution Deviations Summary

If any decisions deviate from constitution principles, summarize them here:

| Decision ID | Principle Violated | Justification | Tech Debt Issue | Status |
|-------------|-------------------|---------------|-----------------|--------|
| DEC-XXXX | [Principle] | [Brief reason] | [Link] | ✅ / 🔄 / 🔲 |

**Total Deviations**: [X]  
**Resolved**: [X]  
**Outstanding**: [X]  

---

## Impact Analysis

### High Impact Decisions
List all decisions marked as 🔴 Critical or 🟡 High:

1. **[DEC-XXXX]**: [Title] - [One sentence summary]
2. **[DEC-YYYY]**: [Title] - [One sentence summary]

### Decisions Affecting Multiple Systems
List decisions that cross system boundaries:

1. **[DEC-XXXX]**: Affects [System 1], [System 2], [System 3]

---

## Lessons Learned

### What Worked Well
Capture insights about the decision-making process:

1. Decision process 1
2. Decision process 2

### What Could Be Improved
Areas for improvement in future decision-making:

1. Improvement 1
2. Improvement 2

### Recommendations for Future Phases
Guidance for upcoming decisions:

1. Recommendation 1
2. Recommendation 2

---

## Decision Review Schedule

Plan to review decisions and validate they're still correct:

| Decision ID | Review Date | Reviewer | Status | Outcome |
|-------------|------------|----------|--------|---------|
| DEC-0001 | [Date] | [Name] | ✅ / 🔄 / 🔲 | [Notes] |

---

## Superseded Decisions

Track decisions that have been replaced:

| Original ID | Superseded By | Date | Reason |
|-------------|---------------|------|--------|
| DEC-XXXX | DEC-YYYY | [Date] | [Brief explanation] |

---

## Decision Approval

**Phase Lead**: [Name]  
**Reviewed By**: [Names]  
**Approval Date**: [Date]  

**Sign-off Checklist**:
- [ ] All decisions documented
- [ ] Constitution deviations justified
- [ ] Technical debt tracked
- [ ] Implementation guidance clear
- [ ] Success criteria defined
- [ ] Risks identified and mitigated

---

## Notes for AI Agents

When documenting decisions:

1. **Be Specific**: Don't just say "we chose X" - explain why X over Y and Z
2. **Show Your Work**: Document alternatives, not just the winner
3. **Think Long-term**: Consider how this affects future phases
4. **Flag Deviations**: Call out constitution violations immediately
5. **Link Everything**: Connect to research, plans, code, issues
6. **Update Status**: Keep decision status current as implementation progresses

**Good Decision Record**:
- Clear context and problem statement
- Multiple alternatives evaluated
- Explicit trade-offs documented
- Implementation guidance provided
- Success criteria measurable

**Bad Decision Record**:
- "We chose X because it's better"
- No alternatives documented
- No trade-offs acknowledged
- Vague or missing implementation notes
- No way to validate decision was correct

---

## Related Documents
- `.cursor/rules/CONSTITUTION.md` - Development principles
- `research.md` - Research findings informing decisions
- `PLAN.md` - How decisions affect implementation plan
- `assignments/completed/phase-X/retrospective.md` - Decision outcomes

