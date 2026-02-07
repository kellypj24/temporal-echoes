# States Module Rules

Game state handler implementations (controllers in MVC). Coordinates model (core) and view (ui).

## Rules
- Each state handler implements: `update(delta_time)`, `handle_input(event)`, `render(renderer)`
- State handlers coordinate between core logic and UI — they don't contain business logic themselves
- Use dependency injection for all managers/stores
- Emit events for all meaningful state changes
- Type hints required on all functions

## Reference
Full patterns: `.cursor/rules/game-logic-worker.mdc`
