#!/usr/bin/env python3
"""
Free Up Space macOS - A tool to move large applications to removable drives
to free up space on your Mac's main drive.
"""

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    from rich.panel import Panel
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
    )
    from rich.text import Text
    from rich import box
except ImportError:
    print("Error: rich library not found. Please install it with: pip install rich")
    sys.exit(1)

console = Console()


def check_root_privileges():
    """Check if the script is running with root privileges."""
    if os.geteuid() != 0:
        console.print(
            Panel.fit(
                "[bold red]Root privileges required![/bold red]\n\n"
                "This script needs to run with sudo to access /Applications and /Volumes.\n"
                "Please run it with:\n\n"
                "[bold cyan]sudo python free-up-space-macos.py[/bold cyan]",
                border_style="red",
                title="Permission Error",
            )
        )
        sys.exit(1)


class AppInfo:
    """Represents information about a macOS application."""

    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.size_bytes = self._calculate_size()
        self.size_gb = self.size_bytes / (1024**3)

    def _calculate_size(self) -> int:
        """Calculate the total size of the application bundle."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(self.path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        continue
        except (OSError, FileNotFoundError):
            pass
        return total_size

    def __str__(self) -> str:
        return f"{self.name} ({self.size_gb:.2f} GB)"


class SpaceManager:
    """Main class for managing application storage."""

    def __init__(self):
        self.applications_dir = Path("/Applications")
        self.volumes_dir = Path("/Volumes")

    def get_applications(self) -> List[AppInfo]:
        """Get all applications from /Applications directory."""
        apps = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning applications...", total=None)

            try:
                for app_path in self.applications_dir.iterdir():
                    if app_path.is_dir() and app_path.suffix == ".app":
                        apps.append(AppInfo(app_path))
            except PermissionError:
                console.print(
                    "[red]Error: Permission denied accessing /Applications[/red]"
                )
                sys.exit(1)

        # Sort by size (largest first)
        apps.sort(key=lambda x: x.size_bytes, reverse=True)
        return apps

    def select_apps_for_target_size(
        self, apps: List[AppInfo], target_gb: float
    ) -> List[AppInfo]:
        """Select applications that will free up the target amount of space."""
        selected_apps = []
        total_size_gb = 0.0

        for app in apps:
            if total_size_gb >= target_gb:
                break
            selected_apps.append(app)
            total_size_gb += app.size_gb

        return selected_apps

    def check_apps_in_use(self, apps: List[AppInfo]) -> List[AppInfo]:
        """Check which applications are currently in use."""
        apps_in_use = []

        console.print("\n[bold]Checking for running applications...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Checking applications...", total=len(apps))

            for app in apps:
                if self._check_app_in_use(app.path):
                    apps_in_use.append(app)
                progress.advance(task)

        return apps_in_use

    def show_close_apps_instructions(self, apps_in_use: List[AppInfo]):
        """Show instructions for closing running applications."""
        if not apps_in_use:
            return

        console.print("\n[bold yellow]To close running applications:[/bold yellow]")
        console.print("[dim]1. Use Command+Q to quit each application[/dim]")
        console.print("[dim]2. Or use Activity Monitor to force quit if needed[/dim]")
        console.print(
            "[dim]3. Check for background processes in Activity Monitor[/dim]"
        )

        # Show specific processes if possible
        for app in apps_in_use:
            try:
                import subprocess

                result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                if result.returncode == 0:
                    lines = result.stdout.split("\n")
                    matching_processes = [
                        line for line in lines if app.name.lower() in line.lower()
                    ]
                    if matching_processes:
                        console.print(f"\n[bold]Processes for {app.name}:[/bold]")
                        for process in matching_processes[:3]:  # Show first 3 matches
                            parts = process.split()
                            if len(parts) > 1:
                                pid = parts[1]
                                console.print(
                                    f"[dim]  PID {pid}: {' '.join(parts[10:])}[/dim]"
                                )
            except Exception:
                pass

    def display_apps_table(self, apps: List[AppInfo], title: str = "Applications"):
        """Display applications in a formatted table."""
        table = Table(title=title, box=box.ROUNDED)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Size (GB)", style="magenta", justify="right")
        table.add_column("Path", style="dim")

        for app in apps:
            table.add_row(app.name, f"{app.size_gb:.2f}", str(app.path))

        console.print(table)

    def get_available_volumes(self) -> List[Path]:
        """Get list of available volumes (removable drives)."""
        volumes = []
        try:
            for volume in self.volumes_dir.iterdir():
                if volume.is_dir() and volume.name not in [
                    "Macintosh HD",
                    "Preboot",
                    "Recovery",
                ]:
                    volumes.append(volume)
        except PermissionError:
            console.print("[red]Error: Permission denied accessing /Volumes[/red]")
            sys.exit(1)

        return volumes

    def select_volume(self) -> Optional[Path]:
        """Prompt user to select a volume for storing applications."""
        volumes = self.get_available_volumes()

        if not volumes:
            console.print("[red]No removable drives found in /Volumes[/red]")
            return None

        console.print("\n[bold]Available volumes:[/bold]")
        for i, volume in enumerate(volumes, 1):
            console.print(f"{i}. {volume.name} ({volume})")

        while True:
            try:
                choice = Prompt.ask("Select volume (number)", default="1")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(volumes):
                    return volumes[choice_idx]
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number.[/red]")

    def create_backup_folder(self, volume: Path) -> Path:
        """Create a timestamped backup folder on the selected volume."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = volume / f"AppBackup_{timestamp}"
        backup_folder.mkdir(exist_ok=True)
        return backup_folder

    def _remove_extended_attributes(self, path: Path) -> bool:
        """Remove extended attributes from a file or directory."""
        try:
            # Use xattr to remove all extended attributes
            import subprocess

            result = subprocess.run(
                ["xattr", "-cr", str(path)], capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _fix_permissions_recursively(self, path: Path) -> bool:
        """Fix permissions recursively for a directory."""
        try:
            import subprocess

            # Use chmod recursively to fix permissions
            result = subprocess.run(
                ["chmod", "-R", "755", str(path)], capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_system_protection(self, path: Path) -> bool:
        """Check if a path has system protection that prevents moving."""
        try:
            import subprocess

            # Check for system integrity protection
            result = subprocess.run(
                ["ls", "-lO", str(path)], capture_output=True, text=True
            )
            if result.returncode == 0:
                # Look for "restricted" flag
                return "restricted" in result.stdout
            return False
        except Exception:
            return False

    def _check_app_in_use(self, app_path: Path) -> bool:
        """Check if an application is currently running."""
        try:
            import subprocess

            # Check if any process is using files in the app bundle
            result = subprocess.run(
                ["lsof", str(app_path)], capture_output=True, text=True
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def move_apps_to_volume(
        self, apps: List[AppInfo], backup_folder: Path
    ) -> Tuple[bool, List[AppInfo]]:
        """Move applications to the backup folder. Returns (success, failed_apps)."""
        console.print(f"\n[bold]Moving applications to: {backup_folder}[/bold]")
        failed_apps = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            for app in apps:
                task = progress.add_task(f"Moving {app.name}...", total=100)

                try:
                    destination = backup_folder / app.path.name

                    # Check if app is in use
                    if self._check_app_in_use(app.path):
                        console.print(
                            f"[yellow]⚠[/yellow] {app.name} appears to be in use. Attempting to force move..."
                        )

                    # Check for system protection
                    progress.update(task, completed=10)
                    if self._check_system_protection(app.path):
                        console.print(
                            f"[yellow]⚠[/yellow] {app.name} has system protection. Attempting to bypass..."
                        )

                    # Remove extended attributes that might prevent moving
                    progress.update(task, completed=25)
                    if not self._remove_extended_attributes(app.path):
                        console.print(
                            f"[yellow]⚠[/yellow] Could not remove extended attributes from {app.name}"
                        )

                    # Fix permissions recursively
                    progress.update(task, completed=40)
                    if not self._fix_permissions_recursively(app.path):
                        console.print(
                            f"[yellow]⚠[/yellow] Could not fix permissions for {app.name}"
                        )

                    # Try to change permissions to ensure we can move it
                    progress.update(task, completed=50)
                    try:
                        os.chmod(
                            app.path,
                            stat.S_IRWXU
                            | stat.S_IRGRP
                            | stat.S_IXGRP
                            | stat.S_IROTH
                            | stat.S_IXOTH,
                        )
                    except Exception:
                        pass  # Continue even if permission change fails

                    # Try to change ownership to root
                    progress.update(task, completed=60)
                    try:
                        import subprocess

                        subprocess.run(
                            ["chown", "-R", "root:wheel", str(app.path)],
                            capture_output=True,
                            check=False,
                        )
                    except Exception:
                        pass  # Continue even if ownership change fails

                    # Move the application
                    progress.update(task, completed=75)
                    shutil.move(str(app.path), str(destination))

                    # Set proper permissions on destination
                    os.chmod(
                        destination,
                        stat.S_IRWXU
                        | stat.S_IRGRP
                        | stat.S_IXGRP
                        | stat.S_IROTH
                        | stat.S_IXOTH,
                    )

                    progress.update(task, completed=100)
                    console.print(f"[green]✓[/green] Moved {app.name}")

                except (PermissionError, OSError, Exception) as e:
                    console.print(f"[red]✗[/red] Failed to move {app.name}: {e}")
                    failed_apps.append(app)

                    # Show manual move instructions
                    self._show_manual_move_instructions(app, backup_folder)

                    # Ask user to continue
                    if not Confirm.ask(f"Continue with remaining applications?"):
                        return False, failed_apps

        return len(failed_apps) == 0, failed_apps

    def _show_manual_move_instructions(self, app: AppInfo, backup_folder: Path) -> None:
        """Show instructions for manually moving a problematic application."""
        console.print(
            f"\n[bold yellow]Manual Move Required for {app.name}[/bold yellow]"
        )
        console.print(f"[dim]This application couldn't be moved automatically.[/dim]")
        console.print(f"\n[bold]Please do the following:[/bold]")
        console.print(f"[dim]1. Open Finder[/dim]")
        console.print(f"[dim]2. Navigate to: {app.path}[/dim]")
        console.print(f"[dim]3. Drag {app.name} to: {backup_folder}[/dim]")
        console.print(f"[dim]4. Delete the original from /Applications[/dim]")
        console.print(f"\n[bold]Or use Terminal:[/bold]")
        console.print(f"[dim]sudo mv '{app.path}' '{backup_folder}/'[/dim]")
        console.print(
            f"\n[yellow]Press Enter when you've completed the manual move...[/yellow]"
        )
        input()

    def test_app_move(self, app_path: Path) -> bool:
        """Test if an application can be moved by attempting a temporary move."""
        try:
            import tempfile
            import shutil

            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dest = Path(temp_dir) / app_path.name

                # Try to move to temp directory
                shutil.move(str(app_path), str(temp_dest))

                # Move it back
                shutil.move(str(temp_dest), str(app_path))

                return True
        except Exception as e:
            console.print(f"[dim]Test move failed: {e}[/dim]")
            return False

    def diagnose_app_protection(self, app_path: Path) -> None:
        """Diagnose what's protecting an application from being moved."""
        console.print(f"\n[bold]Diagnosing protection for {app_path.name}:[/bold]")

        try:
            import subprocess

            # Check extended attributes
            result = subprocess.run(
                ["xattr", "-l", str(app_path)], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                console.print(f"[yellow]Extended attributes found:[/yellow]")
                for line in result.stdout.strip().split("\n"):
                    console.print(f"[dim]  {line}[/dim]")
            else:
                console.print(f"[green]No extended attributes[/green]")

            # Check file flags
            result = subprocess.run(
                ["ls", "-lO", str(app_path)], capture_output=True, text=True
            )
            if result.returncode == 0:
                console.print(f"[yellow]File flags:[/yellow]")
                console.print(f"[dim]  {result.stdout.strip()}[/dim]")

            # Check if any processes are using it
            result = subprocess.run(
                ["lsof", str(app_path)], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                console.print(f"[red]Processes using this app:[/red]")
                lines = result.stdout.strip().split("\n")[1:]  # Skip header
                for line in lines[:5]:  # Show first 5 processes
                    console.print(f"[dim]  {line}[/dim]")
            else:
                console.print(f"[green]No processes using this app[/green]")

            # Check permissions
            stat_info = app_path.stat()
            console.print(f"[yellow]Permissions:[/yellow]")
            console.print(
                f"[dim]  Owner: {stat_info.st_uid}, Group: {stat_info.st_gid}[/dim]"
            )
            console.print(f"[dim]  Mode: {oct(stat_info.st_mode)}[/dim]")

        except Exception as e:
            console.print(f"[red]Diagnosis failed: {e}[/red]")

    def restore_apps_from_backup(self, backup_folder: Path) -> bool:
        """Restore applications from backup folder to /Applications."""
        if not backup_folder.exists():
            console.print(f"[red]Backup folder not found: {backup_folder}[/red]")
            return False

        apps_to_restore = [
            f for f in backup_folder.iterdir() if f.is_dir() and f.suffix == ".app"
        ]

        if not apps_to_restore:
            console.print("[red]No applications found in backup folder[/red]")
            return False

        console.print(
            f"\n[bold]Found {len(apps_to_restore)} applications to restore[/bold]"
        )

        # Display what will be restored
        self.display_apps_table(
            [AppInfo(app) for app in apps_to_restore], "Applications to Restore"
        )

        if not Confirm.ask("Do you want to restore these applications?"):
            console.print("Restore cancelled.")
            return False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            for app_path in apps_to_restore:
                task = progress.add_task(f"Restoring {app_path.stem}...", total=100)

                try:
                    destination = self.applications_dir / app_path.name

                    # Move the application back
                    shutil.move(str(app_path), str(destination))

                    # Set correct permissions
                    os.chmod(
                        destination,
                        stat.S_IRWXU
                        | stat.S_IRGRP
                        | stat.S_IXGRP
                        | stat.S_IROTH
                        | stat.S_IXOTH,
                    )

                    progress.update(task, completed=100)
                    console.print(f"[green]✓[/green] Restored {app_path.stem}")

                except Exception as e:
                    console.print(
                        f"[red]✗[/red] Failed to restore {app_path.stem}: {e}"
                    )
                    return False

        return True


def main():
    """Main function."""
    # Check for root privileges first
    check_root_privileges()

    parser = argparse.ArgumentParser(
        description="Free up space on macOS by moving large applications to removable drives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python free-up-space-macos.py                    # Interactive mode
  sudo python free-up-space-macos.py --restore /Volumes/MyDrive/AppBackup_20231201_143022
        """,
    )

    parser.add_argument(
        "--restore", type=str, help="Restore applications from backup folder"
    )

    args = parser.parse_args()

    # Display welcome banner
    console.print(
        Panel.fit(
            "[bold blue]Free Up Space macOS[/bold blue]\n"
            "Move large applications to removable drives to free up space",
            border_style="blue",
        )
    )

    manager = SpaceManager()

    # Handle restore mode
    if args.restore:
        backup_path = Path(args.restore)
        console.print(f"[bold]Restore mode: {backup_path}[/bold]")

        if manager.restore_apps_from_backup(backup_path):
            console.print(
                "\n[bold green]✓ Restore completed successfully![/bold green]"
            )
        else:
            console.print("\n[bold red]✗ Restore failed![/bold red]")
            sys.exit(1)
        return

    # Interactive mode
    try:
        # Get target size
        target_gb = float(
            Prompt.ask("How many gigabytes do you want to free up?", default="5.0")
        )

        console.print(
            f"\n[bold]Scanning applications to free up {target_gb} GB...[/bold]"
        )

        # Get all applications
        apps = manager.get_applications()

        if not apps:
            console.print("[red]No applications found in /Applications[/red]")
            return

        # Select apps to move
        selected_apps = manager.select_apps_for_target_size(apps, target_gb)

        if not selected_apps:
            console.print(
                "[red]No applications found that meet the size requirement[/red]"
            )
            return

        total_size = sum(app.size_gb for app in selected_apps)

        # Check for running applications
        apps_in_use = manager.check_apps_in_use(selected_apps)

        if apps_in_use:
            console.print(
                f"\n[yellow]⚠ Warning: {len(apps_in_use)} applications are currently running:[/yellow]"
            )
            for app in apps_in_use:
                console.print(f"  • {app.name}")
            console.print(
                "\n[dim]These applications may fail to move. Consider closing them first.[/dim]"
            )

            manager.show_close_apps_instructions(apps_in_use)

            if not Confirm.ask("Continue anyway?"):
                console.print("Operation cancelled.")
                return

        # Display selected apps
        console.print(
            f"\n[bold]Selected {len(selected_apps)} applications (Total: {total_size:.2f} GB)[/bold]"
        )
        manager.display_apps_table(selected_apps, "Applications to Move")

        # Confirm selection
        if not Confirm.ask(
            f"\nMove these applications to free up {total_size:.2f} GB?"
        ):
            console.print("Operation cancelled.")
            return

        # Select volume
        volume = manager.select_volume()
        if not volume:
            console.print("No volume selected. Operation cancelled.")
            return

        # Create backup folder
        backup_folder = manager.create_backup_folder(volume)
        console.print(f"[green]Created backup folder: {backup_folder}[/green]")

        # Move applications
        success, failed_apps = manager.move_apps_to_volume(selected_apps, backup_folder)

        if success:
            console.print(
                f"\n[bold green]✓ Successfully moved {len(selected_apps)} applications![/bold green]"
            )
            console.print(f"[bold]Backup location: {backup_folder}[/bold]")
            console.print(
                f"[dim]To restore later, use: sudo python {sys.argv[0]} --restore {backup_folder}[/dim]"
            )
        else:
            # Check what's in the backup folder
            moved_apps = [
                f for f in backup_folder.iterdir() if f.is_dir() and f.suffix == ".app"
            ]

            if moved_apps:
                console.print(
                    f"\n[green]✓ Successfully moved {len(moved_apps)} applications:[/green]"
                )
                for app in moved_apps:
                    console.print(f"  • {app.stem}")
                console.print(f"[bold]Backup location: {backup_folder}[/bold]")

            if failed_apps:
                console.print(
                    f"\n[yellow]⚠ {len(failed_apps)} applications required manual moving:[/yellow]"
                )
                for app in failed_apps:
                    console.print(f"  • {app.name}")
                console.print(f"[dim]These were moved manually as instructed.[/dim]")

            console.print(
                f"[dim]To restore later, use: sudo python {sys.argv[0]} --restore {backup_folder}[/dim]"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
