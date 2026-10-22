# Moving into a permanent home

The supported dedicated-host profile is Linux with systemd and Python3.9+ (Ubuntu/Debian-style). The project board names a **Beelink EQ14** for the indoor server; the actual unit, Linux installation and power-recovery behavior still need verification. A Windows installation is outside this release. Use the same code and artwork; do not start a second application fork.

## The garden Pi's production power profile

**The microphone power path stays the same in MVP and production:** Pi USB → UGREEN US205/30724 → Clippy's 3.5 mm microphone connection. The USB-powered adapter supplies the Clippy's required plug-in power; no separate microphone power supply is planned. This is the intended wiring, not a completed hardware test. See the [Clippy manufacturer's requirements](https://micbooster.com/product/clippy-em272-microphone/) and [a documented build using this exact pairing](https://github.com/arnegiacomo/fugleramme/blob/main/docs/hardware.md).

For the indoor MVP, use the Pi 5 kit's suitable mains supply. [CanaKit's current starter kit](https://www.canakit.com/canakit-raspberry-pi-5-starter-kit-turbine-black.html?defpid=4913) includes a CanaKit or Raspberry Pi PD supply; [CanaKit's 45 W model](https://www.canakit.com/canakit-45w-usb-c-power-supply-with-pd-black.html) specifies the 5 V / 5 A mode. Confirm the supplied model and successful negotiation. A recognised 5 A supply needs no manual USB-current override.

The project board's intended chain is **Ubiquiti U-PoE+ → outdoor Ethernet/surge protection → Waveshare POE-SPLITTER-25W-TYPE-C → Raspberry Pi 5 USB-C power**, with the splitter's Ethernet output supplying data. It also names **ETH-SP-G2** surge protection. This is a recorded design, not a tested installation.

The live Canva links were rechecked on 22 October 2026. [The Pi Hut's exact splitter listing](https://thepihut.com/products/gigabit-poe-splitter-usb-c) identifies Waveshare **WAV-27736**, 5 V / 5 A maximum, IEEE 802.3af/at, and explicitly lists **Raspberry Pi 5 compatibility**. [The linked NetXL injector](https://www.netxl.com/networking-accessories/ubiquiti-u-poe-+/) is U-POE+, 30 W IEEE 802.3at (box contents also call it U-POE-AT). Their advertised PoE standards match; do not describe this as an unidentified or evidently incompatible splitter. Compatibility does not establish its USB-PD negotiation or a measured full-load power budget. The [exact CanaKit link](https://www.canakit.com/canakit-raspberry-pi-5-4gb-starter-kit-red-white-64gb.html) identifies the Red/White 4 GB / 64 GB kit, preloaded 64-bit Pi OS and a CanaKit or official Pi USB-C PD supply.

The [linked surge protector seller's current page](https://connectec.uk/networking/network-devices/wireless-bridges/ubiquiti-eth-sp-g2-ethernet-network-surge-protector) marks ETH-SP-G2 discontinued/out of stock. This is that seller's status, not proof the manufacturer discontinued it. The board itself marks “PoE+ TBC”; the manufacturer-rating question below remains distinct from finding an in-stock supplier.

The [Waveshare specification](https://www.waveshare.com/product/modules/others/power-relays/poe-splitter-25w-type-c.htm) gives 37–57V PoE input, IEEE802.3af/at support and **5V5A maximum** output. The [U-PoE+ specification](https://techspecs.ui.com/unifi/accessories/u-poe-plus) lists the 30W adapter with 48V/0.65A output. These component ratings do not establish the power available at the Pi after cable and conversion losses.

[TI's PoE design guide, Table 2-2](https://www.ti.com/lit/ug/tiduex8/tiduex8.pdf), distinguishes 30 W at an IEEE 802.3at injector from 25.5 W at the powered-device input, before splitter conversion losses. Waveshare's 25 W maximum therefore does not guarantee 25 W delivered at the Pi. The actual Pi, fan and audio load may need less; verify that load with the final cable run and enclosure.

**Two design details remain to verify on the actual chain:** the splitter's USB-PD negotiation behavior and the ETH-SP-G2's suitability for this PoE+ load. The retrieved Waveshare manufacturer specification does not state PD behavior. The [ETH-SP-G2 datasheet](https://dl.ui.com/datasheets/ETH-SP/ETH-SP-G2_DS.pdf) explicitly lists 802.3af; the [current product page](https://store.ui.com/us/en/products/ethernet-surge-protector) lists generic PoE support. Neither is an explicit PoE+ current rating. Keep the board's “PoE+ TBC” open until confirmed by the supplier/manufacturer or a qualified installer. Follow the [manufacturer's grounding instructions](https://dl.ui.com/qsg/ETH-SP-G2/ETH-SP-G2_EN.html); the software cannot verify grounding or weather protection.

For a Pi5 without a recognised 5V5A PD supply, Raspberry Pi documents a 600mA combined USB allowance. `usb_max_current_enable=1` raises it to1.6A. This changes a limit, not the power supply's capacity. It is unnecessary for a working low-power microphone setup whose combined USB requirement fits600mA. The design note about using this override is therefore a **conditional production setting**, not an MVP default. See [Raspberry Pi's USB power white paper](https://pip-assets.raspberrypi.com/categories/685-app-notes-guides-whitepapers/documents/RP-009856-WP-1-USB%20Power%20delivery%20on%20Raspberry%20Pi%205.pdf).

The local assistant can inspect the Pi without changing anything:

```sh
python3 scripts/pi-production-power.py --plan --profile waveshare-25w-pi5
python3 scripts/pi-production-power.py --diagnose
```

Once the exact chain's capacity has been verified, add the actual maximum USB load and total Pi/fan/USB/accessory budget, including startup margin. The values below are placeholders to replace, **not default measurements**:

```sh
sudo python3 scripts/pi-production-power.py --apply --profile waveshare-25w-pi5 \
  --supply-verified --usb-budget-ma USB_MILLIAMPS --total-budget-ma TOTAL_MILLIAMPS
```

Use `--usb-boot` only if USB boot is required and the storage device is included in that budget. The helper requires Pi5 evidence, readable active power state, no reported current/past throttle or boot USB over-current flags, and a budget within the1.6A USB/5A total ceilings. `--supply-verified` records an operator assertion, not a measurement performed by Songsketch. Do not set it while the chain's compatibility or capacity is unresolved.

Apply creates a timestamped `config.txt.songsketch-power-….bak`, then atomically adds a small Pi5-only managed block to `/boot/firmware/config.txt`. It is idempotent and leaves all unrelated settings intact. Existing USB-power settings, altered managed blocks and included config files require manual review instead of an overwrite. No EEPROM changes, automatic reboot, database reset or blind restart are performed. [Raspberry Pi boot configuration documentation](https://www.raspberrypi.com/documentation/computers/config_txt.html) explains the file and reboot behavior.

After an intentional reboot, verify the active allowance, absence of new power/throttle flags, stable USB capture and advancing inference under sustained real BirdNET load in the finished enclosure. A successful setting write is not a completed power test. If rollback is required, compare the recorded backup with today's file and restore only the managed change; do not overwrite later unrelated edits. See [BirdNET/Pi reliability notes](birdnet-pi-reliability.md) for the full fault checklist.

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
