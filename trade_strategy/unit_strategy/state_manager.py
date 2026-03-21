class StateManager:
    """External state store for stateful conditions.

    Keyed by an arbitrary hashable key (typically ``id(condition)``).
    Separating state from logic means the same :class:`Condition` object can be
    reused across multiple strategies without state bleeding between them.

    Example::

        sm = StateManager()
        state = sm.get_state(id(cond), {"count": 0})
        state["count"] += 1
        sm.set_state(id(cond), state)
    """

    def __init__(self) -> None:
        self._states: dict = {}

    def get_state(self, key, default: dict | None = None) -> dict:
        """Return the state for *key*, initialising it from *default* if absent."""
        if key not in self._states and default is not None:
            self._states[key] = dict(default)
        return self._states.get(key)

    def set_state(self, key, value: dict) -> None:
        """Store *value* under *key*."""
        self._states[key] = value

    def reset(self) -> None:
        """Clear all stored state (e.g. at the start of a backtest episode)."""
        self._states.clear()
