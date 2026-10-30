"""Resolve saved setup inputs and the route to a named Pi, without logging in."""
import ipaddress
import socket
from urllib.parse import urlsplit
from .github_launcher import validate_details, read_details, private_write


def route_address(hostname, port):
    """A UDP route lookup sends no application data or SSH commands."""
    for entry in socket.getaddrinfo(hostname, 22, socket.AF_INET, socket.SOCK_DGRAM):
        remote = ipaddress.ip_address(entry[4][0])
        if remote.is_loopback or remote.is_unspecified or remote.is_multicast:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(3)
            sock.connect(entry[4])
            local = ipaddress.ip_address(sock.getsockname()[0])
        if not (local.is_loopback or local.is_unspecified):
            return 'http://%s:%s' % (local, port)
    raise OSError('No usable IPv4 route')


def prepare(directory, port, overrides=None, context=None, route=route_address):
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Invalid server port')
    path = directory / 'setup-details.json'
    saved = read_details(path) if path.exists() else {}
    supplied = validate_details(overrides or {})
    # A new host must not inherit another Pi's login or microphone choice.
    if supplied.get('hostname') and supplied['hostname'] != saved.get('hostname'):
        for key in ('username', 'capture_device', 'use_existing_birdnet'):
            saved.pop(key, None)
    values = {**saved, **supplied}
    previous = ((context or {}).get('setup', {}).get('job') or {}).get('inputs') or {}
    if previous.get('hostname') == values.get('hostname'):
        for key in ('username', 'latitude', 'longitude', 'server_url', 'use_existing_birdnet'):
            if key not in values and key in previous: values[key] = previous[key]
    values = validate_details(values)
    notes = []
    if values.get('hostname') and not values.get('server_url'):
        try:
            values['server_url'] = route(values['hostname'], port)
            notes.append('Indoor server address selected from the route to the Pi; the Pi-to-server connection still needs verification.')
        except OSError:
            notes.append('The Pi name did not resolve to a usable route. Check power, the name and the shared network before asking for manual network settings.')
    missing = [key for key in ('hostname', 'username', 'server_url', 'latitude', 'longitude') if key not in values]
    if values.get('server_url'):
        host = urlsplit(values['server_url']).hostname
        try: invalid = ipaddress.ip_address(host).is_loopback or ipaddress.ip_address(host).is_unspecified
        except ValueError: invalid = host == 'localhost'
        if invalid:
            missing.append('server_url')
            notes.append('The saved server address points at loopback; select the indoor computer’s reachable address.')
    questions = []
    if 'username' in missing: questions.append('What account name did you choose when setting up the Pi?')
    if 'latitude' in missing or 'longitude' in missing:
        questions.append('Confirm the garden location for sunrise times and BirdNET’s regional filter. Reuse the saved place if available; do not invent coordinates.')
    private_write(path, values)
    return {'details': values, 'missing': missing, 'questions': questions, 'notes': notes,
            'ready_to_probe': not missing, 'pi_login_attempted': False,
            'next': 'Use the guarded probe with these details.' if not missing else 'Resolve only the listed missing inputs, save them, and run prepare again.'}
