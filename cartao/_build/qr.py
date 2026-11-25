"""QR Code encoder (byte mode, EC level M, versions 1-6) + reader used to verify output.

No third-party dependency besides Pillow (used only to rasterise).
"""
from __future__ import annotations

# ---------------------------------------------------------------- GF(256)
EXP = [0] * 512
LOG = [0] * 256
_x = 1
for _i in range(255):
    EXP[_i] = _x
    LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    EXP[_i] = EXP[_i - 255]


def gmul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return EXP[LOG[a] + LOG[b]]


# EC level M: version -> (ec_codewords_per_block, [(block_count, data_codewords), ...])
EC_M = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
}
EC_LEVEL_M_BITS = 0b00


def _rs_generator(n: int) -> list[int]:
    g = [1]
    for i in range(n):
        ng = [0] * (len(g) + 1)
        for j, coef in enumerate(g):
            ng[j] ^= coef
            ng[j + 1] ^= gmul(coef, EXP[i])
        g = ng
    return g


def rs_ec(data: bytes, ec_len: int) -> bytes:
    gen = _rs_generator(ec_len)
    rem = [0] * ec_len
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        if factor:
            for j in range(ec_len):
                rem[j] ^= gmul(gen[j + 1], factor)
    return bytes(rem)


# ---------------------------------------------------------------- bit stream
def encode_payload(text: str, version: int | None = None) -> tuple[int, list[int], list[bytes]]:
    """Return (version, interleaved codewords, block list)."""
    data = text.encode("utf-8")
    if version is None:
        for v in range(1, 7):
            ec_len, groups = EC_M[v]
            capacity = sum(b * d for b, d in groups)
            if 4 + 8 + 8 * len(data) <= capacity * 8:
                version = v
                break
        if version is None:
            raise ValueError(f"payload too long for versions 1-6: {len(data)} bytes")

    ec_len, groups = EC_M[version]
    capacity = sum(b * d for b, d in groups)

    bits = [0, 1, 0, 0]  # byte mode
    count_bits = 8  # versions 1-9
    for i in range(count_bits - 1, -1, -1):
        bits.append((len(data) >> i) & 1)
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    for _ in range(min(4, capacity * 8 - len(bits))):
        bits.append(0)
    while len(bits) % 8:
        bits.append(0)
    codewords = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pads = [0xEC, 0x11]
    i = 0
    while len(codewords) < capacity:
        codewords.append(pads[i % 2])
        i += 1

    blocks: list[bytes] = []
    pos = 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(bytes(codewords[pos:pos + size]))
            pos += size
    ecs = [rs_ec(b, ec_len) for b in blocks]

    out: list[int] = []
    for i in range(max(len(b) for b in blocks)):
        for b in blocks:
            if i < len(b):
                out.append(b[i])
    for i in range(ec_len):
        for e in ecs:
            out.append(e[i])
    return version, out, blocks


# ---------------------------------------------------------------- matrix
def _new_matrix(n: int) -> list[list[bool | None]]:
    return [[None] * n for _ in range(n)]


def _probe(m, row: int, col: int) -> None:
    n = len(m)
    for r in range(-1, 8):
        for c in range(-1, 8):
            rr, cc = row + r, col + c
            if 0 <= rr < n and 0 <= cc < n:
                inside = 0 <= r <= 6 and 0 <= c <= 6
                edge = r in (0, 6) or c in (0, 6)
                core = 2 <= r <= 4 and 2 <= c <= 4
                m[rr][cc] = bool(inside and (edge or core))


def _reserve_probe(m, row: int, col: int) -> None:
    n = len(m)
    for r in range(-1, 8):
        for c in range(-1, 8):
            rr, cc = row + r, col + c
            if 0 <= rr < n and 0 <= cc < n:
                m[rr][cc] = True


def _reserved(n: int, version: int) -> list[list[bool]]:
    """Cells that belong to function patterns (never carry data)."""
    m = [[False] * n for _ in range(n)]
    _reserve_probe(m, 0, 0)
    _reserve_probe(m, 0, n - 7)
    _reserve_probe(m, n - 7, 0)
    for i in range(8, n - 8):
        m[6][i] = True
        m[i][6] = True
    if version >= 2:
        for r in range(n - 9, n - 4):
            for c in range(n - 9, n - 4):
                m[r][c] = True
    for i in range(15):
        if i < 6:
            m[i][8] = True
        elif i < 8:
            m[i + 1][8] = True
        else:
            m[n - 15 + i][8] = True
        if i < 8:
            m[8][n - i - 1] = True
        elif i < 9:
            m[8][15 - i] = True
        else:
            m[8][15 - i - 1] = True
    m[n - 8][8] = True
    return m


