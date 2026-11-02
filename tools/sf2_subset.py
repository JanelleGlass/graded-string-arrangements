"""Cut a SoundFont (.sf2) down to a few presets and write it as base64 text, the way the site's sounds are kept.

    python tools/sf2_subset.py <GeneralUser-GS.sf2> <out.b64.txt> 0:0 [bank:preset ...]

The piano the reader loads for a score with a Piano part (assets/soundfont/piano-generaluser-sf2.b64.txt) is
GeneralUser GS 2.0.3's Grand Piano, bank 0 preset 0: `python tools/sf2_subset.py GeneralUser-GS.sf2
assets/soundfont/piano-generaluser-sf2.b64.txt 0:0`. The full bank comes from https://github.com/mrbumpy409/GeneralUser-GS
and is not kept here (32 MB). Each kept preset keeps its zones, modulators and generators; its instruments and their
samples (and the samples linked to them as stereo pairs) are copied, renumbered, each followed by the 46 silent sample
points the format asks for. The bank's INFO list (name, author, licence) is kept."""
import base64, struct, sys

def chunks(data, off, end):
    while off < end:
        cid, size = data[off:off + 4], struct.unpack('<I', data[off + 4:off + 8])[0]
        yield cid, off + 8, size
        off += 8 + size + (size & 1)

def riff(cid, body): return cid + struct.pack('<I', len(body)) + body + (b'\0' if len(body) & 1 else b'')
def lst(kind, parts): return riff(b'LIST', kind + b''.join(parts))

SIZE = dict(phdr=38, pbag=4, pmod=10, pgen=4, inst=22, ibag=4, imod=10, igen=4, shdr=46)

def subset(data, keep):
    assert data[:4] == b'RIFF' and data[8:12] == b'sfbk', 'not a SoundFont'
    info = smpl = None; pd = {}
    for cid, o, s in chunks(data, 12, len(data)):
        kind = data[o:o + 4]
        if kind == b'INFO': info = data[o + 4:o + s]
        for c2, o2, s2 in chunks(data, o + 4, o + s):
            if kind == b'sdta' and c2 == b'smpl': smpl = data[o2:o2 + s2]
            if kind == b'sdta' and c2 == b'sm24': raise SystemExit('24-bit samples (sm24) are not handled')
            if kind == b'pdta': pd[c2.decode()] = [data[o2 + k:o2 + k + SIZE[c2.decode()]] for k in range(0, s2, SIZE[c2.decode()])]
    u16 = lambda r, at: struct.unpack('<H', r[at:at + 2])[0]
    phdr, pbag, pmod, pgen = pd['phdr'], pd['pbag'], pd['pmod'], pd['pgen']
    inst, ibag, imod, igen, shdr = pd['inst'], pd['ibag'], pd['imod'], pd['igen'], pd['shdr']
    want = [i for i, r in enumerate(phdr[:-1]) if (u16(r, 22), u16(r, 20)) in keep]
    found = {(u16(phdr[i], 22), u16(phdr[i], 20)) for i in want}
    assert found == set(keep), 'not in the bank: %s' % sorted(set(keep) - found)

    def zones(hdrs, bags, i, at):
        """the bags of header i: [(gens, mods)] as lists of raw records"""
        out = []
        for b in range(u16(hdrs[i], at), u16(hdrs[i + 1], at)):
            g0, m0, g1, m1 = u16(bags[b], 0), u16(bags[b], 2), u16(bags[b + 1], 0), u16(bags[b + 1], 2)
            out.append((list(range(g0, g1)), list(range(m0, m1))))
        return out

    # instruments used by the kept presets, and the samples they use (stereo partners too)
    insts, samples = [], []
    for i in want:
        for gens, _ in zones(phdr, pbag, i, 24):
            for g in gens:
                if u16(pgen[g], 0) == 41 and u16(pgen[g], 2) not in insts: insts.append(u16(pgen[g], 2))
    for i in insts:
        for gens, _ in zones(inst, ibag, i, 20):
            for g in gens:
                if u16(igen[g], 0) == 53 and u16(igen[g], 2) not in samples: samples.append(u16(igen[g], 2))
    k = 0
    while k < len(samples):
        r = shdr[samples[k]]
        if u16(r, 44) & 0x7FFF in (2, 4, 8) and u16(r, 42) not in samples: samples.append(u16(r, 42))
        k += 1

    # sample data: each sample copied with its 46 silent points
    newsmpl, newshdr, at = bytearray(), [], 0
    for s in samples:
        r = shdr[s]
        start, end, ls, le = struct.unpack('<IIII', r[20:36])
        newsmpl += smpl[2 * start:2 * end] + b'\0' * 92
        link = u16(r, 42)
        newshdr.append(r[:20] + struct.pack('<IIII', at, at + end - start, at + ls - start, at + le - start) + r[36:42]
                       + struct.pack('<H', samples.index(link) if u16(r, 44) & 0x7FFF in (2, 4, 8) else 0) + r[44:46])
        at += end - start + 46
    newshdr.append(b'EOS'.ljust(20, b'\0') + b'\0' * 26)

    def rebuild(hdrs, bags, gens_all, mods_all, idx_list, at, name_end, hdr_size, remap_oper, remap):
        H, B, G, M = [], [], [], []
        for i in idx_list:
            H.append(hdrs[i][:at] + struct.pack('<H', len(B)) + hdrs[i][at + 2:])
            for gens, mods in zones(hdrs, bags, i, at):
                B.append(struct.pack('<HH', len(G), len(M)))
                for g in gens:
                    r = gens_all[g]
                    G.append(r[:2] + struct.pack('<H', remap[u16(r, 2)]) if u16(r, 0) == remap_oper else r)
                M.extend(mods_all[m] for m in mods)
        H.append(name_end.ljust(20, b'\0') + b'\0' * (at - 20) + struct.pack('<H', len(B)) + b'\0' * (hdr_size - at - 2))
        B.append(struct.pack('<HH', len(G), len(M)))
        G.append(b'\0' * 4); M.append(b'\0' * 10)
        return H, B, G, M

    P = rebuild(phdr, pbag, pgen, pmod, want, 24, b'EOP', 38, 41, {o: n for n, o in enumerate(insts)})
    I = rebuild(inst, ibag, igen, imod, insts, 20, b'EOI', 22, 53, {o: n for n, o in enumerate(samples)})
    (ph, pb, pg, pm), (ih, ib, ig, im) = P, I       # written in the format's order: headers, bags, modulators, generators
    pdta = [riff(n, b''.join(v)) for n, v in ((b'phdr', ph), (b'pbag', pb), (b'pmod', pm), (b'pgen', pg),
                                              (b'inst', ih), (b'ibag', ib), (b'imod', im), (b'igen', ig), (b'shdr', newshdr))]
    body = b'sfbk' + lst(b'INFO', [info]) + lst(b'sdta', [riff(b'smpl', bytes(newsmpl))]) + lst(b'pdta', pdta)
    return riff(b'RIFF', body), [phdr[i][:20].split(b'\0')[0].decode('latin1') for i in want], len(insts), len(samples)

if __name__ == '__main__':
    src, out, *specs = sys.argv[1:]
    keep = [tuple(int(x) for x in s.split(':')) for s in specs]
    sf2, names, ni, ns = subset(open(src, 'rb').read(), keep)
    open(out, 'wb').write(base64.b64encode(sf2))
    print('%s: %s; %d instrument(s), %d sample(s); %.1f MB (%.1f MB as text)' % (out, ', '.join(names), ni, ns, len(sf2) / 1e6, len(sf2) * 4 / 3 / 1e6))
