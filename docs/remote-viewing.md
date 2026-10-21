# Watch the garden from away

**Songsketch is local-network-only by default.** Private remote viewing needs the additional setup below. These instructions have been checked against the application and official Tailscale documentation; remote access has **not** been configured or tested on your equipment.

Start with the [illustrated setup guide](../guide/index.html) or [friend’s short instructions](friend-start-here.md). Get the painting working at home first.

## The simple private route

Install Tailscale on the computer running Songsketch and on the phone, tablet or computer you will watch from. It connects those approved devices privately. The garden Pi can keep sending detections over the home network; it does not need Tailscale for this arrangement.

| Where you are watching | Address to use |
|---|---|
| On the server computer itself | `http://localhost:8765/` |
| On another device at home | The server’s actual home-network address, with `http://` before it and `:8765/` after it |
| Away from home, with Tailscale connected | The server’s actual Tailscale IPv4 address, with `http://` before it and `:8765/` after it |

`localhost` always means the device you are using. It cannot take your phone back to the garden server.

## Set it up on your own devices

1. **Leave the garden running.** Start Songsketch on the Mac, open its painting page and confirm it works. Keep the Mac plugged in, awake and connected, with the lid open. Keep its normal server port at **8765**.
2. **Connect the Mac.** Follow [Tailscale’s macOS installation guide](https://tailscale.com/docs/install/mac). Use its recommended standalone installer, complete sign-in and approve the operating system’s VPN configuration prompts yourself.
3. **Connect your viewing device.** Install the official client for [iPhone/iPad](https://tailscale.com/docs/install/ios), [Android](https://tailscale.com/docs/install/android) or [another supported computer](https://tailscale.com/download). Sign in with your own Tailscale account and connect. Someone else should use their own account; see the friend section below.
4. **Copy the address.** In Tailscale’s **Machines** page, find the Mac running Songsketch and copy its Tailscale **IPv4** address. On the viewing device, type `http://`, paste that address, then add `:8765/`. Save that complete address as a bookmark. Tailscale’s [device connection guide](https://tailscale.com/docs/how-to/connect-to-devices) explains where to find addresses and how service ports work.
5. **Try it away from Wi-Fi.** Turn off your phone’s Wi-Fi, keep mobile data and Tailscale connected, and open the bookmark in a new tab. From the Mac’s dashboard, send a labelled test bird and confirm it reaches the phone. This is the remote acceptance check; a painting already open in a tab is not proof of a fresh connection.

You can also use the server’s actual full MagicDNS name with `http://` and `:8765/`. Copy the name shown by Tailscale rather than inventing one. [MagicDNS documentation](https://tailscale.com/docs/features/magicdns).

This route uses HTTP inside Tailscale’s encrypted connection. Tailscale encrypts traffic between its devices, but the browser may still label the HTTP page “Not secure.” This does not add HTTPS to the ordinary home-network address. [Encryption](https://tailscale.com/docs/concepts/tailscale-encryption) · [Browser/HTTPS distinction](https://tailscale.com/docs/how-to/set-up-https-certificates).

## Let a friend watch

Share **the Songsketch server machine** with the friend, rather than inviting them into your entire private network. This limits which machine they can reach. [Inviting versus sharing](https://tailscale.com/docs/reference/inviting-vs-sharing).

Before sharing, the network owner should review **Access controls** and allow the intended viewer to reach only this server on **TCP 8765**. In a grant, that port selector is `"ip": ["tcp:8765"]`. Grants add together: a narrow rule does not cancel an existing broad rule. Review other matching grants/ACLs instead of pasting a replacement policy over an existing network. [Grant syntax and visual policy editor](https://tailscale.com/docs/reference/syntax/grants).

Then, in **Machines → the server’s menu → Share**, create a single-use invitation and send it privately to the intended person. They install Tailscale, use their own account and accept. Check the accepted identity before treating setup as finished. They should copy the shared machine’s address as shown in **their** Tailscale app and open it on port 8765. A shared machine’s full MagicDNS name also works; its short name does not. Revoke access through the machine’s Share dialog when needed. [Official machine-sharing steps](https://tailscale.com/docs/features/sharing).

Sharing by itself is not a restriction to one port. Port 8765 serves the painting, public status, catalogue and static artwork. The protected operator functions still require a local connection and the operator credential; a viewer should never receive that credential.

## What stays local, and what must stay on

The current [server](../songsketch/server.py) listens on `0.0.0.0:8765`, so direct Tailscale access can reach the same application without changing the Pi’s home-network route. Administrator endpoints check both a loopback source address and a localhost Host header. Remote viewers do not satisfy those checks.

Use this direct connection for viewing. A localhost reverse proxy would change those trust assumptions and needs a separate access review. Remote administration, if required, uses the deliberate SSH tunnel described in [production setup](production.md).

The server must remain awake, online and running; the viewing device must have Internet access and Tailscale connected. An old painting may remain visible after a connection drops. No router port-forward, public tunnel, exit node or subnet router is needed for this design. A link that works in any browser without Tailscale would be a separate public or authenticated web-hosting feature.

If the page does not load, check the actual address, both Tailscale connections, the running server, the host firewall and access policy. Do not disable the whole firewall or expose port 8765 publicly. [Connection troubleshooting](https://tailscale.com/docs/how-to/connect-to-devices).

## Later: the dedicated Linux server

After the [production migration](production.md), follow the [official Linux installation instructions](https://tailscale.com/docs/install/linux) on the new server. After installation, `sudo tailscale up` gives the owner a sign-in URL. Use `tailscale ip` or the Machines page to find its address; choose the IPv4 address for this application. Reapply the intended viewing access, update the bookmark and repeat the mobile-data test. This does not automatically move the Mac’s identity or shares to the new host.

The owner handles installation, account sign-in, device permissions and sharing/access-policy approval. This guide has not performed any of those actions. Record successful remote viewing separately from the [existing local verification](verification.md).
