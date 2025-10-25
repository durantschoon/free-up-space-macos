#!/bin/bash

# Restore Chrome from Time Machine Backup
# This script removes the corrupted Chrome and helps you restore from Time Machine

echo "=== Restore Chrome from Time Machine ==="
echo ""
echo "This script will:"
echo "  1. Remove the corrupted Chrome from /Applications"
echo "  2. Help you restore Chrome from Time Machine backup"
echo ""

APP="/Applications/Google Chrome.app"

# Check if Chrome exists
if [ -e "$APP" ]; then
    echo "Current Chrome status:"
    ls -ld "$APP" 2>&1
    echo ""

    read -p "Do you want to remove the corrupted Chrome? (yes/no): " response
    if [ "$response" = "yes" ]; then
        echo ""
        echo "Removing corrupted Chrome..."

        # Try multiple methods to remove it
        echo "Step 1: Removing flags..."
        sudo chflags -R nouchg "$APP" 2>/dev/null
        sudo chflags -R noschg "$APP" 2>/dev/null

        echo "Step 2: Attempting to delete..."
        sudo rm -rf "$APP" 2>&1

        if [ ! -e "$APP" ]; then
            echo "  ✓ Chrome successfully removed!"
        else
            echo "  ✗ Failed to remove Chrome. Try manually:"
            echo "    sudo chflags -R 0 '$APP'"
            echo "    sudo rm -rf '$APP'"
            exit 1
        fi
    else
        echo "Skipping removal. You'll need to remove it manually before restoring."
        exit 0
    fi
else
    echo "Chrome is not currently installed at $APP"
fi

echo ""
echo "=== Now restore from Time Machine ==="
echo ""
echo "METHOD 1 (Recommended): Using Time Machine GUI"
echo "  1. Open Finder and navigate to /Applications"
echo "  2. Click the Time Machine icon in the menu bar, or use Spotlight to open 'Time Machine'"
echo "  3. Click 'Enter Time Machine' or 'Browse Time Machine Backups'"
echo "  4. Navigate back to a backup from a few days ago (before Oct 23)"
echo "  5. Select 'Google Chrome.app' from the /Applications folder"
echo "  6. Click 'Restore' button"
echo "  7. Time Machine will restore the app with correct permissions"
echo ""
echo "METHOD 2: Using command line (if you have Full Disk Access)"
echo "  1. Find a backup from before Oct 23:"
echo "     ls -lt '/Volumes/Backups.backupdb/$(hostname -s)/*/Macintosh HD - Data/Applications/' | grep Chrome"
echo ""
echo "  2. Restore manually:"
echo "     sudo cp -R '/Volumes/Backups.backupdb/.../Google Chrome.app' /Applications/"
echo ""
echo "METHOD 3: Check your external backup drives"
if ls /Volumes/ | grep -i backup > /dev/null 2>&1; then
    echo "  Found potential backup volumes:"
    ls /Volumes/ | grep -i -E "(backup|time|machine)" | sed 's/^/    - /'
    echo ""
    echo "  Check these volumes for Time Machine backups or app backups"
fi
echo ""
echo "After restoring, verify Chrome works by launching it!"
echo "If permissions are still wrong, run: ./fix-permissions-simple.sh"
