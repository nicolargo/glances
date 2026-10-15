#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Minimal nl80211 client (stdlib only) for the wifi plugin.

Reading `/proc/net/wireless` goes through the legacy wireless extensions
(wext) in the kernel. Since Linux 6.x, cfg80211 logs a one-off
"uses wireless extensions which will stop working for Wi-Fi 7 hardware;
use nl80211" warning for any process doing so, and wext returns nothing
for Wi-Fi 7 (MLO) connections. nl80211, spoken over generic netlink, is
the supported replacement.

Only what the plugin needs is implemented: list the station-mode
interfaces and read the signal strength (dBm) of the access point each
one is associated with. Both requests are available to unprivileged users
(the same data `iw dev <if> link` shows).

The module is split in pure message building/parsing helpers (unit tested
without any wireless hardware) and a thin socket layer.
"""

from __future__ import annotations

import errno
import os
import socket
import struct

# --- netlink / generic netlink (include/uapi/linux/{netlink,genetlink}.h) -----
NETLINK_GENERIC = 16
NLM_F_REQUEST = 0x01
NLM_F_DUMP = 0x300  # NLM_F_ROOT | NLM_F_MATCH
NLMSG_ERROR = 0x02
NLMSG_DONE = 0x03
GENL_ID_CTRL = 0x10
CTRL_CMD_GETFAMILY = 3
CTRL_ATTR_FAMILY_ID = 1
CTRL_ATTR_FAMILY_NAME = 2

# --- nl80211 (include/uapi/linux/nl80211.h) -----------------------------------
NL80211_CMD_GET_INTERFACE = 5
NL80211_CMD_GET_STATION = 17
NL80211_ATTR_IFINDEX = 3
NL80211_ATTR_IFNAME = 4
NL80211_ATTR_IFTYPE = 5
NL80211_ATTR_STA_INFO = 21
NL80211_STA_INFO_SIGNAL = 7
NL80211_IFTYPE_STATION = 2

_NLMSG_HDR = struct.Struct("=IHHII")  # length, type, flags, sequence, port id
_GENL_HDR = struct.Struct("=BBH")  # command, version, reserved
_NLA_HDR = struct.Struct("=HH")  # length, type
_NLA_TYPE_MASK = 0x3FFF  # strip NLA_F_NESTED and NLA_F_NET_BYTEORDER
_RECV_SIZE = 65536
_TIMEOUT = 2.0  # seconds, a wedged netlink socket must never hang the plugin


class Nl80211Unavailable(OSError):
    """nl80211 cannot be used here (no netlink, or no cfg80211 in the kernel)."""


def _align(length: int) -> int:
    return (length + 3) & ~3


def _attr(attr_type: int, payload: bytes) -> bytes:
    """Build one netlink attribute, padded to 4 bytes."""
    length = _NLA_HDR.size + len(payload)
    return _NLA_HDR.pack(length, attr_type) + payload + b"\0" * (_align(length) - length)


def _parse_attrs(data: bytes) -> dict[int, bytes]:
    """Parse a flat run of netlink attributes into {type: payload}."""
    attrs: dict[int, bytes] = {}
    pos = 0
    while pos + _NLA_HDR.size <= len(data):
        length, attr_type = _NLA_HDR.unpack_from(data, pos)
        if length < _NLA_HDR.size or pos + length > len(data):
            break
        attrs[attr_type & _NLA_TYPE_MASK] = data[pos + _NLA_HDR.size : pos + length]
        pos += _align(length)
    return attrs


def _request(family: int, command: int, flags: int, attrs: bytes = b"") -> bytes:
    """Build a generic netlink request message."""
    payload = _GENL_HDR.pack(command, 1, 0) + attrs
    return _NLMSG_HDR.pack(_NLMSG_HDR.size + len(payload), family, flags, 1, 0) + payload


def _parse_messages(data: bytes):
    """Yield (type, payload) for each netlink message in one datagram."""
    pos = 0
    while pos + _NLMSG_HDR.size <= len(data):
        length, msg_type, _flags, _seq, _pid = _NLMSG_HDR.unpack_from(data, pos)
        if length < _NLMSG_HDR.size or pos + length > len(data):
            return
        yield msg_type, data[pos + _NLMSG_HDR.size : pos + length]
        pos += _align(length)


def _u32(raw: bytes | None) -> int | None:
    return struct.unpack_from("=I", raw)[0] if raw is not None and len(raw) >= 4 else None


def _transact(sock: socket.socket, message: bytes, dump: bool) -> list[tuple[int, bytes]]:
    """Send a request and return the (type, payload) of its replies.

    A dump is read until NLMSG_DONE; a plain request gets a single reply.
    A kernel error reply is raised as OSError.
    """
    sock.send(message)
    replies: list[tuple[int, bytes]] = []
    while True:
        for msg_type, payload in _parse_messages(sock.recv(_RECV_SIZE)):
            if msg_type == NLMSG_DONE:
                return replies
            if msg_type == NLMSG_ERROR:
                code = -struct.unpack_from("=i", payload)[0] if len(payload) >= 4 else 0
                if code:
                    raise OSError(code, os.strerror(code))
                return replies  # plain acknowledgement
            replies.append((msg_type, payload))
        if not dump:
            return replies


def _resolve_family(sock: socket.socket, name: str) -> int:
    """Return the dynamic generic netlink family id for `name`."""
    request = _request(
        GENL_ID_CTRL,
        CTRL_CMD_GETFAMILY,
        NLM_F_REQUEST,
        _attr(CTRL_ATTR_FAMILY_NAME, name.encode() + b"\0"),
    )
    try:
        replies = _transact(sock, request, dump=False)
    except OSError as exc:
        raise Nl80211Unavailable(f"generic netlink family {name!r} unavailable: {exc}") from exc
    for msg_type, payload in replies:
        if msg_type == GENL_ID_CTRL:
            raw = _parse_attrs(payload[_GENL_HDR.size :]).get(CTRL_ATTR_FAMILY_ID)
            if raw is not None and len(raw) >= 2:
                return struct.unpack_from("=H", raw)[0]
    raise Nl80211Unavailable(f"generic netlink family {name!r} not found")


def _station_interfaces(sock: socket.socket, family: int) -> list[tuple[int, str]]:
    """Return (ifindex, name) of every station-mode wireless interface."""
    replies = _transact(sock, _request(family, NL80211_CMD_GET_INTERFACE, NLM_F_REQUEST | NLM_F_DUMP), dump=True)
    interfaces = []
    for msg_type, payload in replies:
        if msg_type != family:
            continue
        attrs = _parse_attrs(payload[_GENL_HDR.size :])
        ifindex = _u32(attrs.get(NL80211_ATTR_IFINDEX))
        iftype = _u32(attrs.get(NL80211_ATTR_IFTYPE))
        name = attrs.get(NL80211_ATTR_IFNAME)
        # Interfaces without a netdev (e.g. a P2P device) have no ifindex.
        if ifindex is None or name is None or iftype != NL80211_IFTYPE_STATION:
            continue
        interfaces.append((ifindex, name.rstrip(b"\0").decode(errors="replace")))
    return interfaces


def _station_signal(sock: socket.socket, family: int, ifindex: int) -> int | None:
    """Return the signal (dBm) of the AP `ifindex` is associated with, if any."""
    request = _request(
        family,
        NL80211_CMD_GET_STATION,
        NLM_F_REQUEST | NLM_F_DUMP,
        _attr(NL80211_ATTR_IFINDEX, struct.pack("=I", ifindex)),
    )
    for msg_type, payload in _transact(sock, request, dump=True):
        if msg_type != family:
            continue
        sta_info = _parse_attrs(payload[_GENL_HDR.size :]).get(NL80211_ATTR_STA_INFO)
        if sta_info is None:
            continue
        signal = _parse_attrs(sta_info).get(NL80211_STA_INFO_SIGNAL)
        if signal:
            # A signed byte on the wire (kernel: nla_put_u8 of an s8 dBm value).
            return struct.unpack_from("=b", signal)[0]
    return None


def station_signals() -> dict[str, int]:
    """Return {interface name: signal in dBm} for the associated station interfaces.

    Interfaces that are not associated (or report no signal) are left out,
    like `/proc/net/wireless` did.

    Raises Nl80211Unavailable when nl80211 cannot be reached at all (so the
    caller can fall back), and OSError for any later transient failure.
    """
    try:
        sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_GENERIC)
    except (AttributeError, OSError) as exc:  # AttributeError: no AF_NETLINK (not Linux)
        raise Nl80211Unavailable(f"netlink socket unavailable: {exc}") from exc
    with sock:
        sock.settimeout(_TIMEOUT)
        family = _resolve_family(sock, "nl80211")
        signals: dict[str, int] = {}
        for ifindex, name in _station_interfaces(sock, family):
            try:
                signal = _station_signal(sock, family, ifindex)
            except OSError as exc:
                if exc.errno == errno.ENODEV:
                    continue  # the interface went away between the two requests
                raise
            if signal is not None:
                signals[name] = signal
        return signals
