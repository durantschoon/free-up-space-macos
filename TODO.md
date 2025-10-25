# TODO

## High Priority

- [x] **Time Machine Integration** - COMPLETED (October 2025)
  - ✅ Time Machine is now the PRIMARY strategy
  - ✅ Automatically detects TM backups
  - ✅ Guides user to verify apps exist in TM
  - ✅ Simply deletes verified apps (no copying = no corruption!)
  - ✅ Falls back to external drive if TM unavailable
  - ✅ Easy restoration through Time Machine GUI (perfect permissions!)
  - **⚠️ PENDING TESTING**: Will be tested when next macOS upgrade requires disk space

- [ ] **Test Time Machine Integration** - When next macOS upgrade occurs
  - Real-world validation of TM detection
  - Verify app verification workflow
  - Test deletion and restoration
  - Fix any bugs discovered

- [ ] **Detect Corrupted Copies** (External drive method only)
  - Current issue: Multiple manual copy attempts may result in smaller file sizes on external disk
  - Potential solutions:
    - Compare file counts between source and destination
    - Verify critical files (executables, Info.plist, frameworks)
    - Hash comparison for key files
    - Deep integrity checking
  - Note: Time Machine method eliminates this issue entirely!

- [ ] **Fix/prevent missing icons for restored apps**
  - When applications are moved or restored on macOS, the system icon cache may not update properly, causing apps to appear with generic icons
  - Potential solutions to investigate:
    - Force icon cache refresh using `touch` or similar commands
    - Use macOS's icon services commands (`iconutil`, Launch Services)
    - Set proper extended attributes (xattr) that macOS uses for icon display
    - Rebuild the Launch Services database (`lsregister`)

## Medium Priority

- [ ] Improve automated move success rate for external drive method (investigating alternatives to `shutil.move`)
- [ ] Add size verification after copies complete (external drive method)
- [ ] Better handling of apps with SIP/system protection (external drive method)
- [ ] Dry-run mode to preview actions without making changes
- [ ] Add example workflow screenshots to README

Note: Time Machine method has largely eliminated the need for many of these improvements!

## Low Priority

- [ ] Support for moving other large directories (not just apps)
- [ ] Compression options for rarely-used apps
