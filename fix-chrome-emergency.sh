#!/bin/bash

# Emergency Chrome Permission Fix
# This script tries multiple approaches to fix Chrome's locked permissions

echo "=== Emergency Chrome Permission Fix ==="
echo ""
echo "This will attempt to fix Chrome's locked permissions using multiple methods."
echo "You will be prompted for your password."
echo ""

APP="/Applications/Google Chrome.app"

if [ ! -e "$APP" ]; then
    echo "Error: Chrome not found at $APP"
    exit 1
fi

echo "Step 1: Remove any immutable flags..."
sudo chflags nouchg "$APP" 2>&1

echo ""
echo "Step 2: Remove schg (system immutable) flag..."
sudo chflags noschg "$APP" 2>&1

echo ""
echo "Step 3: Clear all flags..."
sudo chflags 0 "$APP" 2>&1

echo ""
echo "Step 4: Attempting to change ownership to you (this might fail, that's OK)..."
sudo chown -R "$USER:admin" "$APP" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "  ✓ Ownership changed successfully"
else
    echo "  ⚠ Ownership change failed (may be protected)"
fi

echo ""
echo "Step 5: Attempting chmod 755..."
sudo chmod 755 "$APP" 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ Main bundle permission changed to 755"
else
    echo "  ✗ Failed to change permissions - Chrome may be protected by security software"
    echo ""
    echo "Possible causes:"
    echo "  1. Chrome is protected by Endpoint Security software"
    echo "  2. The filesystem has special protections"
    echo "  3. Chrome was installed by MDM (Mobile Device Management)"
    echo ""
    echo "Try these alternatives:"
    echo "  1. Delete Chrome and reinstall it: rm -rf '/Applications/Google Chrome.app'"
    echo "  2. Copy Chrome from your backup drive instead"
    echo "  3. Check if you have Endpoint Security software running"
    exit 1
fi

echo ""
echo "Step 6: Fixing internal permissions (may take a moment)..."
sudo find "$APP" -type d -exec chmod 755 {} + 2>/dev/null
sudo find "$APP" -type f -exec chmod 644 {} + 2>/dev/null
sudo find "$APP/Contents/MacOS" -type f -exec chmod 755 {} + 2>/dev/null

echo ""
echo "Step 7: Removing quarantine attributes..."
sudo find "$APP" -exec xattr -c {} \; 2>/dev/null

echo ""
echo "Step 8: Verifying permissions..."
ls -ld "$APP"

echo ""
echo "=== Done ==="
echo "Try launching Chrome now. If it still doesn't work, you may need to:"
echo "  1. Delete and reinstall Chrome"
echo "  2. Right-click Chrome and select 'Open' to bypass Gatekeeper"
echo "  3. Check System Settings > Privacy & Security for blocked apps"
