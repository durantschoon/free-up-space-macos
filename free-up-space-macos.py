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

        # Applications that should never be moved due to system integration or security
        self.protected_apps = {
            "1Password.app",
            "Obsidian.app",
        }

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
                        # Skip protected applications
                        if app_path.name in self.protected_apps:
                            console.print(
                                f"[dim]Skipping {app_path.name} (protected)[/dim]"
                            )
                            continue
                        apps.append(AppInfo(app_path))
            except PermissionError:
                console.print(
                    "[red]Error: Permission denied accessing /Applications[/red]"
                )
                sys.exit(1)

        # Sort by size (largest first)
        apps.sort(key=lambda x: x.size_bytes, reverse=True)
        return apps

    def get_current_free_space(self) -> float:
        """Get current free space on the main drive in GB."""
        try:
            import shutil

            # Get disk usage for the root filesystem
            total, used, free = shutil.disk_usage("/")
            return free / (1024**3)  # Convert bytes to GB
        except Exception:
            return 0.0

    def calculate_space_to_free(self, target_free_gb: float) -> float:
        """Calculate how much space needs to be freed to reach target free space."""
        current_free_gb = self.get_current_free_space()
        space_needed = target_free_gb - current_free_gb
        return max(0.0, space_needed)  # Don't return negative values

    def select_apps_for_target_free_space(
        self, apps: List[AppInfo], target_free_gb: float
    ) -> Tuple[List[AppInfo], float, float]:
        """Select applications to reach target free space. Returns (selected_apps, space_to_free, current_free)."""
        current_free_gb = self.get_current_free_space()
        space_to_free_gb = self.calculate_space_to_free(target_free_gb)

        if space_to_free_gb <= 0:
            return [], 0.0, current_free_gb

        selected_apps = []
        total_size_gb = 0.0

        for app in apps:
            if total_size_gb >= space_to_free_gb:
                break
            selected_apps.append(app)
            total_size_gb += app.size_gb

        return selected_apps, space_to_free_gb, current_free_gb

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

    def is_app_protected(self, app_path: Path) -> bool:
        """Check if an application is protected and should not be moved."""
        return app_path.name in self.protected_apps

    def get_protected_apps(self) -> List[str]:
        """Get list of protected application names."""
        return list(self.protected_apps)

    def display_protected_apps_info(self) -> None:
        """Display information about protected applications."""
        if self.protected_apps:
            console.print(
                f"\n[bold cyan]🔒 Protected Applications (will not be moved):[/bold cyan]"
            )
            for app_name in sorted(self.protected_apps):
                console.print(f"[dim]  • {app_name}[/dim]")
            console.print(
                f"[dim]These apps have system integration or security features that require them to stay in /Applications[/dim]"
            )

    def select_volume(self) -> Optional[Path]:
        """Prompt user to select a volume for storing applications."""
        volumes = self.get_available_volumes()

        if not volumes:
            console.print("[red]No removable drives found in /Volumes[/red]")
            return None

        # Check for rPi_1T volume specifically
        rpi_volume = None
        for volume in volumes:
            if volume.name == "rPi_1T":
                rpi_volume = volume
                break

        if rpi_volume:
            # Check for existing backup folders on rPi_1T
            existing_backups = self.find_backup_folders(rpi_volume)

            if len(existing_backups) == 1:
                # Found exactly one backup folder on rPi_1T
                console.print(f"\n[bold]Found existing backup folder on rPi_1T:[/bold]")
                console.print(f"[green]{existing_backups[0].name}[/green]")

                # Count apps in the existing folder
                app_count = len(
                    [
                        f
                        for f in existing_backups[0].iterdir()
                        if f.is_dir() and f.suffix == ".app"
                    ]
                )
                console.print(f"[dim]Contains {app_count} applications[/dim]")

                console.print("\n[bold]Choose an option:[/bold]")
                console.print("1. Reuse existing backup folder")
                console.print("2. Create new backup folder on rPi_1T")
                console.print("3. Select different volume")

                while True:
                    try:
                        choice = Prompt.ask("Select option (number)", default="1")
                        if choice == "1":
                            # Reuse existing folder
                            return rpi_volume, existing_backups[0]
                        elif choice == "2":
                            # Create new folder on rPi_1T
                            return rpi_volume, None
                        elif choice == "3":
                            # Show other volumes
                            break
                        else:
                            console.print(
                                "[red]Invalid selection. Please try again.[/red]"
                            )
                    except ValueError:
                        console.print("[red]Please enter a valid number.[/red]")
            elif len(existing_backups) > 1:
                # Multiple backup folders on rPi_1T - show them
                console.print(
                    f"\n[bold]Found {len(existing_backups)} backup folders on rPi_1T:[/bold]"
                )
                for i, folder in enumerate(existing_backups, 1):
                    app_count = len(
                        [
                            f
                            for f in folder.iterdir()
                            if f.is_dir() and f.suffix == ".app"
                        ]
                    )
                    console.print(f"{i}. {folder.name} ({app_count} apps)")

                console.print(
                    f"{len(existing_backups) + 1}. Create new backup folder on rPi_1T"
                )
                console.print(f"{len(existing_backups) + 2}. Select different volume")

                while True:
                    try:
                        choice = Prompt.ask("Select option (number)", default="1")
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(existing_backups):
                            # Reuse selected existing folder
                            return rpi_volume, existing_backups[choice_idx]
                        elif choice_idx == len(existing_backups):
                            # Create new folder on rPi_1T
                            return rpi_volume, None
                        elif choice_idx == len(existing_backups) + 1:
                            # Show other volumes
                            break
                        else:
                            console.print(
                                "[red]Invalid selection. Please try again.[/red]"
                            )
                    except ValueError:
                        console.print("[red]Please enter a valid number.[/red]")

        # Show all available volumes (including rPi_1T if no existing backups or user chose different volume)
        console.print("\n[bold]Available volumes:[/bold]")
        for i, volume in enumerate(volumes, 1):
            console.print(f"{i}. {volume.name} ({volume})")

        while True:
            try:
                choice = Prompt.ask("Select volume (number)", default="1")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(volumes):
                    return volumes[choice_idx], None
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number.[/red]")

    def create_backup_folder(
        self, volume: Path, existing_folder: Optional[Path] = None
    ) -> Path:
        """Create a timestamped backup folder on the selected volume, or reuse existing folder."""
        if existing_folder:
            console.print(
                f"[green]Reusing existing backup folder: {existing_folder}[/green]"
            )
            return existing_folder

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

                    # Check if app is protected
                    if self.is_app_protected(app.path):
                        console.print(
                            f"[yellow]⚠[/yellow] {app.name} is protected and cannot be moved"
                        )
                        failed_apps.append(app)
                        continue

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

                    # Move the application using copy-then-delete approach for better handling of protected apps
                    progress.update(task, completed=75)
                    move_success = self._move_app_robustly(app.path, destination)

                    if move_success:
                        # Set proper permissions on destination
                        try:
                            os.chmod(
                                destination,
                                stat.S_IRWXU
                                | stat.S_IRGRP
                                | stat.S_IXGRP
                                | stat.S_IROTH
                                | stat.S_IXOTH,
                            )
                        except Exception as e:
                            console.print(
                                f"[yellow]⚠[/yellow] Could not set permissions on destination: {e}"
                            )

                        progress.update(task, completed=100)
                        console.print(f"[green]✓[/green] Moved {app.name}")
                    else:
                        # Move failed, add to failed apps
                        failed_apps.append(app)
                        console.print(
                            f"[red]✗[/red] Failed to move {app.name} with all methods"
                        )

                        # Show manual move instructions (this will pause for user input)
                        self._show_manual_move_instructions(app, backup_folder)

                        # Ask user to continue
                        console.print(
                            f"\n[bold]Continue with remaining applications?[/bold]"
                        )
                        if not Confirm.ask("Continue?", default=True):
                            return False, failed_apps

                except (PermissionError, OSError, Exception) as e:
                    console.print(f"[red]✗[/red] Failed to move {app.name}: {e}")
                    failed_apps.append(app)

                    # Show manual move instructions (this will pause for user input)
                    self._show_manual_move_instructions(app, backup_folder)

                    # Ask user to continue
                    console.print(
                        f"\n[bold]Continue with remaining applications?[/bold]"
                    )
                    if not Confirm.ask("Continue?", default=True):
                        return False, failed_apps

        return len(failed_apps) == 0, failed_apps

    def _remove_app_safely(self, app_path: Path) -> bool:
        """Safely remove an application with better error handling."""
        try:
            import subprocess

            # Use rm -rf which is often faster and more reliable than shutil.rmtree
            result = subprocess.run(
                ["rm", "-rf", str(app_path)],
                capture_output=True,
                text=True,
                timeout=60,  # 60 second timeout
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            console.print(
                f"[red]✗[/red] Timeout removing {app_path.name} (took longer than 60 seconds)"
            )
            return False
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to remove {app_path.name}: {e}")
            return False

    def _show_manual_move_instructions(self, app: AppInfo, backup_folder: Path) -> None:
        """Show instructions for manually moving a problematic application."""
        # Clear any progress output and add visual separation
        console.print("\n" + "=" * 80)
        console.print(f"\n[bold red]⚠ MANUAL MOVE REQUIRED for {app.name}[/bold red]")
        console.print(f"[dim]This application couldn't be moved automatically.[/dim]")
        console.print("\n[bold cyan]📋 STEP-BY-STEP INSTRUCTIONS:[/bold cyan]")
        console.print(f"[bold]1.[/bold] Open Finder")
        console.print(f"[bold]2.[/bold] Navigate to: [cyan]{app.path}[/cyan]")
        console.print(
            f"[bold]3.[/bold] Drag [yellow]{app.name}[/yellow] to: [cyan]{backup_folder}[/cyan]"
        )
        console.print(f"[bold]4.[/bold] Delete the original from /Applications")

        console.print(f"\n[bold cyan]🔧 OR USE TERMINAL COMMAND:[/bold cyan]")
        console.print(f"[dim]sudo mv '{app.path}' '{backup_folder}/'[/dim]")

        console.print(
            f"\n[bold yellow]⏳ WAITING FOR YOU TO COMPLETE THE MANUAL MOVE...[/bold yellow]"
        )
        console.print(
            "[dim]Press Enter when you've finished moving the app manually.[/dim]"
        )
        console.print("=" * 80)

        # Use a more robust input method
        try:
            response = input(
                "\n>>> Press Enter when done (or type 'skip' to continue without this app): "
            ).strip()
            if response.lower() == "skip":
                console.print(
                    f"[yellow]Skipping {app.name} - you can move it manually later.[/yellow]"
                )
                return
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n[yellow]Manual move cancelled for {app.name}[/yellow]")
            return

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

    def find_backup_folders(self, volume: Path) -> List[Path]:
        """Find all AppBackup_* folders on a volume."""
        backup_folders = []
        try:
            for item in volume.iterdir():
                if item.is_dir() and item.name.startswith("AppBackup_"):
                    backup_folders.append(item)
        except Exception:
            pass
        return sorted(
            backup_folders, key=lambda x: x.name, reverse=True
        )  # Newest first

    def select_backup_folder(self, volume: Path) -> Optional[Path]:
        """Select a backup folder from a volume."""
        backup_folders = self.find_backup_folders(volume)

        if not backup_folders:
            console.print(f"[red]No backup folders found on {volume.name}[/red]")
            return None

        if len(backup_folders) == 1:
            console.print(
                f"[green]Found backup folder: {backup_folders[0].name}[/green]"
            )
            return backup_folders[0]

        console.print(
            f"\n[bold]Found {len(backup_folders)} backup folders on {volume.name}:[/bold]"
        )
        for i, folder in enumerate(backup_folders, 1):
            # Count apps in each folder
            app_count = len(
                [f for f in folder.iterdir() if f.is_dir() and f.suffix == ".app"]
            )
            console.print(f"{i}. {folder.name} ({app_count} apps)")

        console.print(f"{len(backup_folders) + 1}. Restore ALL backup folders")

        while True:
            try:
                choice = Prompt.ask("Select backup folder (number)", default="1")
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(backup_folders):
                    return backup_folders[choice_idx]
                elif choice_idx == len(backup_folders):
                    return "ALL"  # Special marker for restore all
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number.[/red]")

    def _calculate_app_hash(self, app_path: Path) -> str:
        """Calculate a hash of the app bundle for verification."""
        try:
            import hashlib

            hash_md5 = hashlib.md5()

            # Hash the Info.plist and executable as a quick integrity check
            info_plist = app_path / "Contents" / "Info.plist"
            if info_plist.exists():
                with open(info_plist, "rb") as f:
                    hash_md5.update(f.read())

            # Also hash the app name and size for additional verification
            hash_md5.update(app_path.name.encode())
            hash_md5.update(str(app_path.stat().st_size).encode())

            return hash_md5.hexdigest()
        except Exception:
            return ""

    def _apps_are_identical(self, source_path: Path, dest_path: Path) -> bool:
        """Check if two app bundles are identical."""
        try:
            if not dest_path.exists():
                return False

            # Quick size check first
            if source_path.stat().st_size != dest_path.stat().st_size:
                return False

            # Check if both have Info.plist
            source_info = source_path / "Contents" / "Info.plist"
            dest_info = dest_path / "Contents" / "Info.plist"

            if not (source_info.exists() and dest_info.exists()):
                return False

            # Compare Info.plist content
            with open(source_info, "rb") as f1, open(dest_info, "rb") as f2:
                return f1.read() == f2.read()

        except Exception:
            return False

    def _check_app_integrity(self, app_path: Path) -> bool:
        """Check if an app bundle has the essential files for restoration."""
        try:
            # Check for essential app bundle structure
            if not app_path.exists():
                return False

            # Check for Info.plist (essential for app bundles)
            info_plist = app_path / "Contents" / "Info.plist"
            if not info_plist.exists():
                console.print(f"[yellow]⚠[/yellow] {app_path.name}: Missing Info.plist")
                return False

            # Check for executable
            executable_name = None
            try:
                import plistlib

                with open(info_plist, "rb") as f:
                    plist = plistlib.load(f)
                    executable_name = plist.get("CFBundleExecutable")
            except Exception:
                pass

            if executable_name:
                executable_path = app_path / "Contents" / "MacOS" / executable_name
                if not executable_path.exists():
                    console.print(
                        f"[yellow]⚠[/yellow] {app_path.name}: Missing executable {executable_name}"
                    )
                    return False

            return True
        except Exception as e:
            console.print(
                f"[yellow]⚠[/yellow] {app_path.name}: Integrity check failed: {e}"
            )
            return False

    def find_recently_modified_apps(self, hours: int = 24) -> List[Path]:
        """Find recently modified apps in /Applications."""
        import time

        cutoff_time = time.time() - (hours * 3600)  # hours to seconds
        recent_apps = []

        try:
            for app_path in self.applications_dir.iterdir():
                if app_path.is_dir() and app_path.suffix == ".app":
                    # Check if the app was modified recently
                    if app_path.stat().st_mtime > cutoff_time:
                        # Filter out symlinks and aliases
                        if not self._is_symlink_or_alias(app_path):
                            recent_apps.append(app_path)
                        else:
                            console.print(
                                f"[yellow]⚠[/yellow] {app_path.name}: App appears to be a symlink or alias - skipping"
                            )
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Error scanning /Applications: {e}")

        # Sort by modification time (most recent first)
        recent_apps.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return recent_apps

    def _check_app_in_use(self, app_path: Path) -> bool:
        """Check if an app is currently in use by any process."""
        try:
            import subprocess

            # Use lsof to check if any process has the app open
            result = subprocess.run(
                ["lsof", str(app_path)], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0 and result.stdout.strip()
        except Exception:
            return False

    def _move_app_robustly(self, source: Path, destination: Path) -> bool:
        """Move an app using a robust copy-then-delete approach with multiple fallback methods."""
        try:
            # Method 1: Try direct move first (fastest for unprotected apps)
            try:
                shutil.move(str(source), str(destination))
                return True
            except (PermissionError, OSError) as e:
                console.print(f"[dim]Direct move failed: {e}[/dim]")
                console.print("[dim]Trying copy-then-delete approach...[/dim]")

            # Method 2: Copy-then-delete approach
            try:
                # Copy the entire app bundle
                shutil.copytree(str(source), str(destination), symlinks=True)

                # Verify the copy was successful by checking key files
                if self._verify_app_copy(source, destination):
                    # Remove the original
                    shutil.rmtree(str(source))
                    return True
                else:
                    # Copy verification failed, remove the incomplete copy
                    shutil.rmtree(str(destination), ignore_errors=True)
                    raise Exception("Copy verification failed")

            except Exception as e:
                console.print(f"[dim]Copy-then-delete failed: {e}[/dim]")
                console.print("[dim]Trying rsync approach...[/dim]")

            # Method 3: Use rsync (handles permissions and attributes better)
            try:
                import subprocess

                # Use rsync with proper flags for app bundles
                result = subprocess.run(
                    [
                        "rsync",
                        "-av",
                        "--delete",
                        "--progress",
                        f"{source}/",
                        str(destination),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )  # 5 minute timeout

                if result.returncode == 0:
                    # Verify the rsync copy
                    if self._verify_app_copy(source, destination):
                        # Remove the original
                        shutil.rmtree(str(source))
                        return True
                    else:
                        shutil.rmtree(str(destination), ignore_errors=True)
                        raise Exception("rsync copy verification failed")
                else:
                    raise Exception(f"rsync failed: {result.stderr}")

            except Exception as e:
                console.print(f"[dim]rsync approach failed: {e}[/dim]")
                console.print("[dim]Trying manual copy approach...[/dim]")

            # Method 4: Manual copy with extended attribute handling
            try:
                import subprocess

                # Use ditto which preserves extended attributes and permissions
                result = subprocess.run(
                    ["ditto", str(source), str(destination)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode == 0:
                    # Verify the copy
                    if self._verify_app_copy(source, destination):
                        # Remove the original
                        shutil.rmtree(str(source))
                        return True
                    else:
                        shutil.rmtree(str(destination), ignore_errors=True)
                        raise Exception("ditto copy verification failed")
                else:
                    raise Exception(f"ditto failed: {result.stderr}")

            except Exception as e:
                console.print(f"[dim]ditto approach failed: {e}[/dim]")
                raise Exception("All move methods failed")

        except Exception as e:
            console.print(f"[red]All move methods failed for {source.name}: {e}[/red]")
            return False

    def _verify_app_copy(self, source: Path, destination: Path) -> bool:
        """Verify that an app copy was successful by checking key files."""
        try:
            # Check if destination exists
            if not destination.exists():
                return False

            # Check for essential app bundle files
            info_plist_source = source / "Contents" / "Info.plist"
            info_plist_dest = destination / "Contents" / "Info.plist"

            if not (info_plist_source.exists() and info_plist_dest.exists()):
                return False

            # Quick size comparison (should be roughly the same)
            source_size = sum(
                f.stat().st_size for f in source.rglob("*") if f.is_file()
            )
            dest_size = sum(
                f.stat().st_size for f in destination.rglob("*") if f.is_file()
            )

            # Allow for small differences due to metadata
            size_diff = abs(source_size - dest_size)
            if size_diff > source_size * 0.01:  # More than 1% difference
                console.print(
                    f"[yellow]⚠[/yellow] Size difference detected: {size_diff} bytes"
                )
                return False

            return True

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Copy verification failed: {e}")
            return False

    def _is_symlink_or_alias(self, app_path: Path) -> bool:
        """Check if an app is a symlink or alias pointing to external drive."""
        try:
            # Check if it's a symlink
            if app_path.is_symlink():
                return True

            # Check if it's an alias by looking at the file size
            # Real app bundles should be much larger than a few bytes
            if app_path.stat().st_size < 1000:  # Less than 1KB is suspicious
                return True

            # Check if Contents directory exists and has reasonable size
            contents_dir = app_path / "Contents"
            if not contents_dir.exists():
                return True

            # Check if the app bundle has the expected structure
            info_plist = contents_dir / "Info.plist"
            if not info_plist.exists() or info_plist.stat().st_size < 100:
                return True

            return False
        except Exception:
            return True  # If we can't check, assume it's problematic

    def _get_real_app_size(self, app_path: Path) -> float:
        """Get the real size of an app bundle, handling symlinks and aliases."""
        try:
            if self._is_symlink_or_alias(app_path):
                return 0.0  # Symlinks/aliases don't count as real size

            # Calculate actual directory size
            total_size = 0
            for root, dirs, files in os.walk(app_path):
                for file in files:
                    try:
                        file_path = Path(root) / file
                        if file_path.exists() and not file_path.is_symlink():
                            total_size += file_path.stat().st_size
                    except Exception:
                        continue

            return total_size / (1024**3)  # Convert to GB
        except Exception:
            return 0.0

    def _wait_for_app_unlock(self, app_path: Path, max_wait: int = 30) -> bool:
        """Wait for an app to become unlocked, with progress indication."""
        console.print(f"[dim]Checking if {app_path.stem} is in use...[/dim]")

        for attempt in range(max_wait):
            if not self._check_app_in_use(app_path):
                if attempt > 0:
                    console.print(f"[green]✓[/green] {app_path.stem} is now available")
                return True

            if attempt == 0:
                console.print(f"[yellow]⚠[/yellow] {app_path.stem} is currently in use")
                console.print(
                    "[dim]This is common after copying files - macOS may be indexing or scanning them[/dim]"
                )
                console.print("[dim]Waiting for the app to become available...[/dim]")

            # Show progress dots
            dots = "." * ((attempt % 3) + 1)
            console.print(
                f"[dim]Waiting{dots} ({attempt + 1}/{max_wait})[/dim]", end="\r"
            )

            import time

            time.sleep(1)

        console.print(
            f"\n[yellow]⚠[/yellow] {app_path.stem} is still in use after {max_wait} seconds"
        )
        return False

    def fix_permissions_for_apps(self, apps: List[Path]) -> bool:
        """Fix permissions and attributes for a list of apps."""
        if not apps:
            console.print("[yellow]No applications to fix permissions for[/yellow]")
            return True

        console.print(
            f"\n[bold]Fixing permissions for {len(apps)} applications...[/bold]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            for app_path in apps:
                task = progress.add_task(f"Fixing {app_path.stem}...", total=100)

                try:
                    # Wait for app to be unlocked if it's in use
                    progress.update(task, completed=10)
                    if not self._wait_for_app_unlock(app_path):
                        console.print(
                            f"[yellow]⚠[/yellow] Skipping {app_path.stem} - still in use"
                        )
                        progress.update(task, completed=100)
                        continue

                    # Set correct permissions
                    progress.update(task, completed=25)
                    try:
                        os.chmod(
                            app_path,
                            stat.S_IRWXU
                            | stat.S_IRGRP
                            | stat.S_IXGRP
                            | stat.S_IROTH
                            | stat.S_IXOTH,
                        )
                    except Exception as e:
                        console.print(
                            f"[yellow]⚠[/yellow] Could not set permissions for {app_path.stem}: {e}"
                        )

                    # Remove extended attributes
                    progress.update(task, completed=50)
                    self._remove_extended_attributes(app_path)

                    # Fix permissions recursively
                    progress.update(task, completed=75)
                    self._fix_permissions_recursively(app_path)

                    progress.update(task, completed=100)
                    console.print(
                        f"[green]✓[/green] Fixed permissions for {app_path.stem}"
                    )

                except Exception as e:
                    console.print(
                        f"[yellow]⚠[/yellow] Could not fix permissions for {app_path.stem}: {e}"
                    )
                    progress.update(task, completed=100)

        return True

    def diagnose_and_fix_incomplete_copies(self, apps: List[Path]) -> List[Path]:
        """Diagnose apps that appear to be incomplete copies and provide fix instructions."""
        problematic_apps = []
        fix_instructions = []

        for app_path in apps:
            if self._is_symlink_or_alias(app_path):
                problematic_apps.append(app_path)
                fix_instructions.append(f"rm -rf '{app_path}'")
                continue

            # Check if the app has reasonable size
            real_size = self._get_real_app_size(app_path)
            if real_size < 0.1:  # Less than 100MB is suspicious for most apps
                problematic_apps.append(app_path)
                fix_instructions.append(f"rm -rf '{app_path}'")
                continue

        if problematic_apps:
            console.print(
                f"\n[yellow]⚠[/yellow] Found {len(problematic_apps)} apps that appear to be incomplete copies:"
            )
            for app in problematic_apps:
                console.print(f"  - {app.name}")

            console.print(
                f"\n[bold]These apps need to be removed and re-copied properly.[/bold]"
            )
            console.print(
                f"[dim]Run these commands to clean up the incomplete copies:[/dim]"
            )
            for instruction in fix_instructions:
                console.print(f"[dim]  {instruction}[/dim]")

            console.print(f"\n[bold]Then re-copy the apps using rsync:[/bold]")
            console.print(
                f"[dim]rsync -av --progress '/Volumes/rPi_1T/hide-from-script-AppBackup_20250918_125950/' '/Applications/'[/dim]"
            )

            if Confirm.ask("Do you want to remove the incomplete copies now?"):
                for app in problematic_apps:
                    try:
                        import shutil

                        shutil.rmtree(app)
                        console.print(f"[green]✓[/green] Removed {app.name}")
                    except Exception as e:
                        console.print(f"[red]✗[/red] Failed to remove {app.name}: {e}")

                console.print(
                    f"\n[yellow]Now re-copy the apps using rsync and run the script again.[/yellow]"
                )
                return []

        return apps

    def restore_apps_from_backup(self, backup_folder: Path) -> bool:
        """Restore applications from backup folder to /Applications."""
        if not backup_folder.exists():
            console.print(
                f"[yellow]⚠[/yellow] Backup folder not found: {backup_folder}"
            )
            console.print(
                "[bold]Smart restore mode: Looking for recently copied applications...[/bold]"
            )

            # Find recently modified apps (within last 24 hours)
            recent_apps = self.find_recently_modified_apps(hours=24)

            if not recent_apps:
                console.print(
                    "[yellow]No recently modified applications found in /Applications[/yellow]"
                )
                console.print(
                    "[dim]If you manually copied apps, they may be older than 24 hours[/dim]"
                )
                return False

            # Filter to only valid app bundles
            valid_recent_apps = []
            for app in recent_apps:
                if self._check_app_integrity(app):
                    valid_recent_apps.append(app)
                else:
                    console.print(
                        f"[yellow]⚠[/yellow] {app.name}: App bundle is corrupted or incomplete"
                    )

            if not valid_recent_apps:
                console.print(
                    "[red]No valid recently modified applications found[/red]"
                )
                return False

            console.print(
                f"\n[bold]Found {len(valid_recent_apps)} recently modified applications:[/bold]"
            )

            # Display what will be processed
            self.display_apps_table(
                [AppInfo(app) for app in valid_recent_apps],
                "Recently Modified Applications",
            )

            if not Confirm.ask(
                "Do you want to fix permissions for these applications?"
            ):
                console.print("Permission fix cancelled.")
                return False

            # Fix permissions for the recently modified apps
            return self.fix_permissions_for_apps(valid_recent_apps)

        apps_to_restore = [
            f for f in backup_folder.iterdir() if f.is_dir() and f.suffix == ".app"
        ]

        if not apps_to_restore:
            console.print("[red]No applications found in backup folder[/red]")
            return False

        # Check app integrity before attempting restore
        valid_apps = []
        for app in apps_to_restore:
            if self._check_app_integrity(app):
                valid_apps.append(app)
            else:
                console.print(
                    f"[red]✗[/red] {app.name}: App bundle is corrupted or incomplete"
                )

        if not valid_apps:
            console.print("[red]No valid applications found to restore[/red]")
            return False

        console.print(
            f"\n[bold]Found {len(valid_apps)} valid applications to restore[/bold]"
        )
        if len(valid_apps) < len(apps_to_restore):
            console.print(
                f"[yellow]⚠[/yellow] {len(apps_to_restore) - len(valid_apps)} applications were skipped due to corruption"
            )

        # Display what will be restored
        self.display_apps_table(
            [AppInfo(app) for app in valid_apps], "Applications to Restore"
        )

        if not Confirm.ask("Do you want to restore these applications?"):
            console.print("Restore cancelled.")
            return False

        # Pre-process apps to handle confirmations outside of progress bar
        apps_to_process = []
        for app_path in valid_apps:
            destination = self.applications_dir / app_path.name

            # Check if source exists
            if not app_path.exists():
                console.print(
                    f"[yellow]⚠[/yellow] {app_path.stem} not found in backup, skipping..."
                )
                continue

            # Check if destination already exists
            if destination.exists():
                console.print(
                    f"[yellow]⚠[/yellow] {app_path.stem} already exists in /Applications"
                )

                # Check if apps are identical
                if self._apps_are_identical(app_path, destination):
                    console.print(
                        f"[green]✓[/green] {app_path.stem} is already identical - skipping restore"
                    )
                    continue

                # Ask for confirmation to overwrite
                if not Confirm.ask(f"Overwrite existing {app_path.stem}?"):
                    console.print(f"[dim]Skipping {app_path.stem}[/dim]")
                    continue

            apps_to_process.append(app_path)

        if not apps_to_process:
            console.print(
                "[yellow]No applications to restore after processing[/yellow]"
            )
            return True

        console.print(
            f"\n[bold]Restoring {len(apps_to_process)} applications...[/bold]"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:

            for app_path in apps_to_process:
                task = progress.add_task(f"Restoring {app_path.stem}...", total=100)

                try:
                    destination = self.applications_dir / app_path.name

                    # Remove existing app if it exists (we already confirmed above)
                    if destination.exists():
                        console.print(
                            f"[dim]Removing existing {app_path.stem}...[/dim]"
                        )
                        progress.update(task, completed=25)
                        if not self._remove_app_safely(destination):
                            console.print(f"[dim]Skipping {app_path.stem}[/dim]")
                            progress.update(task, completed=100)
                            continue
                        console.print(
                            f"[green]✓[/green] Removed existing {app_path.stem}"
                        )

                    # Try to move the application back
                    progress.update(task, completed=50)
                    move_success = False
                    try:
                        shutil.move(str(app_path), str(destination))
                        move_success = True
                    except Exception as e:
                        console.print(
                            f"[red]✗[/red] Failed to move {app_path.stem}: {e}"
                        )
                        console.print(
                            f"[yellow]⚠[/yellow] Please manually copy {app_path.stem} to /Applications"
                        )
                        console.print(
                            f"[dim]You can drag and drop the app from the external drive to /Applications[/dim]"
                        )

                        # Wait for user to manually copy
                        if not Confirm.ask(
                            f"Have you manually copied {app_path.stem} to /Applications?"
                        ):
                            console.print(f"[dim]Skipping {app_path.stem}[/dim]")
                            progress.update(task, completed=100)
                            continue

                        # Verify the manual copy worked
                        if not destination.exists():
                            console.print(
                                f"[red]✗[/red] {app_path.stem} not found in /Applications after manual copy"
                            )
                            progress.update(task, completed=100)
                            continue

                        move_success = True

                    # Set correct permissions
                    progress.update(task, completed=75)
                    try:
                        os.chmod(
                            destination,
                            stat.S_IRWXU
                            | stat.S_IRGRP
                            | stat.S_IXGRP
                            | stat.S_IROTH
                            | stat.S_IXOTH,
                        )
                    except Exception as e:
                        console.print(
                            f"[yellow]⚠[/yellow] Could not set permissions for {app_path.stem}: {e}"
                        )

                    progress.update(task, completed=100)
                    console.print(f"[green]✓[/green] Restored {app_path.stem}")

                    # Only offer to remove backup copy if the app is actually in /Applications
                    if destination.exists():
                        # Ask if user wants to remove the backup copy
                        if Confirm.ask(
                            f"Remove backup copy of {app_path.stem} from external drive?"
                        ):
                            try:
                                shutil.rmtree(app_path)
                                console.print(
                                    f"[dim]Removed backup copy of {app_path.stem}[/dim]"
                                )
                            except Exception as e:
                                console.print(
                                    f"[yellow]⚠[/yellow] Could not remove backup copy: {e}"
                                )
                    else:
                        console.print(
                            f"[yellow]⚠[/yellow] {app_path.stem} not found in /Applications - keeping backup copy"
                        )

                except FileNotFoundError as e:
                    console.print(
                        f"[yellow]⚠[/yellow] {app_path.stem}: Some files missing ({e}), but continuing..."
                    )
                    progress.update(task, completed=100)
                    continue
                except PermissionError as e:
                    console.print(
                        f"[red]✗[/red] Failed to restore {app_path.stem}: Permission denied"
                    )
                    console.print(
                        f"[dim]Try running with sudo or check file permissions[/dim]"
                    )
                    return False
                except Exception as e:
                    console.print(
                        f"[red]✗[/red] Failed to restore {app_path.stem}: {e}"
                    )
                    console.print(
                        f"[dim]Continuing with remaining applications...[/dim]"
                    )
                    progress.update(task, completed=100)
                    continue

        # Check if any apps were successfully restored
        restored_count = 0
        for app_path in apps_to_process:
            destination = self.applications_dir / app_path.name
            if destination.exists():
                restored_count += 1

        if restored_count == 0:
            console.print("[red]No applications were successfully restored[/red]")
            return False
        elif restored_count < len(apps_to_process):
            console.print(
                f"[yellow]Successfully restored {restored_count}/{len(apps_to_process)} applications[/yellow]"
            )
        else:
            console.print(
                f"[green]✓[/green] Successfully restored all {restored_count} applications"
            )

        return True

    def restore_all_backups_from_volume(self, volume: Path) -> bool:
        """Restore all backup folders from a volume."""
        backup_folders = self.find_backup_folders(volume)

        if not backup_folders:
            console.print(f"[red]No backup folders found on {volume.name}[/red]")
            return False

        console.print(
            f"\n[bold]Found {len(backup_folders)} backup folders to restore:[/bold]"
        )
        for folder in backup_folders:
            app_count = len(
                [f for f in folder.iterdir() if f.is_dir() and f.suffix == ".app"]
            )
            console.print(f"  • {folder.name} ({app_count} apps)")

        if not Confirm.ask(f"Restore all {len(backup_folders)} backup folders?"):
            console.print("Restore cancelled.")
            return False

        success_count = 0
        for backup_folder in backup_folders:
            console.print(f"\n[bold]Restoring from {backup_folder.name}...[/bold]")
            if self.restore_apps_from_backup(backup_folder):
                success_count += 1
            else:
                console.print(
                    f"[yellow]Failed to restore from {backup_folder.name}[/yellow]"
                )

        console.print(
            f"\n[bold green]✓ Successfully restored {success_count}/{len(backup_folders)} backup folders[/bold green]"
        )
        return success_count > 0


def main():
    """Main function."""
    # Check for root privileges first
    check_root_privileges()

    parser = argparse.ArgumentParser(
        description="Free up space on macOS by moving large applications to removable drives",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sudo python free-up-space-macos.py                    # Interactive mode - specify target free space
  sudo python free-up-space-macos.py --restore /Volumes/MyDrive/AppBackup_20231201_143022  # Restore specific backup
  sudo python free-up-space-macos.py --restore          # Interactive restore - select volume and backup folder
  sudo python free-up-space-macos.py --fix-permissions  # Fix permissions for recently copied apps (smart restore)

The script will calculate how much space to free up based on your target free space goal.
Perfect for OS upgrades that require specific amounts of free space.

Smart Restore Mode:
  If you manually copy apps to /Applications and then delete the backup folder,
  use --fix-permissions to automatically detect and fix permissions for recently copied apps.
        """,
    )

    parser.add_argument(
        "--restore",
        type=str,
        nargs="?",
        const="",
        help="Restore applications from backup folder (no argument for interactive selection)",
    )

    parser.add_argument(
        "--fix-permissions",
        action="store_true",
        help="Fix permissions for recently modified applications in /Applications (smart restore mode)",
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
    if args.restore is not None:
        if args.restore and args.restore.strip():
            # Specific backup folder provided
            backup_path = Path(args.restore)
            console.print(f"[bold]Restore mode: {backup_path}[/bold]")

            if manager.restore_apps_from_backup(backup_path):
                console.print(
                    "\n[bold green]✓ Restore completed successfully![/bold green]"
                )
            else:
                console.print("\n[bold red]✗ Restore failed![/bold red]")
                sys.exit(1)
        else:
            # No backup folder provided - interactive restore
            console.print("[bold]Interactive restore mode[/bold]")
            console.print("Select a volume to restore from:")

            volume_selection = manager.select_volume()
            if not volume_selection:
                console.print("No volume selected. Restore cancelled.")
                return

            volume, _ = volume_selection  # Ignore existing_folder for restore mode

            # Select backup folder
            backup_selection = manager.select_backup_folder(volume)
            if not backup_selection:
                console.print("No backup folder selected.")
                console.print(
                    "[bold]Smart restore mode: Looking for recently copied applications...[/bold]"
                )
                console.print(
                    "[dim]Note: If apps appear 'in use', this is normal after copying - macOS may be indexing or scanning them[/dim]"
                )

                # Find recently modified apps (within last 2 hours)
                recent_apps = manager.find_recently_modified_apps(hours=2)

                if not recent_apps:
                    console.print(
                        "[yellow]No recently modified applications found in /Applications (last 2 hours)[/yellow]"
                    )
                    console.print(
                        "[dim]If you manually copied apps, they may be older than 2 hours[/dim]"
                    )
                    return

                # Filter to only valid app bundles
                valid_recent_apps = []
                for app in recent_apps:
                    if manager._check_app_integrity(app):
                        valid_recent_apps.append(app)
                    else:
                        console.print(
                            f"[yellow]⚠[/yellow] {app.name}: App bundle is corrupted or incomplete"
                        )

                if not valid_recent_apps:
                    console.print(
                        "[red]No valid recently modified applications found[/red]"
                    )
                    return

                # Diagnose and fix incomplete copies
                valid_recent_apps = manager.diagnose_and_fix_incomplete_copies(
                    valid_recent_apps
                )

                if not valid_recent_apps:
                    console.print(
                        "[yellow]No valid applications to process after cleanup[/yellow]"
                    )
                    return

                console.print(
                    f"\n[bold]Found {len(valid_recent_apps)} recently modified applications:[/bold]"
                )

                # Display what will be processed
                manager.display_apps_table(
                    [AppInfo(app) for app in valid_recent_apps],
                    "Recently Modified Applications (last 2 hours)",
                )

                if not Confirm.ask(
                    "Do you want to fix permissions for these applications?"
                ):
                    console.print("Permission fix cancelled.")
                    return

                # Fix permissions for the recently modified apps
                if manager.fix_permissions_for_apps(valid_recent_apps):
                    console.print(
                        "\n[bold green]✓ Permission fix completed successfully![/bold green]"
                    )
                else:
                    console.print("\n[bold red]✗ Permission fix failed![/bold red]")
                    sys.exit(1)
                return

            if backup_selection == "ALL":
                # Restore all backup folders
                if manager.restore_all_backups_from_volume(volume):
                    console.print(
                        "\n[bold green]✓ All restores completed successfully![/bold green]"
                    )
                else:
                    console.print("\n[bold red]✗ Some restores failed![/bold red]")
                    sys.exit(1)
            else:
                # Restore single backup folder
                if manager.restore_apps_from_backup(backup_selection):
                    console.print(
                        "\n[bold green]✓ Restore completed successfully![/bold green]"
                    )
                else:
                    console.print("\n[bold red]✗ Restore failed![/bold red]")
                    sys.exit(1)
        return

    # Handle fix-permissions mode
    if args.fix_permissions:
        console.print(
            "[bold]Smart restore mode: Fixing permissions for recently copied applications[/bold]"
        )
        console.print(
            "[dim]Note: If apps appear 'in use', this is normal after copying - macOS may be indexing or scanning them[/dim]"
        )

        # Find recently modified apps (within last 24 hours)
        recent_apps = manager.find_recently_modified_apps(hours=24)

        if not recent_apps:
            console.print(
                "[yellow]No recently modified applications found in /Applications[/yellow]"
            )
            console.print(
                "[dim]If you manually copied apps, they may be older than 24 hours[/dim]"
            )
            return

        # Filter to only valid app bundles
        valid_recent_apps = []
        for app in recent_apps:
            if manager._check_app_integrity(app):
                valid_recent_apps.append(app)
            else:
                console.print(
                    f"[yellow]⚠[/yellow] {app.name}: App bundle is corrupted or incomplete"
                )

        if not valid_recent_apps:
            console.print("[red]No valid recently modified applications found[/red]")
            return

        console.print(
            f"\n[bold]Found {len(valid_recent_apps)} recently modified applications:[/bold]"
        )

        # Display what will be processed
        manager.display_apps_table(
            [AppInfo(app) for app in valid_recent_apps],
            "Recently Modified Applications",
        )

        if not Confirm.ask("Do you want to fix permissions for these applications?"):
            console.print("Permission fix cancelled.")
            return

        # Fix permissions for the recently modified apps
        if manager.fix_permissions_for_apps(valid_recent_apps):
            console.print(
                "\n[bold green]✓ Permission fix completed successfully![/bold green]"
            )
        else:
            console.print("\n[bold red]✗ Permission fix failed![/bold red]")
            sys.exit(1)
        return

    # Interactive mode
    try:
        # Get current free space and show it
        current_free = manager.get_current_free_space()
        console.print(f"\n[bold]Current free space: {current_free:.2f} GB[/bold]")

        # Get target free space
        target_free_gb = float(
            Prompt.ask("How many GB of free space do you want total?", default="20.0")
        )

        # Calculate space needed
        space_to_free = manager.calculate_space_to_free(target_free_gb)

        if space_to_free <= 0:
            console.print(
                f"\n[green]✓ You already have {current_free:.2f} GB free space![/green]"
            )
            console.print(
                f"[green]Target: {target_free_gb} GB - No action needed.[/green]"
            )
            return

        console.print(
            f"\n[bold]Need to free up {space_to_free:.2f} GB to reach {target_free_gb} GB total free space[/bold]"
        )
        console.print("[bold]Scanning applications...[/bold]")

        # Get all applications
        apps = manager.get_applications()

        if not apps:
            console.print("[red]No applications found in /Applications[/red]")
            return

        # Display protected apps information
        manager.display_protected_apps_info()

        # Select apps to move
        selected_apps, space_to_free, current_free = (
            manager.select_apps_for_target_free_space(apps, target_free_gb)
        )

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
        console.print(
            f"[dim]This will free up {total_size:.2f} GB, giving you {current_free + total_size:.2f} GB total free space[/dim]"
        )
        manager.display_apps_table(selected_apps, "Applications to Move")

        # Confirm selection
        if not Confirm.ask(
            f"\nMove these applications to reach {target_free_gb} GB free space?"
        ):
            console.print("Operation cancelled.")
            return

        # Select volume
        volume_selection = manager.select_volume()
        if not volume_selection:
            console.print("No volume selected. Operation cancelled.")
            return

        volume, existing_folder = volume_selection

        # Create backup folder
        backup_folder = manager.create_backup_folder(volume, existing_folder)
        if existing_folder:
            console.print(
                f"[green]Using existing backup folder: {backup_folder}[/green]"
            )
        else:
            console.print(f"[green]Created backup folder: {backup_folder}[/green]")

        # Move applications
        success, failed_apps = manager.move_apps_to_volume(selected_apps, backup_folder)

        if success:
            new_free_space = manager.get_current_free_space()
            console.print(
                f"\n[bold green]✓ Successfully moved {len(selected_apps)} applications![/bold green]"
            )
            console.print(
                f"[bold green]New free space: {new_free_space:.2f} GB[/bold green]"
            )
            console.print(f"[bold]Backup location: {backup_folder}[/bold]")
            console.print(
                f"\n[bold yellow]📋 RESTORE COMMAND (save this for later):[/bold yellow]"
            )
            console.print(
                f"[bold cyan]sudo python {sys.argv[0]} --restore {backup_folder}[/bold cyan]"
            )
            console.print(
                f"[dim]Copy and save this command to restore your applications later[/dim]"
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
                f"\n[bold yellow]📋 RESTORE COMMAND (save this for later):[/bold yellow]"
            )
            console.print(
                f"[bold cyan]sudo python {sys.argv[0]} --restore {backup_folder}[/bold cyan]"
            )
            console.print(
                f"[dim]Copy and save this command to restore your applications later[/dim]"
            )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
