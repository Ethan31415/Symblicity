from pathlib import Path
import math
import random
import struct
import subprocess
import sys
import wave

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "_site/audio")
OUT.mkdir(parents=True, exist_ok=True)
SR = 22050

def write_wav(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        data = bytearray()
        for x in samples:
            x = max(-1.0, min(1.0, x))
            data += struct.pack("<h", int(x * 32767))
        w.writeframes(data)

def env(i, n, attack=0.01, release=0.05):
    a = max(1, int(SR * attack))
    r = max(1, int(SR * release))
    if i < a:
        return i / a
    if i > n - r:
        return max(0, (n - i) / r)
    return 1.0

def tone(freq, dur, vol=.35, kind="sine"):
    n = int(SR * dur)
    out = []
    for i in range(n):
        ph = (i * freq / SR) % 1.0
        if kind == "square":
            v = 1 if ph < .5 else -1
        elif kind == "triangle":
            v = 4 * abs(ph - .5) - 1
        else:
            v = math.sin(2 * math.pi * ph)
        out.append(v * vol * env(i, n, min(.01, dur / 6), min(.05, dur / 4)))
    return out

def mix(parts):
    n = max(map(len, parts))
    out = [0.0] * n
    for p in parts:
        for i, v in enumerate(p):
            out[i] += v
    return out

def cat(*parts):
    out = []
    for p in parts:
        out.extend(p)
    return out

# Keep this generator in lockstep with the native Battleship package.
nav = mix([tone(880, .08, .32, "square"), tone(1320, .08, .18, "sine")])
sel = cat(tone(660, .08, .34, "triangle"), tone(990, .13, .38, "triangle"))

rng = random.Random(31415)
n = int(SR * .19)
hit = []
for i in range(n):
    t = i / SR
    fall = 1 - i / n
    thud = math.sin(2 * math.pi * (150 - 70 * t) * t) * .42
    noise = (rng.random() * 2 - 1) * .30
    hit.append((thud + noise) * fall)

n = int(SR * .72)
sunk = []
rng = random.Random(2718)
for i in range(n):
    t = i / SR
    fall = (1 - i / n) ** 1.4
    freq = 420 - 300 * (i / n)
    sig = math.sin(2 * math.pi * freq * t) * .34
    rum = math.sin(2 * math.pi * 70 * t) * .28
    noise = (rng.random() * 2 - 1) * .10
    sunk.append((sig + rum + noise) * fall)

notes = {
    "C3": 130.81, "Eb3": 155.56, "G3": 196.00, "Bb3": 233.08,
    "C4": 261.63, "Eb4": 311.13, "G4": 392.00, "Bb4": 466.16,
    "D4": 293.66, "F4": 349.23, "Ab4": 415.30,
}
phrase = [
    ("C3", "C4", "Eb4", "G4"),
    ("Ab4", "G4", "Eb4", "C4"),
    ("Bb3", "D4", "F4", "Bb4"),
    ("G3", "Bb3", "D4", "G4"),
]
step = .25
bg = []
while len(bg) < SR * 180:
    for bass, *arp in phrase:
        for j in range(8):
            freq = notes[arp[j % len(arp)]]
            lead = tone(freq, step, .13, "triangle")
            bass_tone = tone(notes[bass], step, .10, "square")
            bg.extend(mix([lead, bass_tone]))
            if len(bg) >= SR * 180:
                break
        if len(bg) >= SR * 180:
            break
bg = bg[:SR * 180]
fade = int(SR * .4)
for i in range(fade):
    bg[i] *= i / fade
    bg[-1 - i] *= i / fade

assets = {
    "00_background": bg,
    "01_menu_nav": nav,
    "02_menu_select": sel,
    "03_hit": hit,
    "04_sunk": sunk,
}

for name, samples in assets.items():
    wav = OUT / (name + ".wav")
    ogg = OUT / (name + ".ogg")
    write_wav(wav, samples)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
         "-c:a", "libvorbis", "-q:a", "4", str(ogg)],
        check=True,
    )
    wav.unlink()
    print(name + ".ogg", ogg.stat().st_size)
