# Free Up Space macOS

A Python command-line tool with a beautiful colored interface that helps you free up space on your Mac by safely deleting large applications that are backed up in Time Machine. The tool intelligently calculates how much space to free up based on your target free space goal and makes restoration simple through Time Machine.

> **⚠️ DEVELOPMENT NOTE**: The Time Machine integration features described below were implemented without testing (October 2025). They will be tested when the next macOS upgrade requires freeing up disk space. Use with caution and verify Time Machine backups exist before deleting any applications.

## Features

🎨 **Beautiful Interface**

- Rich colored terminal output with progress bars and animations
- Formatted tables showing application sizes and details
- Interactive prompts with clear visual feedback

⏰ **Time Machine Integration (NEW!)**

- **Primary strategy**: Automatically detects Time Machine backups
- Verifies apps exist in backups before deletion
- Simply deletes apps (no copying, no corruption risk)
- Restores from Time Machine with perfect permissions
- Falls back to external drive method if Time Machine unavailable

📊 **Smart Application Management**

- Scans `/Applications` directory for all `.app` bundles
- Calculates actual disk usage for each application
- **Target-based space calculation**: Specify how much total free space you want
- Perfect for OS upgrades that require specific amounts of free space
- Shows detailed information before making changes

💾 **Flexible Storage Options**

- **Primary**: Uses Time Machine backups (safer, no corruption)
- **Fallback**: Lists available removable drives in `/Volumes`
- Creates organized, timestamped backup folders
- Supports any removable drive (USB, external SSD, etc.)

🔄 **Safe Operations**

- Time Machine verification before deletion
- Multiple confirmation prompts before destructive operations
- Comprehensive error handling with colored error messages
- Easy restore through Time Machine GUI (no permission issues!)
- Progress tracking for all operations

## Requirements

- Python 3.12 or higher
- macOS (tested on macOS 10.15+)
- **Root privileges (must run with `sudo`)**

## Installation

1. Clone or download this repository:

   ```bash
   git clone <repository-url>
   cd free-up-space-macos
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Perfect for OS Upgrades

This tool is especially useful for macOS upgrades that require specific amounts of free space:

- **macOS Sonoma**: Requires ~20GB free space
- **macOS Sequoia**: Requires ~25GB free space
- **Any macOS upgrade**: Just enter the required amount

The script will calculate exactly how much space to free up to reach your target.

### Interactive Mode (Default) - Time Machine First!

Run the script without arguments to start the interactive mode:

```bash
sudo python free-up-space-macos.py
```

The script will:

1. **Check for Time Machine backups** (automatic)
2. Show your current free space
3. Ask how many GB of total free space you want (perfect for OS upgrades)
4. Calculate exactly how much space needs to be freed up
5. Scan your `/Applications` directory for the largest apps
6. Show you which applications will be moved
7. **If Time Machine available**:
   - Guide you to verify apps exist in Time Machine backup
   - Ask which apps are verified in TM
   - Simply delete verified apps (no copying!)
   - Show restoration instructions
8. **If Time Machine not available** (or you choose `--use-external-drive`):
   - Let you select a removable drive
   - Move the applications to a timestamped backup folder

### Restore Mode

#### Restore Specific Backup Folder

To restore applications from a specific backup folder:

```bash
sudo python free-up-space-macos.py --restore /Volumes/MyDrive/AppBackup_20231201_143022
```

#### Interactive Restore (New!)

To interactively select a volume and backup folder:

```bash
sudo python free-up-space-macos.py --restore ""
```

The interactive restore will:

1. Show available volumes in `/Volumes`
2. Let you select a volume
3. Find all `AppBackup_*` folders on that volume
4. Show backup folders with app counts
5. Let you select a specific backup or restore all backups
6. Restore applications back to `/Applications`

The script will:

1. Scan the backup folder(s) for applications
2. Show you what will be restored
3. Ask for confirmation
4. Move applications back to `/Applications`
5. Set proper permissions

## Example Workflow

### Freeing Up Space

```bash
$ sudo python free-up-space-macos.py

┌──────────────────────────────────────────────────────────────┐
│                    Free Up Space macOS                       │
│        Move large applications to removable drives           │
│                   to free up space                           │
└──────────────────────────────────────────────────────────────┘

Current free space: 8.5 GB

How many GB of free space do you want total? [20.0]: 25

Need to free up 16.5 GB to reach 25.0 GB total free space
Scanning applications...

Selected 3 applications (Total: 17.2 GB)
This will free up 17.2 GB, giving you 25.7 GB total free space
┌─────────────────────────────────────────────────────────────┐
│                    Applications to Move                     │
├─────────────────────────────────────────────────────────────┤
│ Name                    │ Size (GB) │ Path                  │
├─────────────────────────────────────────────────────────────┤
│ Adobe Photoshop 2024    │     4.23  │ /Applications/Adobe   │
│ Final Cut Pro           │     3.87  │ /Applications/Final   │
│ Xcode                   │     9.10  │ /Applications/Xcode   │
└─────────────────────────────────────────────────────────────┘

