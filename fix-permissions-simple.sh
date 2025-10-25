#!/bin/bash

# Simple permission fix script
# This script ONLY fixes permissions (chmod), not ownership (chown)
# since ownership changes often fail due to SIP and security restrictions

echo "Fixing permissions for applications..."
echo "Note: This script does NOT change ownership, only permissions"
echo ""

# Apps to fix
APPS=(
    "/Applications/Google Chrome.app"
    "/Applications/Docker.app"
    "/Applications/iMovie.app"
)

for APP in "${APPS[@]}"; do
    if [ -e "$APP" ]; then
        echo "Processing: $APP"

        # Fix the main app bundle permission (755 = rwxr-xr-x)
        echo "  - Setting app bundle to 755..."
        sudo chmod 755 "$APP" 2>&1

        # Fix permissions recursively (only if we can access it)
        # Suppress errors for SIP-protected files
        echo "  - Fixing internal permissions..."
        sudo find "$APP" -type d -exec chmod 755 {} + 2>/dev/null
        sudo find "$APP" -type f -exec chmod 644 {} + 2>/dev/null

        # Make executables actually executable
        echo "  - Making executables executable..."
        sudo find "$APP/Contents/MacOS" -type f -exec chmod 755 {} + 2>/dev/null

        # Remove quarantine attributes (recursively using find, not xattr -r)
        echo "  - Removing quarantine attributes..."
        sudo find "$APP" -exec xattr -c {} \; 2>/dev/null

        echo "  ✓ Done with $APP"
        echo ""
    else
        echo "  ⚠ Skipping $APP (not found)"
        echo ""
    fi
done

echo "Finished! Try launching your apps now."
echo ""
echo "If apps still won't launch, you may need to:"
echo "1. Right-click the app and select 'Open' (this bypasses Gatekeeper)"
echo "2. Go to System Settings > Privacy & Security and allow the app"
echo "3. Run: sudo spctl --add '/Applications/AppName.app'"
