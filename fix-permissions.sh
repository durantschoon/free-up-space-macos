#!/bin/bash

echo "Fixing permissions and attributes for the three apps..."

# Fix basic permissions
echo "Setting permissions to 755..."
sudo chmod -R 755 /Applications/iMovie.app /Applications/Docker.app /Applications/FreeCAD.app

# Remove extended attributes (quarantine, etc.)
echo "Removing extended attributes..."
sudo xattr -c /Applications/iMovie.app
sudo xattr -c /Applications/Docker.app
sudo xattr -c /Applications/FreeCAD.app

# Remove extended attributes recursively from all files inside
echo "Removing extended attributes from all files inside apps..."
find /Applications/iMovie.app -type f -exec sudo xattr -c {} \;
find /Applications/Docker.app -type f -exec sudo xattr -c {} \;
find /Applications/FreeCAD.app -type f -exec sudo xattr -c {} \;

# Fix ownership
echo "Setting ownership to root:wheel..."
sudo chown -R root:wheel /Applications/iMovie.app /Applications/Docker.app /Applications/FreeCAD.app

echo "Done! The apps should now have proper permissions and attributes."
