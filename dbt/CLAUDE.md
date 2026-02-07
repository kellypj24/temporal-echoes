# dbt Analytics Rules

dbt-DuckDB OLAP layer for gameplay analytics. Sources from SQLite event store.

## Rules
- **Staging models**: Incremental materialization, raw event transformations, enrich with joins
- **Intermediate models**: Table materialization, business logic and aggregations
- **Analytics models**: Incremental materialization, game-ready metrics
- All models MUST have schema tests (unique, not_null, accepted_range)
- Use dbt macros for reusable game calculations (combo multipliers, damage, critical chance)
- Source from SQLite via `sqlite_scanner` extension
- Never run dbt in the game loop — refresh analytics async or on-demand
- Use incremental models for real-time data processing
- All dbt models need schema.yml with column descriptions and tests

## Key Macros
- `calculate_combo_multiplier(combo_count)` - Damage multiplier tiers
- `timeline_divergence_modifier(divergence_score)` - Timeline impact scaling
- `calculate_critical_chance(base_chance, luck_stat, combo_count)` - Crit calculation

## Database Separation
- SQLite (`data/events.db`): OLTP writes, event sourcing, ACID transactions
- DuckDB (`data/analytics.duckdb`): OLAP reads, analytics queries, columnar storage

## Reference
Full patterns and schemas: `.cursor/rules/data-worker.mdc`