Move these applications to reach 25.0 GB free space? [y/N]: y

Available volumes:
1. MyExternalDrive (/Volumes/MyExternalDrive)
2. USB_Stick (/Volumes/USB_Stick)

Select volume (number) [1]: 1
Created backup folder: /Volumes/MyExternalDrive/AppBackup_20231201_143022

Moving applications to: /Volumes/MyExternalDrive/AppBackup_20231201_143022
✓ Moved Adobe Photoshop 2024
✓ Moved Final Cut Pro
✓ Moved Xcode

✓ Successfully moved 3 applications!
New free space: 25.7 GB
Backup location: /Volumes/MyExternalDrive/AppBackup_20231201_143022
To restore later, use: sudo python free-up-space-macos.py --restore /Volumes/MyExternalDrive/AppBackup_20231201_143022
```

### Restoring Applications

#### Specific Backup Folder

```bash
$ sudo python free-up-space-macos.py --restore /Volumes/MyExternalDrive/AppBackup_20231201_143022

┌─────────────────────────────────────────────────────────────┐
│                    Free Up Space macOS                      │
│        Move large applications to removable drives          │
│                   to free up space                          │
└─────────────────────────────────────────────────────────────┘

Restore mode: /Volumes/MyExternalDrive/AppBackup_20231201_143022

Found 3 applications to restore
┌─────────────────────────────────────────────────────────────┐
│                Applications to Restore                      │
├─────────────────────────────────────────────────────────────┤
│ Name                    │ Size (GB) │ Path                  │
├─────────────────────────────────────────────────────────────┤
│ Adobe Photoshop 2024    │     4.23  │ /Volumes/MyExternal   │
│ Final Cut Pro           │     3.87  │ /Volumes/MyExternal   │
│ Xcode                   │     4.35  │ /Volumes/MyExternal   │
└─────────────────────────────────────────────────────────────┘

Do you want to restore these applications? [y/N]: y

✓ Restored Adobe Photoshop 2024
✓ Restored Final Cut Pro
✓ Restored Xcode

✓ Restore completed successfully!
```

#### Interactive Restore

```bash
$ sudo python free-up-space-macos.py --restore ""

┌─────────────────────────────────────────────────────────────┐
│                    Free Up Space macOS                      │
│        Move large applications to removable drives          │
│                   to free up space                          │
└─────────────────────────────────────────────────────────────┘

Interactive restore mode
Select a volume to restore from:

Available volumes:
1. MyExternalDrive (/Volumes/MyExternalDrive)
2. USB_Stick (/Volumes/USB_Stick)

Select volume (number) [1]: 1

Found 2 backup folders on MyExternalDrive:
1. AppBackup_20231201_143022 (3 apps)
2. AppBackup_20231201_120000 (2 apps)
3. Restore ALL backup folders

Select backup folder (number) [1]: 3

Found 2 backup folders to restore:
  • AppBackup_20231201_143022 (3 apps)
  • AppBackup_20231201_120000 (2 apps)

Restore all 2 backup folders? [y/N]: y

Restoring from AppBackup_20231201_143022...
✓ Restored Adobe Photoshop 2024
✓ Restored Final Cut Pro
✓ Restored Xcode

Restoring from AppBackup_20231201_120000...
✓ Restored Docker
✓ Restored Slack

