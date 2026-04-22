## 2024-05-19 - Frozenset over List for Immutable O(1) Lookups in Settings
**Learning:** Returning `list` from `@functools.cached_property` properties that are used primarily for containment checks (`in`) creates a performance bottleneck (O(N) lookup) in hot paths (like per-request IP validation).
**Action:** Always memoize these structures as `frozenset` instead of `list` to upgrade lookups to O(1) while maintaining immutability.
