# Server health and bounded recovery

`songsketch.supervisor` runs the existing server as its own child and checks the actual HTTP health endpoint. It uses the same application on MacBook and Linux. It requires no AI service, API key or internet connection.

The foreground entry point is:

```sh
python3 -m songsketch.supervisor --host 0.0.0.0 --port 8765 --data-dir /path/to/private/songsketch-data
```

Run from the project root with the installed Python interpreter. Installers and operating-system services can invoke the same module. The watchdog itself does not install a startup service.

## Recovery behaviour

- Before starting, it checks whether the local port is occupied. An existing Songsketch server or another service is left alone; the launcher exits with a helpful message. It never looks up and kills a process merely because it owns a port.
- It starts `sys.executable -m songsketch.server` with the supplied host, port and data folder. The project directory is resolved from the installed module, not a developer's home folder.
- It checks `http://127.0.0.1:<port>/health` every 30 seconds, using a five-second request timeout and a bounded response size. Success requires HTTP 200, `application: "songsketch"` and `ok: true`.
- Three consecutive failed checks restart only its owned child. A successful check clears the failure streak. An exited child is detected without waiting for three HTTP failures.
- Restart delays grow exponentially from one second and never exceed 120 seconds. Five minutes of healthy operation resets the backoff.
- At most five restarts are attempted within a rolling fifteen-minute window during a supervisor run. Exceeding that budget stops the launcher with a nonzero exit; the operating-system service should apply its own restart delay rather than relaunching in a tight loop.
- SIGINT and SIGTERM request a clean shutdown. The owned child receives termination and has ten seconds to exit; a stuck child is killed and reaped. Processes that existed before this launcher are never signalled.
- If the port becomes occupied while restarting, or a health response explicitly identifies another application, the watchdog stops rather than repeatedly targeting that service.

Supported bind hosts are `0.0.0.0`, `127.0.0.1` and `localhost`. These keep the mandatory loopback health check reachable. Use `0.0.0.0` for Pi/display access on the local network. An arbitrary LAN-only bind address is deliberately rejected instead of creating a false health-failure loop.

## Logs and status

The private data folder contains:

- `logs/supervisor.log`: a separate rotating log, at most 1 MB per file plus three retained files.
- `supervisor-status.json`: the latest bounded operational state and reason, UTC update time, owned child PID when present, and restart count for this run.

The watchdog records its own fixed descriptions. It does not copy HTTP response bodies, process output, environment variables or secret configuration into those notes. It never opens or writes the application's SQLite database. Database recovery, pending notifications and diagnostic reconciliation remain the server's responsibility after restart.

This status file is evidence of the watchdog's last action, not proof that the entire installation is healthy. HTTP success exercises the server and its database health query; it does not prove the microphone, BirdNET inference or physical display works. Those components keep their own health checks. A quiet garden does not trigger restarts.

## Exit codes and host service integration

| Code | Meaning |
| --- | --- |
| 0 | A normal stop request; owned server closed |
| 1 | Supervisor error; owned child shutdown attempted |
| 3 | Port occupied or a different application answered; no unrelated process stopped |
| 4 | Restart budget exhausted; operator attention or delayed host-level retry needed |

Host service configuration should distinguish a permanent port conflict from a recoverable child crash and provide restart throttling. Power loss cannot be reported by the powered-off server; the Pi's durable queue and later reconciliation still matter. A dedicated mini PC adds deployment-specific power and startup verification without a second application fork.

## Verification

The unit cases in `tests/test_supervisor.py` use mocked subprocesses, mocked HTTP responses and a fake monotonic clock. They verify application identity, response bounds, startup conflicts, failure streaks, recovery limits, exponential delays, graceful/forced shutdown, rotation and signal handling without starting a service or contacting an external host.

One real-process integration case starts a supervisor and server using a temporary data folder and ephemeral loopback port. It records a simulated detection, kills only that supervisor's owned child, verifies a replacement PID and restored HTTP service with the detection still present, then stops the parent and checks that both owned children are gone. This exercises actual process-crash recovery and persistence; it does not install or verify launchd or systemd.

These tests establish watchdog behaviour in isolation. The launchd/systemd wiring and recovery from actual application hangs, reboots and power interruptions must also be checked on the deployment host.
