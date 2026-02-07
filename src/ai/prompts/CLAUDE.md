# Prompts Module Rules

Prompt engineering for AI Dungeon Master.

## Rules
- All prompts use structured format: [ROLE] [CONTEXT] [TASK] [CONSTRAINTS] [FORMAT]
- Always request JSON output with a defined schema
- Prompt + expected response must fit in 4096 tokens
- Use `PromptTemplate` with required/optional vars — never hardcode prompts
- Version all prompt templates for A/B testing and rollback
- Truncation strategy: keep recent events, summarize older ones
- Use sliding window for conversation history
- Token efficiency: be concise, don't waste tokens on verbose phrasing
- Match 16-bit RPG aesthetic (Chrono Trigger, Final Fantasy VI tone)

## Prompt Types
- COMBAT_NARRATIVE, NPC_DIALOGUE, LOCATION_DESCRIPTION, QUEST_GENERATION, EVENT_DESCRIPTION, TIMELINE_NARRATION

## Reference
Full templates and Pydantic response models: `.cursor/rules/prompt-worker.mdc`
