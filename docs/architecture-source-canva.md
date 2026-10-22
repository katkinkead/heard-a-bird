# Architecture source and current decisions

Read against the [Canva board](https://www.canva.com/design/DAHYbV4yjds/edit), pages 1–4, on 21 October 2026; live pages 1 and 3 and their hardware links rechecked in signed-in Chrome on 22 October 2026. Page 1 contains the detailed physical connections; pages 2 and 3 simplify production and MVP. This record preserves their meaning locally so installation does not depend on Canva access. Prices were not imported because they change.

## MVP: a Pi and the Mac you already have

The CanaKit Pi 5 (4 GB) runs BirdNET-Go locally. The Clippy EM272 mono microphone connects to the UGREEN 30724 microphone input; USB carries audio to the Pi. For the first test, use the kit's appropriate mains supply, cooling and home network. The Mac runs the server and the display browser. A phone can view the read-only display/status over the same network. Optional walkabout tests use a suitable power bank and a hotspot that allows Pi-to-Mac traffic; this is a later physical test, not a reason to change the working home-network configuration first.

[Step 0: the MVP Amazon list](https://www.amazon.co.uk/hz/wishlist/ls/2631A1V48YH7R) contains the CanaKit, UGREEN adapter and two windshield options when inspected. The [Clippy microphone](https://micbooster.com/product/clippy-em272-microphone/) is ordered separately. Choose a compatible windshield, not both by default. Check the actual kit contents and OS setup before buying duplicate power/card accessories or flashing a card.

## Production: powered Ethernet outdoors, dedicated server indoors

- Inside: router/switch data connects to the Ubiquiti U-POE+ injector's data input. Mains powers the injector.
- Its PoE output supplies the outdoor Ethernet run. The ETH-SP-G2 surge protector belongs at the building cable entry with grounding per the manufacturer's instructions. The board flags its full PoE+ chain compatibility for confirmation.
- Outdoors: the Waveshare 5 V / 5 A USB-C PoE splitter separates the incoming powered Ethernet into Ethernet data and USB-C power for the Pi 5. The microphone still connects through its USB sound card.
- The sheltered Hammond 1590Z150 enclosure, bottom cable glands, windshield and passive thermal path are the proposed outdoor hardware. Fit, sealing, electrical noise and sustained heat/load need physical verification.
- Indoors: a Beelink EQ14 is the selected production server candidate. The supported application profile is Linux/systemd; the earlier design's Docker-server sketch is not the shipped server service. The display opens the server's webpage over the network, or an HDMI-connected kiosk computer provides the browser.
- Board colours: blue is Ethernet, green is power, orange is Wi-Fi and purple is the analogue microphone cable. PoE carries power and data together before the splitter.

The power override is covered in [production setup](production.md). It changes the Pi's peripheral-current limit; it does not manufacture extra power or repair a faulty supply.

## Decisions that supersede the older diagram

**Microphone choice, 22 October 2026:** the live board and original shopping guide say only “Clippy EM272 mono”. For the Clippy route, specify **one assembled Clippy EM272M mono, ordinary 3.5 mm TRS plug**, with UGREEN 30724 provisionally retained for acceptance testing. Select **Capsules: Single; Microphone: EM272M** on the [assembled microphone page](https://micbooster.com/product/clippy-em272-microphone/?attribute_pa_microphone=em272m&attribute_pa_single_2_4_matchedcapsules=single). This selects the capsule with improved RF protection; it does not establish complete-system superiority over AudioMoth USB. The latter has fewer separate audio components and remains a legitimate first-choice candidate for a new installation, rather than only a fallback. See [the comparison and acceptance checks](birdnet-pi-reliability.md#microphone-choice-for-new-orders). The live Canva diagram was read, not edited; it still uses the generic EM272 label.

The exact board links are [CanaKit Red/White 4 GB / 64 GB kit](https://www.canakit.com/canakit-raspberry-pi-5-4gb-starter-kit-red-white-64gb.html), [Waveshare splitter at The Pi Hut](https://thepihut.com/products/gigabit-poe-splitter-usb-c), [U-POE+ at NetXL](https://www.netxl.com/networking-accessories/ubiquiti-u-poe-+/), and [ETH-SP-G2 at Connectec](https://securitytec.connectec.uk/networking/network-devices/wireless-bridges/ubiquiti-eth-sp-g2-ethernet-network-surge-protector). The splitter listing explicitly includes Pi 5 compatibility; the surge protector's seller lists it as discontinued/out of stock on its canonical site. See [production checks](production.md) for the remaining distinctions between advertised compatibility, available stock and verified operation.

The board's AI cloud drawing box is optional authoring, not a requirement for each bird. Normal playback uses the approved artwork and completed animations stored on the server. Missing art is logged and can email the configured recipient; it is not generated and published without review. Routine health checks, retries and backups run without AI keys. Operator-triggered AI work needs the operator's AI access. Mail delivery needs an outgoing mail account and connectivity.

The [reference collection](../artwork/index.html) records finished portraits separately from the five completed playback animations. The other thread is creating additional reusable bird layers for portrait and shared-branch presentations; uncompleted/unverified files do not enter the live playback catalogue.

## Evidence still required on the actual equipment

The board lists aims as well as wiring. Software tests do not establish microphone plug-in power, audio quality, weatherproofing, Pi-to-phone reachability, enclosure heat, power-bank runtime or recovery from a physical power cut. See [verification](verification.md) for what has actually been tested and [Pi reliability](birdnet-pi-reliability.md) for failure handling.