def _alignment(m, row: int, col: int) -> None:
    n = len(m)
    for r in range(-2, 3):
        for c in range(-2, 3):
            rr, cc = row + r, col + c
            if 0 <= rr < n and 0 <= cc < n and m[rr][cc] is None:
                m[rr][cc] = max(abs(r), abs(c)) != 1


def _format_bits(mask: int) -> int:
    data = (EC_LEVEL_M_BITS << 3) | mask
    d = data << 10
    while d.bit_length() >= 0x537.bit_length():
        d ^= 0x537 << (d.bit_length() - 0x537.bit_length())
    return ((data << 10) | d) ^ 0x5412


def _place_format(m, mask: int, real: bool = True) -> None:
    n = len(m)
    bits = _format_bits(mask)
    for i in range(15):
        mod = bool((bits >> i) & 1) if real else False
        if i < 6:
            m[i][8] = mod
        elif i < 8:
            m[i + 1][8] = mod
        else:
            m[n - 15 + i][8] = mod
        if i < 8:
            m[8][n - i - 1] = mod
        elif i < 9:
            m[8][15 - i - 1 + 1] = mod
        else:
            m[8][15 - i - 1] = mod
    m[n - 8][8] = True


def _mask_fn(mask: int, i: int, j: int) -> bool:
    if mask == 0:
        return (i + j) % 2 == 0
    if mask == 1:
        return i % 2 == 0
    if mask == 2:
        return j % 3 == 0
    if mask == 3:
        return (i + j) % 3 == 0
    if mask == 4:
        return (i // 2 + j // 3) % 2 == 0
    if mask == 5:
        return (i * j) % 2 + (i * j) % 3 == 0
    if mask == 6:
        return ((i * j) % 2 + (i * j) % 3) % 2 == 0
    return ((i * j) % 3 + (i + j) % 2) % 2 == 0


def _map_data(m, codewords: list[int], mask: int, reserved: list[list[bool]]) -> None:
    n = len(m)
    inc = -1
    row = n - 1
    bit_index = 7
    byte_index = 0
    col = n - 1
    while col > 0:
        if col == 6:
            col -= 1
        while True:
            for c in (0, 1):
                cc = col - c
                if not reserved[row][cc]:
                    dark = False
                    if byte_index < len(codewords):
                        dark = bool((codewords[byte_index] >> bit_index) & 1)
                    if _mask_fn(mask, row, cc):
                        dark = not dark
                    m[row][cc] = dark
                    bit_index -= 1
                    if bit_index == -1:
                        byte_index += 1
                        bit_index = 7
            row += inc
            if row < 0 or row >= n:
                row -= inc
                inc = -inc
                break
        col -= 2


def _penalty(m) -> int:
    n = len(m)
    score = 0
    for line in list(m) + [list(col) for col in zip(*m)]:
        run = 1
        for i in range(1, n):
            if line[i] == line[i - 1]:
                run += 1
            else:
                if run >= 5:
                    score += 3 + run - 5
                run = 1
        if run >= 5:
            score += 3 + run - 5
        s = "".join("1" if v else "0" for v in line)
        for pat in ("10111010000", "00001011101"):
            start = 0
            while True:
                idx = s.find(pat, start)
                if idx < 0:
                    break
                score += 40
                start = idx + 1
    for r in range(n - 1):
        for c in range(n - 1):
            v = m[r][c]
            if v == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                score += 3
    total = n * n
    dark = sum(1 for row in m for v in row if v)
    ratio = dark * 100 / total
    score += int(abs(ratio - 50) / 5) * 10
    return score


def build(text: str) -> tuple[int, list[list[bool]]]:
    version, codewords, _ = encode_payload(text)
    n = 17 + 4 * version
    reserved = _reserved(n, version)
    m = _new_matrix(n)

    _probe(m, 0, 0)
    _probe(m, 0, n - 7)
    _probe(m, n - 7, 0)
    for i in range(8, n - 8):
        if m[6][i] is None:
            m[6][i] = i % 2 == 0
        if m[i][6] is None:
            m[i][6] = i % 2 == 0
    if version >= 2:
        _alignment(m, n - 7, n - 7)
    _place_format(m, 0, real=False)
    _place_format(m, 0, real=True)

    best = None
    for mask in range(8):
        trial = [row[:] for row in m]
        _map_data(trial, codewords, mask, reserved)
        _place_format(trial, mask, real=True)
        p = _penalty(trial)
        if best is None or p < best[0]:
            best = (p, mask, trial)
    _, mask, matrix = best
    return version, [[bool(v) for v in row] for row in matrix]


# ---------------------------------------------------------------- readers
def decode_matrix(matrix: list[list[bool]]) -> str:
    """Independent-ish reader: format info, unmask, zig-zag scan, RS syndrome check."""
    n = len(matrix)
    version = (n - 17) // 4
    ec_len, groups = EC_M[version]

    fmt_a = 0
    for i in range(15):
        if i < 6:
            bit = matrix[i][8]
        elif i < 8:
            bit = matrix[i + 1][8]
        else:
            bit = matrix[n - 15 + i][8]
        fmt_a |= int(bit) << i

    mask = None
    for cand in range(8):
        if _format_bits(cand) == fmt_a:
            mask = cand
            break
    if mask is None:
        raise ValueError(f"format info unreadable: {fmt_a:015b}")

    func = _reserved(n, version)
    bits: list[int] = []
    row, col, inc = n - 1, n - 1, -1
    while col > 0:
        if col == 6:
            col -= 1
        while True:
            for c in (0, 1):
                cc = col - c
                if not func[row][cc]:
                    dark = matrix[row][cc]
                    if _mask_fn(mask, row, cc):
                        dark = not dark
                    bits.append(1 if dark else 0)
            row += inc
            if row < 0 or row >= n:
                row -= inc
                inc = -inc
                break
        col -= 2

    total_cw = sum(b * d for b, d in groups) + ec_len * sum(b for b, _ in groups)
    words = []
    for i in range(total_cw):
        chunk = bits[i * 8:(i + 1) * 8]
        if len(chunk) < 8:
            break
        words.append(int("".join(map(str, chunk)), 2))

    nblocks = sum(b for b, _ in groups)
    sizes = []
    for count, size in groups:
        sizes += [size] * count
    data_words = [[] for _ in range(nblocks)]
    ec_words = [[] for _ in range(nblocks)]
    idx = 0
    for i in range(max(sizes)):
        for b in range(nblocks):
            if i < sizes[b]:
                data_words[b].append(words[idx])
                idx += 1
    for i in range(ec_len):
        for b in range(nblocks):
            ec_words[b].append(words[idx])
            idx += 1

    for b in range(nblocks):
        codeword = data_words[b] + ec_words[b]
        if _syndromes(codeword, ec_len) != [0] * ec_len:
            raise ValueError(f"RS check failed on block {b}")

    stream = [w for b in data_words for w in b]
    allbits = []
    for w in stream:
        allbits += [(w >> i) & 1 for i in range(7, -1, -1)]
    mode = int("".join(map(str, allbits[:4])), 2)
    if mode != 4:
        raise ValueError(f"unexpected mode {mode}")
    count = int("".join(map(str, allbits[4:12])), 2)
    payload = allbits[12:12 + count * 8]
    data = bytes(int("".join(map(str, payload[i:i + 8])), 2) for i in range(0, len(payload), 8))
    return data.decode("utf-8")


def _syndromes(codeword: list[int], ec_len: int) -> list[int]:
    out = []
    for i in range(ec_len):
        acc = 0
        for c in codeword:
            acc = gmul(acc, EXP[i]) ^ c
        out.append(acc)
    return out


def _function_mask(n: int, version: int) -> list[list[bool]]:
    m = _new_matrix(n)
    _probe(m, 0, 0)
    _probe(m, 0, n - 7)
    _probe(m, n - 7, 0)
    for i in range(8, n - 8):
        m[6][i] = True
        m[i][6] = True
    if version >= 2:
        _alignment(m, n - 7, n - 7)
    _place_format(m, 0, real=False)
    return [[bool(v) for v in row] for row in m]


# ---------------------------------------------------------------- render
def to_svg(matrix: list[list[bool]], quiet: int = 4, dark: str = "#10233c", light: str = "#ffffff") -> str:
    n = len(matrix)
    size = n + quiet * 2
    path = []
    for r, row in enumerate(matrix):
        run = None
        for c in range(n + 1):
            dark_px = c < n and row[c]
            if dark_px and run is None:
                run = c
            elif not dark_px and run is not None:
                path.append(f"M{run + quiet} {r + quiet}h{c - run}v1h-{c - run}z")
                run = None
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'shape-rendering="crispEdges" role="img" aria-label="QR code">'
        f'<rect width="{size}" height="{size}" fill="{light}"/>'
        f'<path d="{"".join(path)}" fill="{dark}"/></svg>'
    )


def to_png(matrix: list[list[bool]], path: str, scale: int = 12, quiet: int = 4) -> None:
    from PIL import Image
    n = len(matrix)
    size = (n + quiet * 2) * scale
    img = Image.new("RGB", (size, size), "white")
    px = img.load()
    for r, row in enumerate(matrix):
        for c, dark in enumerate(row):
            if dark:
                x0 = (c + quiet) * scale
                y0 = (r + quiet) * scale
                for y in range(y0, y0 + scale):
                    for x in range(x0, x0 + scale):
                        px[x, y] = (16, 35, 60)
    img.save(path)
