# Start here, garden keeper

Songsketch has three everyday parts: the garden Pi hears birds, an indoor computer remembers them, and a browser paints the portraits. A local AI assistant can handle the software setup while the visual guide shows what is happening.

## Give the assistant the job

Open an assistant that can use a terminal and files **on the computer being set up**. Give it the [setup handoff prompt](ai-setup.md#copy-this-to-your-local-assistant). It will read the existing project, obtain the release, organise its folders, start the server and work through the Pi connection and checks. You should not have to copy a chain of terminal commands or recreate this project with AI.

The [GitHub repository](https://github.com/katkinkead/songsketch) is private. Use your existing authorised access, or ask the owner for the release ZIP and point the assistant to it. A supplied ZIP works without a GitHub account. Never paste an access token into chat.

Ordinary cloud chat cannot reach your computer or Pi by itself. If the assistant has no local tools, use the same prompt in a terminal-capable assistant. The HTML page alone cannot start SSH or install software before the local helper is running.

## Your part is the garden and the permissions

Connect the Pi’s suitable power supply, USB sound card and microphone. Supply the garden location and the Pi account/network details when asked. Enter secrets through a local private prompt, and confirm the actual Pi’s SSH fingerprint or operating-system permission when needed.

A working supported 64-bit Pi OS can be reused. A blank card or a Pi without a usable account, network or SSH connection may need first-boot setup or Raspberry Pi Imager. Writing an image erases the selected card: the assistant must explain the need and get your approval first. A preloaded OS is not the same as an installed BirdNET system.

Once the assistant opens the control panel, follow only the human actions it identifies. Use the URL it opens so its private session stays connected. Check the labelled test painting, then the real microphone and a real bird. A completed diagnostic is not proof that installation or the equipment passed.

## Leave it running

The MacBook MVP works while the Mac is awake, powered and connected. A dedicated Linux computer can run the same application later; the assistant handles the supported service installation and migration. Power, weatherproofing, microphone placement, network coverage and a real reboot/reconnect test still need attention on site. See [production setup](production.md).

BirdNET-Go with BirdNET v2.4 and the five approved paintings need **no AI API key**. Missing-portrait email and paid AI draft tools are optional and can be added after the garden works. New art needs review; an animation proposal is not a completed new painting sequence.

## If something stops

Tell the local assistant what you observed and ask it to resume from the setup status. It should inspect evidence, make bounded safe repairs and create a redacted support packet if it cannot finish. You should only be asked for the specific physical action or permission it cannot perform.

The Pi queues reports when the server is unreachable and uploads them after reconnection. The dashboard also offers a report download. A host without power cannot send its own alert; a quiet garden alone does not mean a fault. The server has defined automatic recovery and maintenance, not unlimited AI repair authority.

The painting is available on the home network by default. [Private remote viewing](remote-viewing.md) is a separate setup. Keep this guide with its release and check [what has actually been verified](verification.md).
