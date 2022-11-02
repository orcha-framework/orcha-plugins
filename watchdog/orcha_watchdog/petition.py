#                                   MIT License
#
#              Copyright (c) 2022 Javier Alonso <jalonso@teldat.com>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#      copies of the Software, and to permit persons to whom the Software is
#            furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
#                 copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#     AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#                                    SOFTWARE.
"""Watchdog petition class"""
from __future__ import annotations

import systemd.daemon as systemd
import typing

from dataclasses import dataclass
from datetime import datetime

from orcha.interfaces import Petition, PetitionState
from orcha.utils import nopr

from .constants import WATCHDOG_ID

if typing.TYPE_CHECKING:
    from queue import Queue
    from typing import Optional


@dataclass(init=False)
class WatchdogPetition(Petition):
    """
    Watchdog petition has always the greatest priority so it should be run the first
    whenever it is received. It is used for indicating whether the processor should
    watchdog the SystemD main process so we inform we are still running.

    Warning:
        The priority of this petition is always the higher (using ``float("-inf")``),
        be careful whenever you place a custom petition with higher priority: do not
        use ``float("-inf")`` as an expression, try keeping your priorities above ``0``
        an go as high as you want.
    """

    # maximum priority, our life depends on it
    priority = float("-inf")
    id = WATCHDOG_ID
    condition = nopr(True)
    terminate = nopr(True)

    def __init__(self, queue: Optional[Queue] = None):
        self.queue = queue
        self.creation_time = datetime.utcnow()
        self.elapsed_time = -1

    def action(self, *_, **__):
        """Sends a watchdog message to SystemD based on given petition."""

        try:
            systemd.notify("WATCHDOG=1")
            if self.queue is not None:
                self.finish(0)
        except (EOFError, ConnectionError):
            self.state = PetitionState.BROKEN
            self.elapsed_time = self.creation_time - datetime.utcnow()
