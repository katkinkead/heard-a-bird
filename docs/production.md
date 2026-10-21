# Moving into a permanent home

The supported dedicated-host profile is Linux with systemd and Python3.9+ (Ubuntu/Debian-style). The exact mini PC has not been selected. A Windows installation is outside this release. Use the same code and artwork; do not start a second application fork.

## Move the history

1. On the Mac dashboard, choose **Keeping well → Download migration bundle**. Keep this ZIP private: it contains garden history and non-secret settings. API keys, SMTP passwords and station tokens are excluded.
2. Stop the Mac foreground run or its background service. Keep the old Mac data as rollback until the new installation is verified.
3. Install the same Songsketch release on the mini PC. Run `sudo bash scripts/install-server-linux.sh`; review the helper first. It installs the application in `/opt/songsketch-server`, an unprivileged service and data in `/var/lib/songsketch-server`.
4. Stop the new service: `sudo systemctl stop songsketch-server`. Restore the exported ZIP as its service user: `sudo -u songsketch python3 /opt/songsketch-server/scripts/restore.py /path/to/songsketch-migration.zip --data-dir /var/lib/songsketch-server`. The file must be readable by that user. The restore verifies the DB and creates a rollback copy before replacing existing data.
5. Start the service again. From the mini PC open `http://localhost:8765/setup`. For a headless host, use `ssh -L 127.0.0.1:8765:127.0.0.1:8765 user@mini-pc` from a Mac with no server occupying that local port, then visit localhost. Read the private setup code from the new host’s `secrets.json` locally; never share that file.
6. Choose the Linux profile in settings, re-enter email/AI credentials as wanted, and re-pair the Pi to the new server address/token. `scripts/pair-pi.sh` needs the service data directory; run it locally as the service user with `SONGSKETCH_DATA_DIR=/var/lib/songsketch-server`, or use the private manual provisioning route in the Pi notes.
7. Verify one test painting and a real detection, history counts, offline replay, email, service restart and host reboot. Point the display browser at the mini PC’s LAN address.

## Before leaving it unattended

- Reserve the server/Pi LAN addresses in the router, or use verified local hostnames. Do not expose port8765 to the internet.
- Check automatic power recovery in the mini PC’s firmware and a real power-loss/restart cycle. Decide whether a UPS is needed for your installation.
- Restore a backup on a separate test data directory. Seven snapshots on one disk protect against some mistakes, not disk loss; copy migration exports to another device on an appropriate schedule.
- Run a sustained test with the actual display browser. Exercise brief network loss and ensure reports/history catch up without duplicate counts.
- Confirm the final enclosure, power supply, microphone weather protection and network route suit the outdoor site. Software tests cannot establish weatherproofing.
- Document who receives missing-art emails and who handles unresolved issues. Immediate notice of a completely dead server needs a separate monitoring host; none is configured by this MVP.

## Updates and rollback

Download a known versioned release. Make a verified migration export, stop the service, retain the current application directory as a rollback copy, then install the replacement. Do not run two versions on the same data directory. Re-run local checks and the hardware smoke test. Preserve the exported database if a future version changes its schema; restoring old code over a migrated database is not automatically safe.

The current database schema is version1. Installer reruns preserve configuration and runtime data. The Pi installer retains its first downloaded BirdNET image digest instead of silently tracking a moving latest tag. A BirdNET upgrade needs its own API/microphone test.
