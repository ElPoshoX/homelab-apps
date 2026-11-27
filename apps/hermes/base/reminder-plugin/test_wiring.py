"""Regression: Hermes wires native handlers after Discord's first READY."""

import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class PluginWiringTests(unittest.IsolatedAsyncioTestCase):
    async def test_late_wiring_starts_one_worker_and_reconnect_does_not_duplicate(self):
        plugin_dir = Path(__file__).parent
        with tempfile.TemporaryDirectory() as root:
            plugins = types.ModuleType("plugins")
            storage = types.ModuleType("plugins.plugin_storage")
            storage.plugin_data_dir = lambda name: Path(root)
            fake_discord = types.ModuleType("discord")

            class Context:
                def register_tool(self, **kwargs):
                    pass

                def register_skill(self, *args):
                    pass

                def register_platform_handler(self, platform, factory):
                    self.factory = factory

            class Bot:
                def __init__(self):
                    self.listeners = {}
                    self.closed = False

                def add_listener(self, callback, event):
                    self.listeners[event] = callback

                def is_ready(self):
                    return True

                def is_closed(self):
                    return self.closed

                async def wait_until_ready(self):
                    pass

                def get_channel(self, channel_id):
                    return object()

            module_spec = importlib.util.spec_from_file_location(
                "kepler_reminder_test_package", plugin_dir / "__init__.py",
                submodule_search_locations=[str(plugin_dir)])
            module = importlib.util.module_from_spec(module_spec)
            with patch.dict(sys.modules, {"plugins": plugins, "plugins.plugin_storage": storage,
                                          "discord": fake_discord,
                                          "kepler_reminder_test_package": module}):
                module_spec.loader.exec_module(module)
                context = Context()
                module.register(context)
                bot = Bot()
                with patch.dict("os.environ", {"KEPLER_REMINDER_CHANNEL_ID": "1",
                                               "KEPLER_REMINDER_OWNER_ID": "2"}):
                    context.factory(bot, None)
                    for _ in range(3):
                        await asyncio.sleep(0)
                    workers = [task for task in asyncio.all_tasks() if task.get_name() == "kepler-reminders"]
                    self.assertEqual(len(workers), 1)
                    await bot.listeners["on_ready"]()
                    self.assertEqual(len([task for task in asyncio.all_tasks()
                                          if task.get_name() == "kepler-reminders"]), 1)
                    bot.closed = True
                    module._wake.set()
                    await asyncio.wait_for(workers[0], timeout=1)


if __name__ == "__main__":
    unittest.main()
