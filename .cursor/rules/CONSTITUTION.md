---
alwaysApply: true
---

# Temporal Echoes Development Constitution

**Version**: 1.0.0  
**Last Updated**: 2024-11-24  
**Status**: Active

This document defines the immutable principles that ALL AI agents, developers, and contributors MUST follow when working on Temporal Echoes. These are non-negotiable unless explicitly documented and approved.

## Immutable Principles

### Architecture Principles

#### 1. Event Sourcing is Sacred
- **Rule**: All state changes MUST emit immutable events to the event store
- **Why**: Timeline branching and replay functionality depend on complete event history
- **Never**: Update or delete events from `game_events` table
- **Always**: INSERT only, events are append-only

#### 2. Dependency Injection Only
- **Rule**: Pass dependencies via constructor parameters, never use global state
- **Why**: Testability, clarity, and avoiding hidden dependencies
- **Never**: Use global variables, singletons (except AIManager), or service locators
- **Always**: Inject EventStore, StateMachine, AIManager through constructors

#### 3. Type Safety is Non-Negotiable
- **Rule**: Type hints required on ALL function signatures and class attributes
- **Why**: Early error detection, better IDE support, self-documenting code
- **Never**: Use `Any` without explicit justification
- **Always**: Use specific types, `Optional[]`, `Union[]` when appropriate

#### 4. Separation of Concerns
- **Rule**: No rendering code in game logic files, no game logic in rendering files
- **Why**: Maintainability, testability, clear architecture
- **Never**: Import pygame in `src/core/` or `src/entities/` (logic layers)
- **Always**: Keep Model (core), View (ui), Controller (states) separate

### Code Quality Principles

#### 5. Test Coverage Requirement
- **Rule**: >= 80% test coverage required before merging any code
- **Why**: Quality assurance, regression prevention, documentation
- **Never**: Skip tests because "it's simple code"
- **Always**: Write unit tests alongside implementation

#### 6. Specific Error Handling
- **Rule**: Use specific exception types, never bare `except:`
- **Why**: Proper error handling, debugging capability, expected vs unexpected errors
- **Never**: `except:` or `except Exception:` without re-raising
- **Always**: Catch specific exceptions, log errors, handle gracefully

#### 7. Documentation Standards
- **Rule**: Google-style docstrings on all public methods and classes
- **Why**: Self-documenting code, API clarity, IDE integration
- **Never**: Leave public APIs undocumented
- **Always**: Include Args, Returns, Raises sections in docstrings

### AI Integration Principles

#### 8. Never Block the Game Loop
- **Rule**: All AI/LLM calls MUST be async and non-blocking
- **Why**: Game must remain responsive, 60 FPS target
- **Never**: Use synchronous HTTP requests in game loop
- **Always**: Use `async/await`, timeouts, and fallbacks

#### 9. Always Have Fallbacks
- **Rule**: Every AI feature must have a rule-based fallback
- **Why**: Game must be playable even when AI unavailable
- **Never**: Make AI required for core gameplay
- **Always**: Implement fallback before AI integration

#### 10. Token Budget Compliance
- **Rule**: 4096 token hard limit, validate before sending to Ollama
- **Why**: Llama 3.2 context window limitation
- **Never**: Send unchecked prompts to LLM
- **Always**: Count tokens, truncate if needed, cache responses

### Database Principles

#### 11. Events are Immutable
- **Rule**: NEVER UPDATE or DELETE from `game_events` table
- **Why**: Event sourcing integrity, audit trail, timeline replay
- **Never**: Modify historical events
- **Always**: INSERT new events, mark timelines inactive if needed

#### 12. Transaction Safety
- **Rule**: Always use transactions for multi-step database operations
- **Why**: ACID guarantees, data consistency, rollback capability
- **Never**: Execute related operations without transaction
- **Always**: Use `with` statement or explicit begin/commit/rollback

#### 13. Database Separation
- **Rule**: SQLite for OLTP (transactional), DuckDB for OLAP (analytics)
- **Why**: Right tool for right job, performance optimization
- **Never**: Mix analytical queries with transactional database
- **Always**: Use dbt to transform SQLite events into DuckDB analytics

### Performance Principles

#### 14. 60 FPS Target
- **Rule**: Game loop must maintain target tick rate consistently
- **Why**: Smooth gameplay, good user experience
- **Never**: Block game loop with long operations
- **Always**: Profile performance, optimize hotspots, keep frame time < 16ms

#### 15. Responsive AI
- **Rule**: < 5 second response time for AI features, timeout to fallback
- **Why**: User experience, game flow
- **Never**: Wait indefinitely for AI response
- **Always**: Set timeouts, trigger fallback on timeout

## Deviation Protocol

If you MUST deviate from these principles:

### Step 1: Justify
- Document WHY the deviation is necessary
- Explain what alternatives were considered
- Describe the impact of NOT deviating

### Step 2: Document
- Add entry to `assignments/active/phase-X/decisions.md`
- Include:
  - Which principle is being violated
  - Justification and rationale
  - Trade-offs accepted
  - Mitigation plan

### Step 3: Get Approval
- Human review required for principle deviations
- AI agents cannot self-approve deviations
- Must be explicitly acknowledged

### Step 4: Create Technical Debt
- Open GitHub issue tagged with `tech-debt`
- Link to decision document
- Plan remediation path
- Set target date for resolution

### Step 5: Remediate
- Address technical debt in future phases
- Don't accumulate deviations without resolution plan
- Prioritize based on impact

## Enforcement

### AI Agents
- Must check constitution before making architectural decisions
- Must reference constitution in decision documents
- Must flag potential violations for human review
- Cannot proceed with unchecked deviations

### Developers
- Review constitution before starting new features
- Reference in code reviews
- Challenge violations in pull requests
- Update constitution if principles evolve

### Code Reviews
- Constitution compliance is a review criterion
- Reviewers must check for violations
- Deviations require explicit approval
- Document all approved deviations

## Updates to Constitution

### When to Update
- New architectural patterns adopted
- Lessons learned from production issues
- Technology changes requiring new principles
- Team grows and needs clearer guidelines

### Update Process
1. Propose change in GitHub issue
2. Discuss trade-offs and implications
3. Update constitution with version bump
4. Notify all contributors
5. Update existing code if principle changes

### Versioning
- **Major**: Change to existing principle (1.0.0 → 2.0.0)
- **Minor**: Addition of new principle (1.0.0 → 1.1.0)
- **Patch**: Clarification or formatting (1.0.0 → 1.0.1)

## Constitution Checkpoints

Run constitution check at these milestones:

- [ ] Before creating phase plan
- [ ] Before starting implementation
- [ ] Before code review
- [ ] Before merging to main
- [ ] During architecture review
- [ ] When adding new dependencies

## Related Documents
- `.cursor/rules/architect-supervisor.mdc` - Architecture orchestration
- `.cursor/rules/ai-integration-supervisor.mdc` - AI principles
- `.cursor/rules/data-worker.mdc` - Database principles
- `assignments/templates/DECISIONS_TEMPLATE.md` - Decision logging format

---

**This constitution is the foundation of Temporal Echoes development. When in doubt, refer back to these principles.**

