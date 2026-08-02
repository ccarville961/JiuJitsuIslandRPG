# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

from tuxemon.constants.paths import get_plugin_paths, mods_folder
from tuxemon.plugin import PluginManager
from tuxemon.state.state import State

if TYPE_CHECKING:
    from tuxemon.state.repository import StateRepository

logger = logging.getLogger(__name__)


class StateLoader:
    """
    Discovers and registers game state classes using the new plugin system.
    """

    def __init__(self, base_package: str, lib_dir: Path) -> None:
        """
        Initializes the StateLoader.

        Parameters:
            base_package: The base package name (e.g., "my_game.states") to
                scan for states.
            lib_dir: The base directory where game libraries are located
                (e.g., paths.LIBDIR).
        """
        self.base_package = base_package
        self.lib_dir = lib_dir

    def _build_plugin_manager(
        self,
        folders: list[Path],
        include: list[str] | None = None,
        exclude: list[str] = ["State"],
    ) -> PluginManager:
        """
        Helper to create a PluginManager configured for state discovery.
        """
        return PluginManager.from_directory(
            plugin_folders=folders,
            root_path=mods_folder.parent,
            include=include,
            exclude=exclude,
        )

    def auto_state_discovery(self, repository: StateRepository) -> None:
        """
        Discover and register game states from core and mod folders using
        the new plugin architecture.
        """
        state_folder = self.lib_dir / Path(*self.base_package.split(".")[1:])
        logger.info(f"Initiating game state discovery from {state_folder}")

        plugin_folders: list[Path] = []
        core_includes: list[str] = []

        if state_folder.is_dir():
            plugin_folders.append(state_folder)
            core_includes = [
                f.stem
                for f in state_folder.glob("*.py")
                if f.is_file() and f.stem != "State"
            ]
        else:
            logger.warning(
                f"State discovery path does not exist: {state_folder}"
            )

        mod_state_folders = get_plugin_paths(
            base_path=mods_folder,
            category="states",
            subfolder=None,
        )

        mod_includes = [
            f.stem
            for folder in mod_state_folders
            for f in folder.glob("*.py")
            if f.is_file() and f.stem != "__init__"
        ]

        core_pm = self._build_plugin_manager(
            folders=[state_folder],
            include=core_includes,
            exclude=["State"],
        )

        mod_pm = self._build_plugin_manager(
            folders=mod_state_folders,
            include=mod_includes,
            exclude=["State"],
        )

        # Register core states discovered through the existing filesystem
        # plugin system first.
        for plugin in core_pm.get_all_plugins(interface=State):
            repository.add_state(plugin.plugin_object)

        # Android/package fallback:
        # Packaged applications do not always expose their Python package
        # directories in exactly the same way as a normal source checkout.
        # Discover modules through Python's package system and register any
        # locally-defined State subclasses that filesystem discovery missed.
        registered = repository.all_states()

        if "BackgroundState" not in registered or "IntroState" not in registered:
            logger.warning(
                "Filesystem state discovery was incomplete; "
                "running package-based state discovery."
            )

            package = importlib.import_module(self.base_package)
            package_paths = getattr(package, "__path__", [])

            for module_info in pkgutil.iter_modules(
                package_paths,
                package.__name__ + ".",
            ):
                module_name = module_info.name

                try:
                    module = importlib.import_module(module_name)
                except Exception as exc:
                    logger.error(
                        f"Skipping state module '{module_name}': {exc}"
                    )
                    continue

                for _, state_class in inspect.getmembers(
                    module,
                    inspect.isclass,
                ):
                    if state_class is State:
                        continue

                    try:
                        is_state_class = issubclass(state_class, State)
                    except TypeError:
                        # Some typing and extension objects can appear class-like
                        # to inspect.isclass() but cannot be used with issubclass().
                        logger.debug(
                            "Skipping non-class-like object %r from %s",
                            state_class,
                            module.__name__,
                        )
                        continue

                    if not is_state_class:
                        continue

                    # Do not register classes merely imported into this module.
                    if state_class.__module__ != module.__name__:
                        continue

                    if state_class.__name__ not in repository.all_states():
                        logger.info(
                            f"Package discovery registering state: "
                            f"{state_class.__name__}"
                        )
                        repository.add_state(state_class)

        # Mods override core states.
        for plugin in mod_pm.get_all_plugins(interface=State):
            repository.add_state(plugin.plugin_object)
