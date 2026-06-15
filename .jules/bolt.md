## 2024-06-15 - Replace copy.deepcopy with .copy() for shallow dicts
**Learning:** `copy.deepcopy()` is significantly slower than `.copy()` due to internal memoization and recursion checks. When duplicating flat or shallow dictionaries (like simple string mappings in `InMemorySessionStore` representing `SessionInfo` metadata), `.copy()` provides better execution performance without side effects.
**Action:** Always use `.copy()` for dictionaries that don't contain nested mutable structures when returning defensively copied data.
