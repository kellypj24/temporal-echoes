# Core Module Rules

This module contains state machines, event store, and core game logic. **No rendering code allowed.**

## Rules
- NEVER import pygame in this module
- All state changes MUST emit events to EventStore (append-only)
- Use dependency injection: pass EventStore, session_id via constructors
- Type hints required on ALL functions and class attributes
- Use dataclasses for data structures, Enums for state/constants
- State machine must validate transitions before executing them
- Invalid transitions must raise `StateTransitionError`

## Event Emission
Every state change emits a `GameEvent` with: event_id, timestamp, session_id, timeline_id, event_type, player_id, state_before, player_action, outcome.

## Valid State Transitions
- MENU -> EXPLORING
- EXPLORING -> COMBAT, DIALOGUE, INVENTORY, TIMELINE_VIEW
- COMBAT, DIALOGUE, INVENTORY, TIMELINE_VIEW -> EXPLORING

## Reference
Full patterns: `.cursor/rules/game-logic-worker.mdc`
