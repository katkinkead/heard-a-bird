# Start here, garden keeper

Songsketch has three everyday parts: the garden Pi hears birds, an indoor computer remembers them, and a browser paints the portraits. A local AI assistant can handle the software setup while the visual guide shows what is happening.

## Open the setup guide

The [illustrated guide](../guide/index.html) starts with what you need, then Pi preparation, garden details, connection to a local assistant and live installation stages. Keep an existing usable Pi OS; prepare a new card for headless access only when needed.

In Step 0, use the [MVP Amazon list](https://www.amazon.co.uk/hz/wishlist/ls/2631A1V48YH7R) for the CanaKit, USB sound card and windshield options. Its four items include two alternative windshields: choose one compatible fit. Order the [Clippy EM272M mono TRS microphone separately from Micbooster](https://micbooster.com/product/clippy-em272-microphone/?attribute_pa_microphone=em272m&attribute_pa_single_2_4_matchedcapsules=single). Check the kit’s card, cooler, case and power supply, and have a card reader available.

At **Connect your AI**, use the guide’s **Connect my AI & install** button. Unzip `Install Songsketch.zip`, then open the launcher inside once; the ZIP preserves the executable file needed by macOS. It obtains the private [GitHub project](https://github.com/katkinkead/songsketch) using existing authorised access and opens an installed Codex or Claude Code in the repository. Complete its normal sign-in or operating-system prompt when asked. Missing prerequisites are explained rather than silently installed.

The assistant reads [the current repository procedure](ai-setup.md) and handles routine computer work. There is no long setup prompt to copy. If the project is already open in a local assistant, ask it to follow that file. An owner-supplied release ZIP can also be used without a GitHub account; never paste an access token into chat.

A standalone HTML page or ordinary cloud conversation cannot start a local assistant or SSH into the Pi. That one local launch is the bridge; after the helper starts, the guide shows its actual progress and errors.

## Your part is the garden and the permissions

Connect the Pi’s suitable power supply, USB sound card and microphone. Supply the garden location and the Pi account/network details when asked. Enter secrets through a local private prompt, and confirm the actual Pi’s SSH fingerprint or operating-system permission when needed.

A working supported 64-bit Pi OS can be reused. A blank card or a Pi without a usable account, network or SSH connection may need first-boot setup or Raspberry Pi Imager. Writing an image erases the selected card: the assistant must explain the need and get your approval first. A preloaded OS is not the same as an installed BirdNET system.

Once the assistant opens the control panel, follow only the human actions it identifies. Use the URL it opens so its private session stays connected. Check the labelled test painting, then the real microphone and a real bird. A completed diagnostic is not proof that installation or the equipment passed.

## Leave it running

The MacBook MVP works while the Mac is awake, powered and connected. A dedicated Linux computer can run the same application later; the assistant handles the supported service installation and migration. Power, weatherproofing, microphone placement, network coverage and a real reboot/reconnect test still need attention on site. See [production setup](production.md).

BirdNET-Go with BirdNET v2.4 and the five approved paintings need **no AI API key**. The local setup assistant uses your existing Codex or Claude account. Optional dashboard AI diagnosis and artwork tools need separately configured API credentials. Missing-portrait email needs local SMTP settings; saving an alert recipient alone does not send or verify a message. These options can wait until the garden works. New art needs review; an animation proposal is not a completed new painting sequence.

## If something stops

Tell the local assistant what you observed and ask it to resume from the setup status. It should inspect evidence, make bounded safe repairs and create a redacted support packet if it cannot finish. You should only be asked for the specific physical action or permission it cannot perform.

The Pi queues reports when the server is unreachable and uploads them after reconnection. The dashboard also offers a report download. A host without power cannot send its own alert; a quiet garden alone does not mean a fault. The server has defined automatic recovery and maintenance, not unlimited AI repair authority.

The painting is available on the home network by default. [Private remote viewing](remote-viewing.md) is a separate setup. Keep this guide with its release and check [what has actually been verified](verification.md).
