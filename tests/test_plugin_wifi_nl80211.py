#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the wifi plugin nl80211 client (no wireless hardware needed)."""

from __future__ import annotations

import errno
import struct
import sys

import pytest

from glances.plugins.wifi import nl80211 as nl

FAMILY = 28  # nl80211 is a dynamic generic netlink family: any id will do


# ----------------------------------------------------- kernel-like replies


def _msg(msg_type: int, payload: bytes, flags: int = 0) -> bytes:
    return struct.pack("=IHHII", 16 + len(payload), msg_type, flags, 1, 0) + payload + b"\0" * (-len(payload) % 4)


def _genl(cmd: int, *attrs: bytes) -> bytes:
    return _msg(FAMILY, struct.pack("=BBH", cmd, 1, 0) + b"".join(attrs), flags=2)  # NLM_F_MULTI


def _done() -> bytes:
    return _msg(nl.NLMSG_DONE, struct.pack("=i", 0), flags=2)


def _error(code: int) -> bytes:
    return _msg(nl.NLMSG_ERROR, struct.pack("=i", -code) + b"\0" * 16)


def _u32(attr: int, value: int) -> bytes:
    return nl._attr(attr, struct.pack("=I", value))


def _iface(ifindex: int | None, name: str, iftype: int) -> bytes:
    attrs = [nl._attr(nl.NL80211_ATTR_IFNAME, name.encode() + b"\0"), _u32(nl.NL80211_ATTR_IFTYPE, iftype)]
    if ifindex is not None:
        attrs.insert(0, _u32(nl.NL80211_ATTR_IFINDEX, ifindex))
    return _genl(nl.NL80211_CMD_GET_INTERFACE, *attrs)


def _station(signal: int | None) -> bytes:
    inner = b"" if signal is None else nl._attr(nl.NL80211_STA_INFO_SIGNAL, struct.pack("=b", signal))
    # NLA_F_NESTED (0x8000) is set by the kernel on nested attributes
    nested = struct.pack("=HH", 4 + len(inner), nl.NL80211_ATTR_STA_INFO | 0x8000) + inner
    return _genl(nl.NL80211_CMD_GET_STATION, nested)


class FakeKernel:
    """A socket that answers like the kernel, from a per-command script."""

    def __init__(self, interfaces, stations, family_reply=None):
        self.interfaces = interfaces  # list of datagrams (messages) for GET_INTERFACE
        self.stations = stations  # {ifindex: list of datagrams} or {ifindex: OSError code}
        self.family_reply = family_reply
        self.sent: list[tuple[int, int, int, dict]] = []  # (type, flags, cmd, attrs)
        self._queue: list[bytes] = []
        self.timeout = None

    # socket API used by nl80211
    def settimeout(self, value):
        self.timeout = value

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send(self, data):
        _length, msg_type, flags, _seq, _pid = struct.unpack_from("=IHHII", data)
        cmd = data[16]
        attrs = nl._parse_attrs(data[20:])
        self.sent.append((msg_type, flags, cmd, attrs))
        if msg_type == nl.GENL_ID_CTRL:
            self._queue += [self.family_reply if self.family_reply is not None else self._family_ok()]
        elif cmd == nl.NL80211_CMD_GET_INTERFACE:
            self._queue += [b"".join(self.interfaces) + _done()]
        elif cmd == nl.NL80211_CMD_GET_STATION:
            reply = self.stations[nl._u32(attrs[nl.NL80211_ATTR_IFINDEX])]
            self._queue += [_error(reply) if isinstance(reply, int) else b"".join(reply) + _done()]

    def recv(self, _size):
        return self._queue.pop(0)

    @staticmethod
    def _family_ok():
        attrs = nl._attr(nl.CTRL_ATTR_FAMILY_NAME, b"nl80211\0") + nl._attr(
            nl.CTRL_ATTR_FAMILY_ID, struct.pack("=H", FAMILY)
        )
        return _msg(nl.GENL_ID_CTRL, struct.pack("=BBH", 1, 2, 0) + attrs)


@pytest.fixture
def kernel(monkeypatch):
    def install(**kwargs):
        fake = FakeKernel(**kwargs)
        monkeypatch.setattr(nl.socket, "socket", lambda *a, **k: fake)
        return fake

    return install


# ------------------------------------------------------------ pure helpers


def test_attr_is_padded_and_round_trips():
    raw = nl._attr(7, b"abcde") + nl._attr(9, struct.pack("=I", 42))
    assert len(raw) == 12 + 8  # 4+5 padded to 12, then 4+4
    attrs = nl._parse_attrs(raw)
    assert attrs[7] == b"abcde"
    assert nl._u32(attrs[9]) == 42


def test_parse_attrs_masks_nested_flag_and_survives_truncation():
    raw = struct.pack("=HH", 8, 5 | 0x8000) + b"\x01\x02\x03\x04" + struct.pack("=HH", 40, 6) + b"xx"
    assert nl._parse_attrs(raw) == {5: b"\x01\x02\x03\x04"}  # truncated 2nd attribute ignored


def test_u32_rejects_short_or_missing():
    assert nl._u32(None) is None
    assert nl._u32(b"\x01\x02") is None


@pytest.mark.skipif(sys.byteorder != "little", reason="golden bytes are little-endian (netlink uses host order)")
def test_getfamily_request_golden_bytes():
    """The one request that must be byte-exact for any kernel to answer it."""
    request = nl._request(
        nl.GENL_ID_CTRL, nl.CTRL_CMD_GETFAMILY, nl.NLM_F_REQUEST, nl._attr(nl.CTRL_ATTR_FAMILY_NAME, b"nl80211\0")
    )
    nlmsghdr = bytes.fromhex("20000000 1000 0100 01000000 00000000")  # len 32, GENL_ID_CTRL, REQUEST, seq 1, pid 0
    genlmsghdr = bytes.fromhex("03 01 0000")  # CTRL_CMD_GETFAMILY, version 1
    family_name = bytes.fromhex("0c00 0200 6e6c383032313100")  # CTRL_ATTR_FAMILY_NAME = "nl80211\0"
    assert request == nlmsghdr + genlmsghdr + family_name


