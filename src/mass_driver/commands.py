"""The different main commands of the mass-driver tool"""

import sys
from argparse import Namespace
from pathlib import Path
from typing import Callable

from pydantic import ValidationError

from mass_driver.discovery import (
    discover_drivers,
    discover_forges,
    get_driver_entrypoint,
    get_forge_entrypoint,
    get_scanners,
)
from mass_driver.forge_run import main as forge_main
from mass_driver.forge_run import pause_until_ok
from mass_driver.migration_run import main as migration_main
from mass_driver.models.activity import ActivityLoaded, ActivityOutcome
from mass_driver.scan_run import scan_main


def drivers_command(args: Namespace):
    """Process the CLI for 'Drivers' subcommand"""
    return plugins_command(args, "driver", get_driver_entrypoint, discover_drivers)


def forges_command(args: Namespace):
    """Process the CLI for 'Forges' subcommand"""
    return plugins_command(args, "forge", get_forge_entrypoint, discover_forges)


def plugins_command(
    args: Namespace, plugin: str, entrypoint: Callable, discover: Callable
):
    """Process the CLI for a generic plugin subcommand"""
    if args.info:
        target_plugin = args.info
        try:
            plugin_obj = entrypoint(target_plugin)
            print(
                f"Plugin name: {plugin_obj.name}; Import path: "
                f"{plugin_obj.module}; Class: {plugin_obj.attr}"
            )
            print(plugin_obj.load().__doc__)
            return
        except ImportError as e:
            print(str(e), file=sys.stderr)
            print(f"Try `mass driver {plugin}s --list`", file=sys.stderr)
            return
    # if args.list:  # Implicit
    plugins = discover()
    print("Available plugins:")
    for plugin_obj in plugins:
        print(plugin_obj.name)
    return True


def run_command(args: Namespace) -> ActivityOutcome:
    """Process the CLI for 'run'"""
    print("Run mode!")
    repos = read_repolist(args)
    activity_str = args.activity_file.read()
    try:
        activity = ActivityLoaded.from_config(activity_str)
    except ValidationError as e:
        forge_config_error_exit(e)
    if activity.migration is None:
        print("No migration section: skipping migration")
        migration_result = ActivityOutcome(
            repos_input=repos,
            local_repos_path={r: Path(r) for r in repos},
        )
    else:
        migration_result = migration_main(
            activity.migration,
            repos,
            not args.no_cache,
        )
    print("Migration complete!")
    if activity.forge is None:
        # Nothing else to do, just print completion and exit
        print("No Forge available: end")
        maybe_save_outcome(args, migration_result)
        return migration_result
    # Now guaranteed to have a Forge: pause + forge
    if not args.no_pause:
        print("Review the commits now.")
        pause_until_ok("Type y/yes/continue to run the Forge\n")
    forge_result = forge_main(activity.forge, migration_result)
    maybe_save_outcome(args, forge_result)
    return forge_result


def scanners_command(args: Namespace):
    """Process the CLI for 'scan'"""
    print("Available scanners:")
    scanners = get_scanners()
    for scanner in scanners:
        print(scanner.name)
    return True


def scan_command(args: Namespace) -> ActivityOutcome:
    """Process the CLI for 'scan'"""
    print("Scan mode!")
    repos = read_repolist(args)
    activity_str = args.activity_file.read()
    activity = ActivityLoaded.from_config(activity_str)
    result = scan_main(
        activity.scan,
        repo_urls=repos,
        cache=not args.no_cache,
    )
    maybe_save_outcome(args, result)
    return result


def forge_config_error_exit(e: ValidationError):
    """Exit in case of bad forge config"""
    for error in e.errors():
        if error["type"] == "value_error.missing":
            envvars = ["FORGE_" + var.upper() for var in error["loc"]]
            print(
                f"Missing Forge config: Set envvar(s) {', '.join(envvars)}",
                file=sys.stderr,
            )
        else:
            print(
                f"Forge config validation error: {error}",
                file=sys.stderr,
            )
    raise e  # exit code = Simulate the argparse behaviour of exiting on bad args


def read_repolist(args) -> list[str]:
    """Read the repo-list or repo-path arg"""
    repos = args.repo_path
    if args.repo_filelist:
        repos = args.repo_filelist.read().strip().split("\n")
    return repos


def maybe_save_outcome(args: Namespace, outcome: ActivityOutcome):
    """Consider saving the outcome"""
    if not args.json_outfile:
        return
    save_outcome(outcome, args.json_outfile)
    print("Saved outcome to given JSON file")


def save_outcome(outcome: ActivityOutcome, out_file):
    """Save the output to given JSON file handle"""
    out_file.write(outcome.json(indent=2))
    out_file.write("\n")
