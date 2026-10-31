"""Summarize the simulator's little-endian Ethernet PCAP without dependencies."""
import collections
import struct


def summarize_capture(path):
    frames = []
    with path.open('rb') as capture:
        header = capture.read(24)
        if len(header) != 24 or header[:4] != bytes.fromhex('d4c3b2a1') or struct.unpack_from('<I', header, 20)[0] != 1:
            raise ValueError('Expected little-endian Ethernet PCAP')
        while record := capture.read(16):
            if len(record) != 16:
                raise ValueError('Truncated PCAP record')
            _, _, size, original = struct.unpack('<IIII', record)
            if size > 65535 or size > original:
                raise ValueError('Invalid PCAP frame length')
            frame = capture.read(size)
            if len(frame) != size:
                raise ValueError('Truncated PCAP frame')
            frames.append(frame)
    station = bytes.fromhex('029000000001')
    arp_replies = echo_replies = lat_multicasts = 0
    for frame in frames:
        if len(frame) < 14 or frame[6:12] != station:
            continue
        kind = frame[12:14]
        if kind == b'\x08\x06' and len(frame) >= 22 and frame[20:22] == b'\x00\x02':
            arp_replies += 1
        if kind == b'\x60\x04' and frame[0] & 1:
            lat_multicasts += 1
        if kind == b'\x08\x00' and len(frame) >= 34 and frame[23] == 1:
            offset = 14 + (frame[14] & 15) * 4
            if len(frame) > offset and frame[offset] == 0:
                echo_replies += 1
    return dict(captured_frames=len(frames),
                ether_types=dict(collections.Counter(frame[12:14].hex() for frame in frames if len(frame) >= 14)),
                station_mac_seen=any(frame[6:12] == station for frame in frames),
                station_arp_replies=arp_replies, station_icmp_echo_replies=echo_replies,
                station_lat_multicasts=lat_multicasts)
