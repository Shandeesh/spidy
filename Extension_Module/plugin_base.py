"""
Spidy Plugin Base — Abstract base class and auto-loading PluginLoader.
All plugins in Extension_Module/plugins/ are auto-discovered on startup.

To create a plugin:
    1. Create a .py file in Extension_Module/plugins/
    2. Subclass SpidyPlugin
    3. Override the event hooks you need
    4. The PluginLoader will find and initialize it automatically.
"""
import os
import sys
import importlib.util
import traceback


class SpidyPlugin:
    """Abstract base class for all Spidy extension plugins."""

    name: str = "BasePlugin"
    enabled: bool = True

    def on_trade_open(self, symbol: str, action: str, volume: float,
                      price: float, ticket: int, strategy: str) -> None:
        """Called immediately after a trade is successfully opened."""
        pass

    def on_trade_close(self, symbol: str, action: str, profit: float,
                       ticket: int, reason: str) -> None:
        """Called immediately after a trade is successfully closed."""
        pass

    def on_alert(self, level: str, message: str) -> None:
        """
        Called when a system alert fires (e.g. daily loss limit, brute-force).
        level: 'INFO' | 'WARNING' | 'CRITICAL'
        """
        pass

    def on_bridge_start(self) -> None:
        """Called once when the bridge server finishes startup."""
        pass


class PluginLoader:
    """
    Auto-discovers and loads all SpidyPlugin subclasses from
    Extension_Module/plugins/*.py at startup.
    """

    def __init__(self, plugins_dir: str | None = None):
        if plugins_dir is None:
            plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
        self._dir     = plugins_dir
        self._plugins: list[SpidyPlugin] = []
        self._load_all()

    def _load_all(self) -> None:
        if not os.path.isdir(self._dir):
            os.makedirs(self._dir, exist_ok=True)
            return

        for fname in os.listdir(self._dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            fpath = os.path.join(self._dir, fname)
            try:
                spec   = importlib.util.spec_from_file_location(fname[:-3], fpath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                for attr_name in dir(module):
                    cls = getattr(module, attr_name)
                    if (isinstance(cls, type)
                            and issubclass(cls, SpidyPlugin)
                            and cls is not SpidyPlugin):
                        instance = cls()
                        if instance.enabled:
                            self._plugins.append(instance)
                            print(f"[PluginLoader] Loaded: {instance.name}")
            except Exception:
                print(f"[PluginLoader] Failed to load {fname}:\n{traceback.format_exc()}")

    def fire(self, event: str, **kwargs) -> None:
        """
        Fire an event on all loaded plugins.
        Plugins that raise exceptions are silently skipped.
        """
        for plugin in self._plugins:
            try:
                handler = getattr(plugin, event, None)
                if callable(handler):
                    handler(**kwargs)
            except Exception:
                pass  # Plugin errors must never crash the bridge

    @property
    def loaded(self) -> list[str]:
        return [p.name for p in self._plugins]