✓ Successfully restored 2/2 backup folders
✓ All restores completed successfully!
```

## Command Line Options

### Time Machine Options (NEW!)
- `--restore-from-tm`: Interactive Time Machine restoration guide
- `--check-tm-status`: Check Time Machine availability and backup status
- `--use-external-drive`: Force external drive method (skip Time Machine check)

### External Drive Options
- `--restore <path>`: Restore applications from a specific backup folder
- `--restore ""`: Interactive restore mode - select volume and backup folder
- `--fix-permissions`: Fix permissions for recently modified applications (smart restore mode)
- `--fix-permissions-choose N`: Show top N largest apps and ask how many to fix permissions for (default: 15)

### General
- `--help`: Show help message and usage examples

### Smart Restore Mode (New!)

If you manually copy apps back to `/Applications` (e.g., by dragging and dropping in Finder), you may need to fix permissions:

```bash
sudo python free-up-space-macos.py --fix-permissions
```

This will:
1. Look for apps modified in the last 24 hours
2. If none found, show the top 15 largest apps with numbering
3. Ask how many apps to fix (default: 12)
4. Fix permissions automatically without additional confirmation

You can also specify how many largest apps to show:

```bash
sudo python free-up-space-macos.py --fix-permissions-choose 20
```

**Note:** The numbered list makes it easy to count which apps you want to fix without manually counting rows.

## How It Works

### Time Machine Method (Primary - Recommended)

1. **Time Machine Detection**: Checks if Time Machine is configured and has recent backups
2. **Application Discovery**: Scans `/Applications` for all `.app` bundles
3. **Size Calculation**: Recursively calculates actual disk usage for each application
4. **Smart Selection**: Sorts applications by size and selects the largest ones to meet your target
5. **Backup Verification**: Guides you to verify apps exist in Time Machine backup
6. **Safe Deletion**: Simply deletes verified apps (no copying, no corruption)
7. **Easy Restoration**: Restore anytime from Time Machine with perfect permissions

### External Drive Method (Fallback)

1. **Application Discovery**: Scans `/Applications` for all `.app` bundles
2. **Size Calculation**: Recursively calculates actual disk usage for each application
3. **Smart Selection**: Sorts applications by size and selects the largest ones to meet your target
4. **Safe Moving**: Uses `shutil.move()` to move applications to removable drives
5. **Permission Management**: Sets proper permissions when restoring applications
6. **Backup Organization**: Creates timestamped folders for easy identification

## Safety Features

- **Confirmation Prompts**: Multiple confirmation steps before any destructive operations
- **Error Handling**: Comprehensive error handling with clear error messages
- **Permission Checks**: Verifies access to directories before operations
- **Progress Tracking**: Visual progress bars for long operations
- **Backup Verification**: Checks backup folder contents before restoration

## Known Limitations & Workflow Notes

### Time Machine Method (Recommended)

✅ **The Time Machine method eliminates most previous issues:**

- **No copying** = No corruption risk
- **No permission issues** = Time Machine restores perfectly
- **Faster** = Just delete, don't copy
- **Simpler** = No manual steps needed

**Requirements:**
- Time Machine must be configured and have recent backups
- You must manually verify apps exist in backups (opens Time Machine GUI)
- Apps will be permanently deleted from `/Applications` (restorable from TM)

**⚠️ Testing Note**: This method was implemented in October 2025 without testing. It will be validated during the next macOS upgrade cycle.

### External Drive Method (Fallback)

⚠️ **Note**: Due to macOS system protections, moving applications programmatically can be unreliable.

**Current Workflow:**

1. Run the script to identify large apps to move
2. For stubborn apps that won't move programmatically:
   - Use Finder to drag and drop apps to your external drive
   - The script will show you which apps and where to move them
3. After manual copying, run `--fix-permissions` to fix permissions for the copied apps

**Why this happens:** macOS has various protection mechanisms (SIP, extended attributes, app quarantine) that can prevent programmatic moves even with `sudo`. Finder has special privileges that bypass some of these restrictions.

### Future Improvements

See the [TODO section](#todo) below for planned enhancements.

## Troubleshooting

### Permission Denied Errors

The script requires root privileges to access `/Applications` and `/Volumes` directories. Always run with `sudo`:

```bash
sudo python free-up-space-macos.py
```

If you see permission errors even with sudo, ensure your user account has administrative privileges.

### No Removable Drives Found

Ensure your external drive is properly mounted and visible in `/Volumes`. The script excludes system volumes like "Macintosh HD", "Preboot", and "Recovery".

### Application Not Found

If an application appears to be missing after restoration, check that:

1. The backup folder path is correct
2. The application files weren't corrupted during the move
3. You have proper permissions to write to `/Applications`

## File Structure

```
free-up-space-macos/
├── free-up-space-macos.py    # Main script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Dependencies

- `rich>=13.0.0`: For beautiful terminal output and progress bars

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## TODO / Future Improvements

### High Priority

- ✅ **Time Machine Integration** - COMPLETED (October 2025, pending testing)
  - Time Machine is now the primary strategy
  - Automatically detects and uses TM backups
  - Simply deletes apps verified in TM
  - Eliminates corruption and permission issues
  - Falls back to external drive if TM unavailable

- **Test Time Machine Integration** - When next macOS upgrade occurs
  - Validate TM detection works correctly
  - Verify app verification workflow is smooth
  - Ensure deletion and restoration work as expected
  - Fix any bugs discovered during real-world use

- **Fix/prevent missing icons for restored apps**
  - When applications are moved or restored on macOS, the system icon cache may not update properly
  - Potential solutions to investigate:
    - Force icon cache refresh using `touch` or similar commands
    - Use macOS's icon services commands (`iconutil`, Launch Services)
    - Set proper extended attributes (xattr) that macOS uses for icon display
    - Rebuild the Launch Services database (`lsregister`)

### Medium Priority

- **Detect Corrupted Copies** (External drive method only)
  - Compare file counts between source and destination
  - Verify critical files (executables, Info.plist, frameworks)
  - Hash comparison for key files
  - Warn user about potentially corrupted apps

- Improve automated move success rate for external drive method
- Add size verification after copies complete
- Better handling of apps with SIP/system protection
- Dry-run mode to preview actions without making changes

### Low Priority

- Support for moving other large directories (not just apps)
- Compression options for rarely-used apps
- Web UI for easier use

## Disclaimer

This tool moves applications between drives. While it includes safety features, always ensure you have backups of important data before using this tool. The authors are not responsible for any data loss.
