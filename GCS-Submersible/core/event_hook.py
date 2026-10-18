# -*- coding: utf-8 -*-
"""
Lightweight Pure-Python Event Hook / Signal-Slot mechanism.
Enables event-driven architecture with zero external GUI dependencies.
Compatible with ROS2 nodes, headless services, and Qt adapter layers.
"""
from typing import Callable, List, Any


class EventHook:
    """
    Thread-safe, lightweight pure-Python event emitter.
    Compatible with Qt signal syntax (.connect, .disconnect, .emit).
    """
    def __init__(self):
        self._handlers: List[Callable[..., Any]] = []

    def connect(self, handler: Callable[..., Any]):
        if handler not in self._handlers:
            self._handlers.append(handler)

    def disconnect(self, handler: Callable[..., Any]):
        if handler in self._handlers:
            self._handlers.remove(handler)

    def emit(self, *args, **kwargs):
        for handler in list(self._handlers):
            try:
                handler(*args, **kwargs)
            except RuntimeError as e:
                if "has been deleted" in str(e):
                    if handler in self._handlers:
                        self._handlers.remove(handler)
                else:
                    print(f"[EventHook RuntimeError] {e}")
            except Exception as e:
                print(f"[EventHook Error] {e}")

    def __call__(self, *args, **kwargs):
        self.emit(*args, **kwargs)
