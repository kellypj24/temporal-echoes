# Entities Module Rules

Game objects: Player, NPC, Item, etc. Pure data + behavior, **no rendering code**.

## Rules
- NEVER import pygame in this module
- Use dataclasses for entity definitions (not dicts)
- Use Enums for entity types, item types, directions
- All entities inherit from base `GameObject` (id, position, sprite_key)
- Type hints required on all attributes and methods
- Entity state changes should be trackable via events

## Reference
Full patterns: `.cursor/rules/pygame-worker.mdc` (entity rendering in ui/), `.cursor/rules/game-logic-worker.mdc` (entity logic)