# ------------------------------------------------------------------ _transact


class _Replies:
    def __init__(self, *datagrams):
        self.datagrams = list(datagrams)
        self.sent = []

    def send(self, data):
        self.sent.append(data)

    def recv(self, _size):
        return self.datagrams.pop(0)


def test_transact_dump_spans_datagrams_until_done():
    sock = _Replies(_iface(3, "a", 2) + _iface(4, "b", 2), _iface(5, "c", 2) + _done())
    replies = nl._transact(sock, b"req", dump=True)
    assert [nl._u32(nl._parse_attrs(p[4:])[nl.NL80211_ATTR_IFINDEX]) for _t, p in replies] == [3, 4, 5]


def test_transact_plain_request_returns_after_first_datagram():
    sock = _Replies(_iface(3, "a", 2), b"must-not-be-read")
    assert len(nl._transact(sock, b"req", dump=False)) == 1
    assert sock.datagrams == [b"must-not-be-read"]


def test_transact_error_reply_raises_oserror():
    with pytest.raises(OSError) as exc:
        nl._transact(_Replies(_error(errno.ENODEV)), b"req", dump=True)
    assert exc.value.errno == errno.ENODEV


def test_transact_ack_is_not_an_error():
    assert nl._transact(_Replies(_msg(nl.NLMSG_ERROR, struct.pack("=i", 0) + b"\0" * 16)), b"req", dump=False) == []


# ----------------------------------------------------------- station_signals


def test_station_signals_reads_associated_station_interfaces(kernel):
    fake = kernel(
        interfaces=[
            _iface(3, "wlan0", nl.NL80211_IFTYPE_STATION),
            _iface(4, "ap0", 3),  # NL80211_IFTYPE_AP: skipped
            _iface(None, "p2p-dev-wlan0", nl.NL80211_IFTYPE_STATION),  # no netdev: skipped
            _iface(5, "wlan1", nl.NL80211_IFTYPE_STATION),  # not associated
            _iface(6, "wlan2", nl.NL80211_IFTYPE_STATION),  # associated, strong signal
        ],
        stations={3: [_station(-52)], 5: [], 6: [_station(-31)]},
    )
    assert nl.station_signals() == {"wlan0": -52, "wlan2": -31}
    assert fake.timeout == nl._TIMEOUT
    # the requests are what the kernel expects: resolve, dump interfaces, dump stations per ifindex
    assert [(t, c) for t, _f, c, _a in fake.sent] == [
        (nl.GENL_ID_CTRL, nl.CTRL_CMD_GETFAMILY),
        (FAMILY, nl.NL80211_CMD_GET_INTERFACE),
        (FAMILY, nl.NL80211_CMD_GET_STATION),
        (FAMILY, nl.NL80211_CMD_GET_STATION),
        (FAMILY, nl.NL80211_CMD_GET_STATION),
    ]
    assert all(f == nl.NLM_F_REQUEST | nl.NLM_F_DUMP for _t, f, c, _a in fake.sent[1:])
    assert [nl._u32(a[nl.NL80211_ATTR_IFINDEX]) for _t, _f, _c, a in fake.sent[2:]] == [3, 5, 6]


def test_station_without_signal_is_left_out(kernel):
    kernel(interfaces=[_iface(3, "wlan0", 2)], stations={3: [_station(None)]})
    assert nl.station_signals() == {}


def test_interface_vanishing_between_requests_is_skipped(kernel):
    kernel(
        interfaces=[_iface(3, "gone0", 2), _iface(4, "wlan0", 2)],
        stations={3: errno.ENODEV, 4: [_station(-60)]},
    )
    assert nl.station_signals() == {"wlan0": -60}


def test_other_station_errors_propagate(kernel):
    kernel(interfaces=[_iface(3, "wlan0", 2)], stations={3: errno.EPERM})
    with pytest.raises(OSError) as exc:
        nl.station_signals()
    assert exc.value.errno == errno.EPERM
    assert not isinstance(exc.value, nl.Nl80211Unavailable)


def test_no_wireless_hardware_is_empty_not_unavailable(kernel):
    kernel(interfaces=[], stations={})
    assert nl.station_signals() == {}


def test_missing_family_is_unavailable(kernel):
    kernel(interfaces=[], stations={}, family_reply=_error(errno.ENOENT))
    with pytest.raises(nl.Nl80211Unavailable):
        nl.station_signals()


def test_family_reply_without_id_is_unavailable(kernel):
    kernel(interfaces=[], stations={}, family_reply=_msg(nl.GENL_ID_CTRL, struct.pack("=BBH", 1, 2, 0)))
    with pytest.raises(nl.Nl80211Unavailable):
        nl.station_signals()


def test_netlink_socket_failure_is_unavailable(monkeypatch):
    def _fail(*_a, **_k):
        raise PermissionError("seccomp")

    monkeypatch.setattr(nl.socket, "socket", _fail)
    with pytest.raises(nl.Nl80211Unavailable):
        nl.station_signals()


def test_platform_without_af_netlink_is_unavailable(monkeypatch):
    monkeypatch.delattr(nl.socket, "AF_NETLINK", raising=False)
    with pytest.raises(nl.Nl80211Unavailable):
        nl.station_signals()
