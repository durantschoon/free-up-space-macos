# TODO

## High Priority

- [ ] **Detect Corrupted Copies & Time Machine Integration**: Implement better detection for incomplete or corrupted app copies, and explore using Time Machine backups as a restoration source
  - Current issue: Multiple manual copy attempts may result in smaller file sizes on external disk
  - Potential solutions being investigated:
    - Compare file counts between source and destination
    - Verify critical files (executables, Info.plist, frameworks)
    - Hash comparison for key files
    - Deep integrity checking
    - **Check Time Machine backups and restore apps from there instead** - may prevent corrupted copies entirely
    - Explore if Time Machine backups can identify better candidates for moving (files that can be safely restored)
  - Challenge: What to do when multiple copy attempts fail? Options:
    - Warn user and suggest specific apps may be corrupted
    - Provide detailed diagnostic information about what's missing
    - Recommend using different copy methods (rsync, ditto, cp -a)
    - Mark app as "uncopyable" and suggest keeping it on main drive
    - Fall back to Time Machine restoration if available

- [ ] **Fix/prevent missing icons for restored apps**
  - When applications are moved or restored on macOS, the system icon cache may not update properly, causing apps to appear with generic icons
  - Potential solutions to investigate:
    - Force icon cache refresh using `touch` or similar commands
    - Use macOS's icon services commands (`iconutil`, Launch Services)
    - Set proper extended attributes (xattr) that macOS uses for icon display
    - Rebuild the Launch Services database (`lsregister`)

## Medium Priority

- [ ] Improve automated move success rate (investigating alternatives to `shutil.move`)
- [ ] Add size verification after copies complete
- [ ] Better handling of apps with SIP/system protection
- [ ] Option to create symlinks instead of moving files
- [ ] Dry-run mode to preview actions without making changes

## Low Priority

- [ ] Support for moving other large directories (not just apps)
- [ ] Compression options for rarely-used apps
