# Free Up Space macOS

A Python command-line tool with a beautiful colored interface that helps you free up space on your Mac by moving large applications to removable drives. The tool intelligently selects the largest applications to meet your space requirements and provides easy restoration functionality.

## Features

🎨 **Beautiful Interface**

- Rich colored terminal output with progress bars and animations
- Formatted tables showing application sizes and details
- Interactive prompts with clear visual feedback

📊 **Smart Application Management**

- Scans `/Applications` directory for all `.app` bundles
- Calculates actual disk usage for each application
- Selects largest applications to meet your target space requirements
- Shows detailed information before making changes

💾 **Flexible Storage Options**

- Lists available removable drives in `/Volumes`
- Creates organized, timestamped backup folders
- Supports any removable drive (USB, external SSD, etc.)

🔄 **Safe Operations**

- Multiple confirmation prompts before destructive operations
- Comprehensive error handling with colored error messages
- Easy restore functionality with proper permission management
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

### Interactive Mode (Default)

Run the script without arguments to start the interactive mode:

```bash
sudo python free-up-space-macos.py
```

The script will:

1. Ask how many gigabytes you want to free up
2. Scan your `/Applications` directory
3. Show you the largest applications that will be moved
4. Ask for confirmation
5. Let you select a removable drive
6. Move the applications to a timestamped backup folder

### Restore Mode

To restore applications from a backup folder:

```bash
sudo python free-up-space-macos.py --restore /Volumes/MyDrive/AppBackup_20231201_143022
```

The script will:

1. Scan the backup folder for applications
2. Show you what will be restored
3. Ask for confirmation
4. Move applications back to `/Applications`
5. Set proper permissions

## Example Workflow

### Freeing Up Space

```bash
$ sudo python free-up-space-macos.py

┌─────────────────────────────────────────────────────────────┐
│                    Free Up Space macOS                     │
│        Move large applications to removable drives         │
│                   to free up space                         │
└─────────────────────────────────────────────────────────────┘

How many gigabytes do you want to free up? [5.0]: 10

Scanning applications to free up 10.0 GB...

Selected 3 applications (Total: 12.45 GB)
┌─────────────────────────────────────────────────────────────┐
│                    Applications to Move                     │
├─────────────────────────────────────────────────────────────┤
│ Name                    │ Size (GB) │ Path                  │
├─────────────────────────────────────────────────────────────┤
│ Adobe Photoshop 2024    │     4.23  │ /Applications/Adobe   │
│ Final Cut Pro           │     3.87  │ /Applications/Final   │
│ Xcode                   │     4.35  │ /Applications/Xcode   │
└─────────────────────────────────────────────────────────────┘

Move these applications to free up 12.45 GB? [y/N]: y

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
Backup location: /Volumes/MyExternalDrive/AppBackup_20231201_143022
To restore later, use: sudo python free-up-space-macos.py --restore /Volumes/MyExternalDrive/AppBackup_20231201_143022
```

### Restoring Applications

```bash
$ sudo python free-up-space-macos.py --restore /Volumes/MyExternalDrive/AppBackup_20231201_143022

┌─────────────────────────────────────────────────────────────┐
│                    Free Up Space macOS                     │
│        Move large applications to removable drives         │
│                   to free up space                         │
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

## Command Line Options

- `--restore <path>`: Restore applications from a backup folder
- `--help`: Show help message and usage examples

## How It Works

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
└── README.md                # This file
```

## Dependencies

- `rich>=13.0.0`: For beautiful terminal output and progress bars

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

## Disclaimer

This tool moves applications between drives. While it includes safety features, always ensure you have backups of important data before using this tool. The authors are not responsible for any data loss.
