#                                   MIT License
#
#              Copyright (c) 2021 Javier Alonso <jalonso@teldat.com>
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
"""Client entrypoint - :func:`main` handles the petitions for incoming requests"""
from __future__ import annotations

import errno
import sys
import typing
from queue import Empty
from datetime import datetime

import systemd.daemon as systemd
from orcha import properties
from orcha.interfaces import Message
from orcha.lib import ClientManager
from orcha.plugins import BasePlugin
from orcha.utils import version

from .constants import WATCHDOG_ID

if typing.TYPE_CHECKING:
    import argparse

__version__ = "0.0.1"


class WatchdogClient(BasePlugin):
    """Plugin that sends a :obj:`WatchdogPetition` through the pluggable interface, by simply
    sending a message with the 
    """

    name = "watchdog"
    alias = ("wd",)
    help = "send a watchdog request to the main Orcha service"

    def create_parser(self, parser: argparse.ArgumentParser):
        parser.add_argument(
            "--timeout",
            type=float,
            default=None,
            help="Timeout in seconds to wait until considering the request failed",
        )

    def handle(self, args: argparse.Namespace) -> int:
        manager = ClientManager(
            properties.listen_address, properties.port, properties.authkey,
        )
        start = datetime.utcnow()
        if not manager.connect():
            error_msg = f"Cannot connect to server {properties.listen_address}:{properties.port}"
            print(error_msg, file=sys.stderr)
            systemd.notify(f"STATUS={error_msg}")
            systemd.notify(f"ERRNO={errno.ECONNREFUSED}")

        systemd.notify("READY=1")
        queue = manager.manager.Queue()
        manager.send(Message(WATCHDOG_ID, {"queue": queue}))
        systemd.notify(f"STATUS=Waiting for confirmation (since {start.isoformat()})")
        try:
            ret = queue.get(timeout=args.timeout)
            end = datetime.utcnow()
            systemd.notify(f"STATUS=Finished with status code={ret} (elapsed time={end - start})")

            return ret
        except Empty:
            error_msg = (
                "Did not receive a response from server in time "
                f"(more than {args.timeout} seconds have passed)"
            )
            print(error_msg, file=sys.stderr)
            systemd.notify(f"STATUS={error_msg}")
            systemd.notify(f"ERRNO={errno.ETIMEDOUT}")

            return errno.ETIMEDOUT

    @staticmethod
    def version() -> str:
        return f"watchdog - {version('orcha-watchdog')}"
