import argparse
from datetime import datetime

from orcha.plugins import BasePlugin
from orcha.utils import version


from .render import collect_events, render_events


class TimelineCLI(BasePlugin):
    name = "timeline"
    alias = ("tl",)
    help = "timeline operations"

    def create_parser(self, parser: argparse.ArgumentParser):
        subparsers = parser.add_subparsers(help="Timeline commands")
        render_parser = subparsers.add_parser("render", help="Render timeline")
        render_parser.add_argument(
            "-l",
            "--log",
            help="Orcha Timeline log file",
            default="/var/log/orcha-timeline",
            metavar="file",
        )
        render_parser.add_argument(
            "-o",
            "--output",
            help="Orcha Timeline output graph",
            metavar="file",
        )
        render_parser.add_argument(
            "-r",
            "--resolution",
            help="(x, y) resolution of the output graph in pixels",
            default=[1920, 1080],
            nargs=2,
        )
        render_parser.add_argument(
            "-f",
            "--format",
            help="Output format",
            choices=["png", "svg", "pdf", "ps"],
            default="png",
        )
        render_parser.add_argument(
            "-q", "--quiet", help="Quiet mode", action="store_true"
        )
        render_parser.add_argument(
            "-s", "--start", help="Graph start time", type=datetime.fromisoformat
        )
        render_parser.add_argument(
            "-e", "--end", help="Graph end time", type=datetime.fromisoformat
        )

    def handle(self, args: argparse.Namespace):
        if not args.quiet:
            print("Collecting events...")
        events = collect_events(args.log)

        if not args.quiet:
            print("Rendering events...")
        resolution = (args.resolution[0] / 100, args.resolution[1] / 100)
        output = args.output if args.output is not None else f"timeline.{args.format}"
        render_events(events, output, resolution, args.format)

        if not args.quiet:
            print("Done!")

    @staticmethod
    def version() -> str:
        return f"timeline - {version('orcha-timeline')}"
