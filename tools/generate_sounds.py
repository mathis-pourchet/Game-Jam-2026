#!/usr/bin/env python3
"""Générateur procédural des effets sonores et musiques du jeu (style chiptune NES).

Utilisation (depuis la racine du dépôt) :
    .venv/bin/python tools/generate_sounds.py

Les fichiers .wav (PCM 16 bits, mono, 22050 Hz) sont écrits dans assets/sounds/.
Ils peuvent être remplacés à tout moment par de vrais sons, à condition de
garder exactement les mêmes noms de fichiers.
Les fichiers music_*.wav sont des boucles parfaites (nombre entier de mesures).
Bibliothèque standard uniquement : aucune dépendance externe.
"""
import math
import random
import sys
import wave
from array import array
from pathlib import Path

SR = 22050
TWO_PI = 2.0 * math.pi
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"
SFX_PEAK = 0.8
MUSIC_PEAK = 0.6

random.seed(2026)

# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------
_NOTE_INDEX = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def note_midi(name):
    """'A4' -> 69. Accepte dièses et bémols ('F#4', 'Bb3')."""
    semi = _NOTE_INDEX[name[0].upper()]
    rest = name[1:]
    while rest and rest[0] in "#b":
        semi += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + semi


def midi_name(midi):
    return _SHARP_NAMES[midi % 12] + str(midi // 12 - 1)


def note_freq(name):
    """'A4' -> 440.0 ; un nombre est renvoyé tel quel (Hz)."""
    if not isinstance(name, str):
        return float(name)
    return 440.0 * 2.0 ** ((note_midi(name) - 69) / 12.0)


def transpose(name, semitones):
    return midi_name(note_midi(name) + semitones)


# ---------------------------------------------------------------------------
# Synthèse de base
# ---------------------------------------------------------------------------
_WAVES = {"square": 0, "triangle": 1, "saw": 2, "sine": 3}


def _blep(t, dt):
    # PolyBLEP : adoucit les fronts des ondes carrées/scie (moins d'aliasing)
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    if t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


def osc(freq, n, wave="square", duty=0.5, freq_end=None, vib=0.0, vib_rate=6.0, vib_delay=0.0):
    """Oscillateur brut de n échantillons.

    freq : Hz, ou fonction t -> Hz (contours libres).
    freq_end : glissando exponentiel jusqu'à cette fréquence.
    vib : profondeur du vibrato en demi-tons.
    """
    out = [0.0] * n
    w = _WAVES[wave]
    dur = n / SR
    if callable(freq):
        fn = freq
    elif freq_end is not None:
        f0, ratio = freq, freq_end / freq
        fn = lambda t: f0 * ratio ** (t / dur)
    else:
        fn = None
    f = freq if fn is None else 0.0
    dc = 2.0 * duty - 1.0
    inv = 1.0 / SR
    phase = 0.0
    dynamic = fn is not None or vib
    dt = f * inv
    for i in range(n):
        if dynamic:
            t = i * inv
            f = fn(t) if fn is not None else freq
            if vib and t > vib_delay:
                f *= 2.0 ** (vib * math.sin(TWO_PI * vib_rate * (t - vib_delay)) / 12.0)
            dt = f * inv
        if w == 0:
            s = (1.0 if phase < duty else -1.0) - dc
            if dt > 0.0:
                p2 = phase - duty
                if p2 < 0.0:
                    p2 += 1.0
                s += _blep(phase, dt) - _blep(p2, dt)
        elif w == 1:
            # triangle NES quantifié sur 16 niveaux
            s = int((2.0 - 4.0 * abs(phase - 0.5)) * 7.999) / 7.5 - 1.0
        elif w == 2:
            s = 2.0 * phase - 1.0
            if dt > 0.0:
                s -= _blep(phase, dt)
        else:
            s = math.sin(TWO_PI * phase)
        out[i] = s
        phase += dt
        if phase >= 1.0:
            phase -= int(phase)
    return out


def envelope(n, attack=0.005, decay=0.0, sustain=1.0, release=0.01, curve=None):
    """ADSR (secondes). curve : constante de temps d'une décroissance exponentielle.
    Le premier et le dernier échantillon valent 0 (pas de clic)."""
    a = max(1, int(attack * SR))
    d = int(decay * SR)
    r = max(1, int(release * SR))
    k = -1.0 / (curve * SR) if curve else 0.0
    env = [0.0] * n
    for i in range(n):
        if i < a:
            e = i / a
        elif i < a + d:
            e = 1.0 - (1.0 - sustain) * (i - a) / d
        else:
            e = sustain
        if k:
            e *= math.exp(k * i)
        j = n - 1 - i
        if j < r:
            e *= j / r
        env[i] = e
    return env


def tone(freq, dur, wave="square", duty=0.5, vol=1.0, attack=0.005, decay=0.0,
         sustain=1.0, release=0.01, curve=None, freq_end=None, **kw):
    """Note enveloppée. freq / freq_end acceptent un nom de note ('C5') ou des Hz."""
    if not callable(freq):
        freq = note_freq(freq)
    if freq_end is not None:
        freq_end = note_freq(freq_end)
    n = int(dur * SR)
    sig = osc(freq, n, wave, duty, freq_end=freq_end, **kw)
    env = envelope(n, attack, decay, sustain, release, curve)
    return [s * e * vol for s, e in zip(sig, env)]


def noise(dur, vol=1.0, hold=SR, hold_end=None, attack=0.002, decay=0.0, sustain=1.0,
          release=0.01, curve=None, lowpass_hz=None, highpass_hz=None):
    """Bruit façon canal NES : valeur aléatoire renouvelée 'hold' fois par seconde
    (hold bas = bruit grave et granuleux)."""
    n = int(dur * SR)
    out = [0.0] * n
    acc, v = 1.0, 0.0
    for i in range(n):
        h = hold if hold_end is None else hold * (hold_end / hold) ** (i / n)
        acc += h / SR
        if acc >= 1.0:
            acc -= int(acc)
            v = random.uniform(-1.0, 1.0)
        out[i] = v
    if lowpass_hz:
        out = lowpass(out, lowpass_hz)
    if highpass_hz:
        out = highpass(out, highpass_hz)
    env = envelope(n, attack, decay, sustain, release, curve)
    return [s * e * vol for s, e in zip(out, env)]


def lowpass(buf, cutoff, passes=1):
    """Passe-bas 1 pôle ; cutoff en Hz ou fonction t -> Hz."""
    for _ in range(passes):
        out = [0.0] * len(buf)
        y = 0.0
        if callable(cutoff):
            for i, x in enumerate(buf):
                a = 1.0 - math.exp(-TWO_PI * cutoff(i / SR) / SR)
                y += a * (x - y)
                out[i] = y
        else:
            a = 1.0 - math.exp(-TWO_PI * cutoff / SR)
            for i, x in enumerate(buf):
                y += a * (x - y)
                out[i] = y
        buf = out
    return buf


def highpass(buf, cutoff):
    return [x - l for x, l in zip(buf, lowpass(buf, cutoff))]


# ---------------------------------------------------------------------------
# Mixage
# ---------------------------------------------------------------------------
def silence(dur):
    return [0.0] * int(round(dur * SR))


def concat(*bufs):
    out = []
    for b in bufs:
        out.extend(b)
    return out


def mix_into(dst, src, start=0, gain=1.0, wrap=False):
    """Ajoute src dans dst à partir de l'échantillon start.
    wrap=True : ce qui dépasse revient au début (boucles musicales)."""
    n = len(dst)
    start = int(start)
    if wrap:
        start %= n
    end = start + len(src)
    if end <= n:
        dst[start:end] = [d + s * gain for d, s in zip(dst[start:end], src)]
        return
    k = n - start
    if k > 0:
        dst[start:] = [d + s * gain for d, s in zip(dst[start:], src[:k])]
    if wrap:
        mix_into(dst, src[k:], 0, gain, wrap=True)


def place(dst, src, t, gain=1.0):
    """Comme mix_into mais position en secondes."""
    mix_into(dst, src, int(round(t * SR)), gain)


def peak(buf):
    return max((abs(x) for x in buf), default=0.0)


def normalize(buf, target=1.0):
    m = peak(buf)
    if m == 0.0:
        return buf[:]
    g = target / m
    return [x * g for x in buf]


def drive(buf, amount=2.0):
    """Saturation douce (tanh) pour épaissir les impacts."""
    buf = normalize(buf)
    k = math.tanh(amount)
    return [math.tanh(amount * x) / k for x in buf]


def echo(buf, delay, feedback=0.35, repeats=2, wrap=True):
    """Écho ; en mode wrap la queue revient au début (boucle sans coupure)."""
    d = int(round(delay * SR))
    out = buf[:]
    n = len(buf)
    for r in range(1, repeats + 1):
        g = feedback ** r
        s = (d * r) % n
        if wrap:
            shifted = buf[-s:] + buf[:-s] if s else buf
        else:
            shifted = [0.0] * min(s, n) + buf[: max(0, n - s)]
        out = [o + g * x for o, x in zip(out, shifted)]
    return out


def write_wav(path, buf, target_peak):
    buf = normalize(buf, target_peak)
    data = array("h", (int(round(max(-1.0, min(1.0, x)) * 32767)) for x in buf))
    if sys.byteorder == "big":
        data.byteswap()
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())
    return len(buf) / SR, path.stat().st_size


# ---------------------------------------------------------------------------
# Effets sonores
# ---------------------------------------------------------------------------
def sfx_jump():
    a = tone(250, 0.18, "square", duty=0.25, freq_end=900, attack=0.003, release=0.05, curve=0.2)
    b = tone(125, 0.18, "triangle", freq_end=450, vol=0.4, attack=0.003, release=0.05, curve=0.15)
    out = silence(0.18)
    place(out, a, 0)
    place(out, b, 0)
    return out


def sfx_coin():
    a = tone("B5", 0.075, "square", duty=0.5, attack=0.002, release=0.006)
    b = tone("E6", 0.225, "square", duty=0.5, attack=0.002, release=0.06, curve=0.1)
    return concat(a, b)


def sfx_sword():
    d = 0.15
    sw = noise(d, hold=SR, attack=0.035, release=0.1)
    sw = lowpass(sw, lambda t: 900 + 6500 * math.sin(math.pi * min(1.0, t / d)), passes=2)
    sw = highpass(sw, 600)
    sw = normalize(sw)
    ping = tone(2600, 0.07, "square", duty=0.125, freq_end=3800, attack=0.003, release=0.04)
    out = silence(d)
    place(out, sw, 0)
    place(out, ping, 0.02, 0.12)
    return out


def sfx_hit():
    d = 0.15
    out = silence(d)
    place(out, tone(lambda t: 50 + 190 * math.exp(-t * 30), d, "sine",
                    attack=0.001, release=0.03, curve=0.06), 0, 1.0)
    place(out, noise(0.08, hold=3500, attack=0.001, release=0.02, curve=0.025), 0, 0.7)
    place(out, tone(150, 0.06, "square", duty=0.5, freq_end=70, attack=0.001, release=0.02), 0, 0.35)
    return drive(out, 2.0)


def sfx_stomp():
    d = 0.15
    out = silence(d)
    place(out, tone(620, d, "square", duty=0.5, freq_end=110, vib=1.5, vib_rate=35,
                    attack=0.002, release=0.04, curve=0.1), 0)
    place(out, noise(0.05, hold=1500, attack=0.001, release=0.02, curve=0.02, lowpass_hz=1500), 0, 0.5)
    return out


def sfx_hurt():
    d = 0.3
    out = silence(d)
    place(out, tone(700, d, "square", duty=0.125, freq_end=160, vib=1.0, vib_rate=28,
                    attack=0.003, release=0.07), 0, 1.0)
    place(out, tone(710, d, "square", duty=0.5, freq_end=150, vib=1.0, vib_rate=28,
                    attack=0.003, release=0.07), 0, 0.6)
    place(out, noise(0.08, hold=4000, attack=0.001, release=0.03, curve=0.04), 0, 0.3)
    return drive(out, 1.5)


def _wah_note(note, dur, final=False):
    """Une note 'wah' de trombone triste : filtre qui s'ouvre puis se ferme."""
    f0 = note_freq(note)
    vib_start = 0.14

    def pitch(t):
        x = t / dur
        if final:
            fr = f0 * 2.0 ** (-1.2 * max(0.0, x - 0.55) / 0.45 / 12.0)
            if t > vib_start:
                fr *= 2.0 ** (0.55 * math.sin(TWO_PI * 5.5 * (t - vib_start)) / 12.0)
            return fr
        return f0 * 2.0 ** (-0.7 * max(0.0, x - 0.6) / 0.4 / 12.0)

    def cutoff(t):
        x = t / dur
        if final:
            # le "wah-wah" suit le vibrato et se referme doucement
            wob = 0.5 + 0.5 * math.sin(TWO_PI * 5.5 * max(0.0, t - vib_start) - math.pi / 2)
            if t < vib_start:
                wob = min(1.0, t / vib_start)
            return 400 + 2600 * wob * max(0.25, 1.0 - 0.7 * x)
        return 350 + 2800 * math.sin(math.pi * min(1.0, x)) ** 1.5

    rel = 0.3 if final else 0.05
    lead = tone(pitch, dur, "square", duty=0.5, attack=0.02, release=rel)
    lead = lowpass(lead, cutoff, passes=2)
    lead = normalize(lead)
    body = tone(lambda t: pitch(t) / 2, dur, "triangle", attack=0.02, release=rel)
    out = [a + 0.45 * b for a, b in zip(lead, body)]
    return out


def sfx_death():
    out = silence(1.8)
    notes = [("G4", 0.0, 0.33), ("F#4", 0.36, 0.33), ("F4", 0.72, 0.33)]
    for name, t, d in notes:
        place(out, _wah_note(name, d), t)
    place(out, _wah_note("E4", 0.72, final=True), 1.08)
    return out


def sfx_rebirth():
    d = 1.6
    out = silence(d)
    # montée grave
    place(out, tone(110, 0.4, "triangle", freq_end=880, attack=0.01, release=0.05), 0, 0.5)
    # souffle qui monte
    swell = noise(0.45, hold=SR, attack=0.35, release=0.1, highpass_hz=3500)
    place(out, swell, 0, 0.25)
    # arpège rapide
    arp = ["C5", "E5", "G5", "C6", "E6", "G6", "C7"]
    for i, name in enumerate(arp):
        place(out, tone(name, 0.07, "square", duty=0.25, attack=0.002, release=0.02), 0.03 + i * 0.05, 0.5)
    # accord final brillant avec léger vibrato
    t0 = 0.4
    chord = [("C6", 0.25, 0.4), ("E6", 0.5, 0.3), ("G6", 0.125, 0.3)]
    for name, duty, vol in chord:
        place(out, tone(name, 1.2, "square", duty=duty, vol=vol, attack=0.01, release=0.5,
                        curve=1.0, vib=0.15, vib_rate=7.0), t0)
    place(out, tone("C4", 1.2, "triangle", attack=0.01, release=0.5, curve=1.0), t0, 0.45)
    place(out, tone("G4", 1.2, "triangle", attack=0.01, release=0.5, curve=1.0), t0, 0.3)
    # étincelles
    sparkle = ["C7", "D7", "E7", "G7", "A7", "C8"]
    t = 0.35
    while t < 1.45:
        vol = 0.18 * (1.0 - (t - 0.35) / 1.2)
        place(out, tone(random.choice(sparkle), 0.04, "square", duty=0.125,
                        attack=0.001, release=0.02), t, vol)
        t += random.uniform(0.035, 0.07)
    return out


def sfx_death_special():
    """Mort qui rend plus fort : impact grave, souffle qui monte, puis lumière (la mineur -> la majeur)."""
    d = 2.2
    out = silence(d)
    place(out, tone(95, 0.55, "triangle", freq_end=38, attack=0.001, release=0.3), 0, 1.0)
    place(out, noise(0.35, hold=2200, attack=0.001, release=0.25, lowpass_hz=900), 0, 0.7)
    place(out, noise(0.9, hold=SR, attack=0.8, release=0.05, highpass_hz=2500), 0.15, 0.28)
    arp = ["A3", "C4", "E4", "A4", "C5", "E5", "A5", "C#6", "E6"]
    for i, name in enumerate(arp):
        place(out, tone(name, 0.22, "triangle", attack=0.004, release=0.15), 0.35 + i * 0.07, 0.55)
        place(out, tone(name, 0.1, "square", duty=0.125, attack=0.002, release=0.06), 0.35 + i * 0.07, 0.12)
    t0 = 1.0
    for name, duty, vol in (("A5", 0.25, 0.32), ("C#6", 0.5, 0.26), ("E6", 0.125, 0.26), ("A6", 0.125, 0.16)):
        place(out, tone(name, 1.15, "square", duty=duty, vol=vol, attack=0.03, release=0.6, curve=1.0,
                        vib=0.18, vib_rate=6.5), t0)
    place(out, tone("A3", 1.15, "triangle", attack=0.02, release=0.6, curve=1.0), t0, 0.5)
    sparkle = ["A6", "C#7", "E7", "A7", "C#8"]
    t = 1.0
    while t < 2.05:
        place(out, tone(random.choice(sparkle), 0.04, "square", duty=0.125, attack=0.001, release=0.02), t,
              0.16 * (1.0 - (t - 1.0) / 1.1))
        t += random.uniform(0.03, 0.06)
    return echo(out, 0.11, feedback=0.3, repeats=2, wrap=False)


def sfx_aging():
    d = 1.5
    out = silence(d)
    a4 = note_freq("A4")

    def pitch(t):
        base = a4 * 2.0 ** (-7.0 * (t / d) / 12.0)  # A4 -> D4, lentement
        return base * 2.0 ** (0.5 * math.sin(TWO_PI * 4.0 * t) / 12.0)

    place(out, tone(pitch, d, "triangle", attack=0.06, release=0.45), 0, 0.8)
    place(out, tone(lambda t: pitch(t) * 1.004, d, "square", duty=0.125,
                    attack=0.1, release=0.45), 0, 0.22)
    # tic-tac d'horloge
    for i, t in enumerate((0.12, 0.47, 0.82, 1.17)):
        f = 2100 if i % 2 == 0 else 1400
        click = noise(0.03, hold=SR, attack=0.0005, release=0.01, curve=0.006, highpass_hz=3000)
        place(out, click, t, 0.5)
        place(out, tone(f, 0.03, "square", duty=0.5, attack=0.0005, release=0.01, curve=0.008), t, 0.3)
    return out


def sfx_select():
    a = tone("C6", 0.07, "square", duty=0.25, attack=0.002, release=0.008)
    b = tone("G6", 0.18, "square", duty=0.25, attack=0.002, release=0.05, curve=0.09)
    out = concat(a, b)
    return out


def sfx_menu_move():
    return tone(1320, 0.06, "square", duty=0.25, attack=0.001, release=0.02, curve=0.025)


def sfx_spring():
    d = 0.35

    def pitch(t):
        base = 170 * 3.2 ** (t / d)
        return base * (1.0 + 0.3 * math.exp(-t * 7.0) * math.sin(TWO_PI * 16.0 * t))

    out = silence(d)
    place(out, tone(pitch, d, "triangle", attack=0.003, release=0.08, curve=0.3), 0, 1.0)
    place(out, tone(pitch, d, "square", duty=0.25, attack=0.003, release=0.08, curve=0.2), 0, 0.3)
    return out


def sfx_break():
    d = 0.3
    out = silence(d)
    place(out, noise(0.12, hold=8000, attack=0.001, release=0.03, curve=0.04), 0, 1.0)
    place(out, tone(lambda t: 55 + 130 * math.exp(-t * 30), 0.1, "sine",
                    attack=0.001, release=0.03, curve=0.04), 0, 0.8)
    # éboulement : petits grains de débris
    for k in range(9):
        t = 0.03 + k * 0.028 + random.uniform(0.0, 0.012)
        grain = noise(0.03, hold=random.uniform(2000, 6000), attack=0.001, release=0.01, curve=0.01)
        place(out, grain, t, 0.6 * (1.0 - k / 10.0))
    return drive(out, 1.5)


def sfx_bump():
    d = 0.12
    out = silence(d)
    place(out, tone(180, d, "square", duty=0.5, freq_end=90, attack=0.001, release=0.04, curve=0.05), 0, 0.6)
    place(out, tone(120, d, "triangle", freq_end=60, attack=0.001, release=0.04, curve=0.06), 0, 1.0)
    place(out, noise(0.03, hold=3000, attack=0.0005, release=0.01, curve=0.01, lowpass_hz=2500), 0, 0.4)
    return out


def sfx_powerup():
    out = silence(0.6)
    notes = [("G5", 0.0, 0.09), ("B5", 0.09, 0.09), ("D6", 0.18, 0.09), ("G6", 0.27, 0.33)]
    for name, t, d in notes:
        rel = 0.12 if d > 0.1 else 0.01
        place(out, tone(name, d, "square", duty=0.25, attack=0.002, release=rel), t, 0.6)
        place(out, tone(transpose(name, -12), d, "triangle", attack=0.002, release=rel), t, 0.4)
    return echo(out, 0.045, 0.3, 1, wrap=False)


def sfx_zombie_groan():
    d = 0.7

    def pitch(t):
        x = t / d
        base = 85 * (115 / 85) ** (x / 0.35) if x < 0.35 else 115 * (68 / 115) ** ((x - 0.35) / 0.65)
        return base * 2.0 ** (0.8 * math.sin(TWO_PI * 3.5 * t) / 12.0)

    out = silence(d)
    place(out, tone(pitch, d, "square", duty=0.25, attack=0.08, release=0.2), 0, 0.7)
    place(out, tone(lambda t: pitch(t) * 1.015, d, "square", duty=0.5, attack=0.08, release=0.2), 0, 0.5)
    place(out, noise(d, hold=3000, attack=0.1, release=0.2, lowpass_hz=1200), 0, 0.3)
    out = lowpass(out, 900, passes=2)
    # léger tremolo "baveux"
    return [x * (0.8 + 0.2 * math.sin(TWO_PI * 7.0 * i / SR)) for i, x in enumerate(out)]


def sfx_spit():
    d = 0.25
    out = silence(d)
    place(out, noise(0.07, hold=SR, attack=0.002, release=0.03, curve=0.03, lowpass_hz=3000), 0, 0.6)
    blip = lowpass(tone(900, 0.12, "square", duty=0.5, freq_end=240, attack=0.002,
                        release=0.03, curve=0.07), 2500)
    place(out, blip, 0.01, 1.0)
    place(out, tone(350, 0.08, "triangle", freq_end=1100, attack=0.003, release=0.03), 0.15, 0.7)
    return out


def sfx_boss_roar():
    d = 1.4

    def pitch(t):
        x = t / d
        base = 55 + 45 * (x / 0.3) if x < 0.3 else 100 - 55 * ((x - 0.3) / 0.7)
        return base * (1.0 + 0.06 * math.sin(TWO_PI * 23.0 * t))

    out = silence(d)
    place(out, tone(pitch, d, "saw", attack=0.06, release=0.4), 0, 1.0)
    place(out, tone(lambda t: pitch(t) * 1.01, d, "square", duty=0.25, attack=0.06, release=0.4), 0, 0.6)
    place(out, noise(d, hold=5000, attack=0.05, release=0.4, lowpass_hz=1500), 0, 0.8)
    out = [x * (0.7 + 0.3 * math.sin(TWO_PI * 25.0 * i / SR)) for i, x in enumerate(out)]
    out = lowpass(out, 2200)
    return drive(out, 3.0)


def sfx_boss_slam():
    d = 0.6
    out = silence(d)
    place(out, tone(lambda t: 30 + 90 * math.exp(-t * 18), 0.5, "sine",
                    attack=0.001, release=0.1, curve=0.18), 0, 1.0)
    place(out, noise(0.03, hold=SR, attack=0.0005, release=0.01, curve=0.01), 0, 0.6)
    place(out, noise(d, hold=900, attack=0.002, release=0.12, curve=0.2, lowpass_hz=350), 0, 1.0)
    place(out, tone(lambda t: 40 + 30 * math.exp(-t * 4), d, "triangle",
                    attack=0.002, release=0.12, curve=0.25), 0, 0.4)
    return drive(out, 2.5)


def _clank():
    c = silence(0.3)
    partials = [(523, 1.0, 0.12), (1187, 0.6, 0.09), (1763, 0.5, 0.07), (2601, 0.35, 0.05), (3310, 0.25, 0.04)]
    for fr, amp, dec in partials:
        w = "square" if fr < 1000 else "sine"
        place(c, tone(fr, 0.3, w, duty=0.5, attack=0.0005, release=0.02, curve=dec), 0, amp)
    place(c, noise(0.06, hold=SR, attack=0.0005, release=0.02, curve=0.015), 0, 0.8)
    return c


def sfx_gate():
    d = 0.8
    out = silence(d)
    place(out, _clank(), 0, 1.0)
    place(out, _clank(), 0.17, 0.35)
    place(out, noise(d, hold=600, attack=0.002, release=0.15, curve=0.25, lowpass_hz=250), 0, 1.2)
    place(out, tone(55, d, "triangle", attack=0.002, release=0.15, curve=0.3), 0, 0.5)
    return drive(out, 1.8)


# ---------------------------------------------------------------------------
# Séquenceur (jingles et musiques)
# ---------------------------------------------------------------------------
def seq(pattern):
    """'C5:1 E5:.5 R:1/3' -> [(note, battements), ...] ; R = silence."""
    out = []
    for tok in pattern.split():
        name, beats = tok.split(":")
        if "/" in beats:
            a, b = beats.split("/")
            out.append((name, float(a) / float(b)))
        else:
            out.append((name, float(beats)))
    return out


def total_beats(notes):
    return sum(b for _, b in notes)


_TONE_CACHE = {}


def cached_tone(freq, dur, **kw):
    key = (freq, round(dur, 6), tuple(sorted(kw.items())))
    if key not in _TONE_CACHE:
        _TONE_CACHE[key] = tone(freq, dur, **kw)
    return _TONE_CACHE[key]


def render_voice(buf, notes, beat, start_beat=0.0, vol=1.0, gate=0.9, wrap=True, **kw):
    """Joue une liste (note, battements) dans buf. Renvoie la position finale (battements)."""
    pos = start_beat
    for name, beats in notes:
        if name != "R":
            src = cached_tone(name, beats * beat * gate, **kw)
            mix_into(buf, src, round(pos * beat * SR), vol, wrap)
        pos += beats
    return pos


def chord_notes(name, octave):
    """'Am', 4 -> ['A4', 'C5', 'E5'] (fondamentale, tierce, quinte)."""
    minor = name.endswith("m")
    root = note_midi(name.rstrip("m") + str(octave))
    return [midi_name(root), midi_name(root + (3 if minor else 4)), midi_name(root + 7)]


def _chords_in(prog):
    # une mesure peut contenir deux accords ("F G")
    for bar in prog:
        chords = bar.split()
        for ch in chords:
            yield ch, 4.0 / len(chords)


def bass_line(prog, style="octave", octave=2):
    out = []
    for ch, beats in _chords_in(prog):
        r, _, f = chord_notes(ch, octave)
        o = transpose(r, 12)
        if style == "half":
            out += [(r, beats / 2), (f, beats / 2)]
            continue
        pat = [r, o] if style == "octave" else [r, f, o, f]
        out += [(pat[i % len(pat)], 0.5) for i in range(int(beats * 2))]
    return out


def arp_line(prog, octave=4, pattern=(0, 1, 2, 3), step=0.25):
    out = []
    for ch, beats in _chords_in(prog):
        r, t, f = chord_notes(ch, octave)
        tones = [r, t, f, transpose(r, 12)]
        out += [(tones[pattern[i % len(pattern)]], step) for i in range(int(round(beats / step)))]
    return out


def third_below(notes, scale=(0, 2, 4, 5, 7, 9, 11)):
    """Harmonie diatonique une tierce en dessous (deux degrés de la gamme)."""
    out = []
    for name, b in notes:
        if name == "R":
            out.append((name, b))
            continue
        k, steps = note_midi(name), 0
        while steps < 2:
            k -= 1
            if k % 12 in scale:
                steps += 1
        out.append((midi_name(k), b))
    return out


_DRUMS = {}
DRUM_VOL = {"k": 1.0, "s": 0.55, "h": 0.2, "o": 0.22, "c": 0.3}


def drum(kind):
    """k = grosse caisse, s = caisse claire, h/o = charleston fermé/ouvert, c = cymbale."""
    if kind not in _DRUMS:
        if kind == "k":
            s = tone(lambda t: 45 + 120 * math.exp(-t * 35), 0.15, "sine",
                     attack=0.001, release=0.03, curve=0.07)
            mix_into(s, noise(0.01, hold=SR, attack=0.0005, release=0.005), 0, 0.3)
        elif kind == "s":
            s = noise(0.15, hold=SR, attack=0.001, release=0.03, curve=0.05, highpass_hz=900)
            mix_into(s, tone(190, 0.07, "triangle", freq_end=140, attack=0.001,
                             release=0.02, curve=0.03), 0, 0.6)
        elif kind == "h":
            s = noise(0.04, hold=SR, attack=0.0005, release=0.01, curve=0.012, highpass_hz=6000)
        elif kind == "o":
            s = noise(0.15, hold=SR, attack=0.0005, release=0.04, curve=0.05, highpass_hz=5000)
        else:
            s = noise(1.0, hold=SR, attack=0.001, release=0.2, curve=0.35, highpass_hz=3000)
        _DRUMS[kind] = normalize(s)
    return _DRUMS[kind]


def render_drums(buf, bars, beat, start_bar=0, vol=1.0, wrap=True):
    """bars : liste de dicts {instrument: motif de 16 doubles-croches}.
    'x' = coup, '-' = coup faible, '.' = rien."""
    step = beat / 4
    for b, pat in enumerate(bars):
        bar_start = (start_bar + b) * 4 * beat
        for kind, steps in pat.items():
            for i, ch in enumerate(steps):
                if ch != ".":
                    g = vol * DRUM_VOL[kind] * (0.55 if ch == "-" else 1.0)
                    mix_into(buf, drum(kind), round((bar_start + i * step) * SR), g, wrap)


def new_loop(bpm, bars):
    beat = 60.0 / bpm
    return [0.0] * int(round(bars * 4 * beat * SR)), beat


# ---------------------------------------------------------------------------
# Jingles
# ---------------------------------------------------------------------------
def sfx_victory():
    beat = 60.0 / 160
    out = silence(3.5)
    lead = seq("C5:.5 E5:.5 G5:.5 C6:1 G5:.5 A5:.5 F5:.5 A5:.5 C6:1 D6:1/3 D6:1/3 D6:1/3")
    harm = seq("G4:.5 C5:.5 E5:.5 G5:1 E5:.5 F5:.5 C5:.5 F5:.5 A5:1 B5:1/3 B5:1/3 B5:1/3")
    bass = seq("C3:1 G3:1 C3:1 F3:1 C4:1 F3:.5 G3:1")
    render_voice(out, lead, beat, vol=0.45, gate=0.85, wrap=False, duty=0.5, release=0.02)
    render_voice(out, harm, beat, vol=0.25, gate=0.85, wrap=False, duty=0.25, release=0.02)
    render_voice(out, bass, beat, vol=0.55, gate=0.9, wrap=False, wave="triangle", release=0.02)
    # note finale tenue (accord de do majeur)
    t_end = 6.5 * beat
    d = 3.5 - t_end
    fin = dict(attack=0.005, release=0.55, curve=1.2, vib=0.25, vib_rate=6.0, vib_delay=0.2)
    place(out, tone("E6", d, "square", duty=0.5, **fin), t_end, 0.45)
    place(out, tone("C6", d, "square", duty=0.25, **fin), t_end, 0.25)
    place(out, tone("G5", d, "square", duty=0.125, **fin), t_end, 0.12)
    place(out, tone("C3", d, "triangle", attack=0.005, release=0.55, curve=1.2), t_end, 0.6)
    # percussions
    for b in (0.0, 3.0):
        place(out, drum("k"), b * beat, 0.5)
    for b in (5.5, 5.5 + 1 / 3, 5.5 + 2 / 3):
        place(out, drum("s"), b * beat, 0.3)
    place(out, drum("k"), t_end, 0.55)
    place(out, drum("c"), t_end, 0.25)
    return out


def sfx_game_over():
    beat = 0.6
    out = silence(2.8)
    lead = seq("E5:.5 D5:.5 C5:.5 B4:.5 A4:.5 G#4:.5")
    harm = seq("C5:1 A4:1 E4:1")
    bass = seq("A2:1 F2:1 E2:1")
    render_voice(out, lead, beat, vol=0.45, gate=0.85, wrap=False, duty=0.25, release=0.04)
    render_voice(out, harm, beat, vol=0.2, gate=0.9, wrap=False, duty=0.125, release=0.05)
    render_voice(out, bass, beat, vol=0.55, gate=0.9, wrap=False, wave="triangle", release=0.05)
    t_end = 3 * beat
    d = 2.8 - t_end
    place(out, tone("A4", d, "square", duty=0.25, attack=0.01, release=0.5, curve=1.0,
                    vib=0.3, vib_rate=5.0, vib_delay=0.25), t_end, 0.45)
    place(out, tone("C4", d, "square", duty=0.125, attack=0.01, release=0.5, curve=1.0), t_end, 0.2)
    place(out, tone("A2", d, "triangle", attack=0.01, release=0.5, curve=1.0), t_end, 0.55)
    return out


# ---------------------------------------------------------------------------
# Musiques (boucles parfaites)
# ---------------------------------------------------------------------------
def music_level():
    """Thème du niveau : 140 BPM, do majeur, A (8) + B (8) + A' (8) + transition (4)."""
    buf, beat = new_loop(140, 28)
    prog_a = ["C", "G", "Am", "F", "C", "G", "F G", "C"]
    prog_b = ["F", "G", "Em", "Am", "F", "G", "Am", "G"]
    prog_t = ["F", "G", "Am", "G"]
    lead_a = seq(
        "E5:.5 G5:.5 C6:1 B5:.5 G5:.5 E5:1 "
        "D5:.5 G5:.5 B5:1 A5:.5 G5:.5 D5:1 "
        "C5:.5 E5:.5 A5:1 G5:.5 E5:.5 C5:.5 E5:.5 "
        "F5:1 A5:.5 C6:.5 A5:1 G5:1 "
        "E5:.5 G5:.5 C6:1 B5:.5 C6:.5 D6:1 "
        "B5:.5 G5:.5 D5:1 G5:.5 A5:.5 B5:1 "
        "A5:.5 G5:.5 F5:.5 A5:.5 G5:.5 F5:.5 D5:.5 B4:.5 "
        "C5:2 R:1 G4:.5 B4:.5")
    lead_b = seq(
        "C5:.75 A4:.75 C5:.5 F5:1 E5:1 "
        "D5:.75 B4:.75 D5:.5 G5:1 F5:.5 E5:.5 "
        "E5:.75 G5:.75 B5:.5 E6:1.5 D6:.5 "
        "C6:1 B5:.5 A5:.5 E5:2 "
        "F5:.5 F5:.5 A5:.5 C6:.5 R:.5 C6:.5 D6:.5 C6:.5 "
        "B5:.5 B5:.5 D6:.5 B5:.5 R:.5 G5:.5 A5:.5 B5:.5 "
        "C6:1.5 B5:.5 A5:.5 G5:.5 E5:1 "
        "D5:.5 E5:.5 F5:.5 G5:.5 A5:.5 B5:.5 D6:1")
    lead_t = seq(
        "A5:1 G5:.5 F5:.5 C5:2 "
        "B5:1 A5:.5 G5:.5 D5:2 "
        "C6:1 B5:.5 A5:.5 E5:1 A5:1 "
        "G5:1 D5:.5 G5:.5 B5:1 B4:.5 D5:.5")
    assert total_beats(lead_a) == 32 and total_beats(lead_b) == 32 and total_beats(lead_t) == 16

    lead = dict(wave="square", attack=0.004, decay=0.08, sustain=0.7, release=0.03,
                vib=0.15, vib_rate=6.0, vib_delay=0.18)
    render_voice(buf, lead_a, beat, 0, 0.30, duty=0.25, **lead)
    render_voice(buf, lead_b, beat, 32, 0.28, duty=0.5, **lead)
    render_voice(buf, lead_a, beat, 64, 0.30, duty=0.25, **lead)
    render_voice(buf, third_below(lead_a), beat, 64, 0.13, duty=0.125, **lead)
    render_voice(buf, lead_t, beat, 96, 0.30, duty=0.25, **lead)

    # arpèges (section B et transition)
    pluck = dict(wave="square", duty=0.125, attack=0.002, release=0.02, curve=0.06)
    render_voice(buf, arp_line(prog_b, 4), beat, 32, 0.09, gate=0.8, **pluck)
    render_voice(buf, arp_line(prog_t, 4), beat, 96, 0.08, gate=0.8, **pluck)

    # basse triangle
    tri = dict(wave="triangle", attack=0.004, release=0.03)
    render_voice(buf, bass_line(prog_a, "octave"), beat, 0, 0.42, gate=0.8, **tri)
    render_voice(buf, bass_line(prog_b, "arp"), beat, 32, 0.42, gate=0.8, **tri)
    render_voice(buf, bass_line(prog_a, "octave"), beat, 64, 0.42, gate=0.8, **tri)
    render_voice(buf, bass_line(prog_t, "octave"), beat, 96, 0.42, gate=0.8, **tri)

    # batterie
    normal = {"k": "x.......x.x.....", "s": "....x.......x...", "h": "x-x-x-x-x-x-x-x-"}
    busy = {"k": "x.....x...x.....", "s": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"}
    fill = {"k": "x.......x.......", "s": "....x...x.x.xxxx", "h": "x-x-x-x-........"}
    crash = dict(normal, c="x...............")
    crash_busy = dict(busy, c="x...............")
    drums = ([normal] * 7 + [fill] + [crash_busy] + [busy] * 6 + [fill]
             + [crash] + [normal] * 6 + [fill] + [busy] * 3 + [fill])
    render_drums(buf, drums, beat, 0, 0.5)
    return buf


def music_boss():
    """Thème du boss : 160 BPM, la mineur, A (8) + B (8) + transition (4)."""
    buf, beat = new_loop(160, 20)
    prog_a = ["Am", "Am", "F", "G", "Am", "Am", "F", "E"]
    prog_b = ["Dm", "Am", "Dm", "E", "F", "G", "E", "E"]
    prog_t = ["Am", "F", "G", "E"]
    lead_a = seq(
        "A4:.5 A4:.5 C5:.5 A4:.5 E5:1 D5:.5 C5:.5 "
        "B4:.5 C5:.5 D5:.5 E5:.5 A5:2 "
        "F5:.5 E5:.5 D5:.5 C5:.5 D5:1 A4:1 "
        "G4:.5 A4:.5 B4:.5 D5:.5 G5:1.5 F5:.5 "
        "E5:.5 E5:.5 A5:.5 E5:.5 C6:1 B5:.5 A5:.5 "
        "G5:.5 A5:.5 B5:.5 C6:.5 E6:2 "
        "D6:.5 C6:.5 A5:.5 F5:.5 D6:1 C6:1 "
        "B5:1 G#5:1 E5:1 B4:1")
    lead_b = seq(
        "F5:2 E5:1 D5:1 "
        "E5:2 C5:1 A4:1 "
        "F5:1 G5:1 A5:1 D6:1 "
        "G#5:3 B5:1 "
        "C6:1.5 A5:.5 F5:1 A5:1 "
        "D6:1.5 B5:.5 G5:1 B5:1 "
        "E6:.5 B5:.5 G#5:.5 E5:.5 E6:.5 B5:.5 G#5:.5 E5:.5 "
        "G#5:.5 A5:.5 B5:.5 C6:.5 D6:1 E6:1")
    riff = lambda notes, times: [(n, 0.25) for n in notes.split()] * times
    lead_t = (riff("A5 E5 C5 E5", 4) + riff("A5 F5 C5 F5", 4) + riff("B5 G5 D5 G5", 4)
              + riff("G#5 E5 B4 E5", 2) + seq("G#5:1 B5:1"))
    assert total_beats(lead_a) == 32 and total_beats(lead_b) == 32 and total_beats(lead_t) == 16

    lead = dict(wave="square", attack=0.003, decay=0.06, sustain=0.8, release=0.03,
                vib=0.2, vib_rate=7.0, vib_delay=0.15)
    render_voice(buf, lead_a, beat, 0, 0.28, duty=0.5, **lead)
    render_voice(buf, lead_b, beat, 32, 0.26, duty=0.25, **lead)
    harmonic_minor = (9, 11, 0, 2, 4, 5, 8)
    render_voice(buf, third_below(lead_b, harmonic_minor), beat, 32, 0.13, duty=0.125, **lead)
    render_voice(buf, lead_t, beat, 64, 0.24, gate=0.7, duty=0.125, **lead)

    # basse triangle + arpèges pulsés graves qui "poussent"
    tri = dict(wave="triangle", attack=0.003, release=0.02)
    render_voice(buf, bass_line(prog_a, "octave"), beat, 0, 0.45, gate=0.75, **tri)
    render_voice(buf, bass_line(prog_b, "arp"), beat, 32, 0.45, gate=0.75, **tri)
    render_voice(buf, bass_line(prog_t, "octave"), beat, 64, 0.45, gate=0.75, **tri)
    pluck = dict(wave="square", duty=0.25, attack=0.002, release=0.015, curve=0.05)
    prog_all = prog_a + prog_b + prog_t
    render_voice(buf, arp_line(prog_all, 3, (0, 2, 3, 2)), beat, 0, 0.08, gate=0.7, **pluck)

    # batterie plus lourde
    four = {"k": "x...x...x...x...", "s": "....x.......x...", "h": "x-x-x-x-x-x-x-x-"}
    open_ = {"k": "x...x...x...x.x.", "s": "....x.......x...", "h": "x...x...x...x...",
             "o": "..x...x...x...x."}
    drive_ = {"k": "x.x.x.x.x.x.x.x.", "s": "....x.......x...", "h": "xxxxxxxxxxxxxxxx"}
    fill = {"k": "x...x...x.......", "s": "....x...xxxxxxxx", "h": "x-x-x-x-........"}
    drums = ([four] * 7 + [fill] + [dict(open_, c="x...............")] + [open_] * 6 + [fill]
             + [dict(drive_, c="x...............")] + [drive_] * 2 + [fill])
    render_drums(buf, drums, beat, 0, 0.55)
    return buf


def music_menu():
    """Thème du menu : 100 BPM, fa majeur, doux et rêveur (12 mesures)."""
    buf, beat = new_loop(100, 12)
    prog = ["F", "Am", "Bb", "C", "Dm", "Bb", "F", "C", "Bb", "C", "Am Dm", "Gm C"]
    melody = seq(
        "A5:1.5 G5:.5 F5:1 C5:1 "
        "E5:1.5 F5:.5 G5:1 A5:1 "
        "D6:1.5 C6:.5 Bb5:1 F5:1 "
        "G5:3 R:1 "
        "F5:1 A5:1 D6:1.5 C6:.5 "
        "Bb5:1 A5:.5 G5:.5 F5:2 "
        "A5:1 C6:1 A5:1 F5:1 "
        "G5:2 E5:1 C5:1 "
        "D5:1 F5:1 Bb5:2 "
        "C6:1 Bb5:.5 A5:.5 G5:2 "
        "A5:1 E5:1 F5:1 D5:1 "
        "G5:1 Bb5:1 A5:1 G5:1")
    assert total_beats(melody) == 48

    lead = [0.0] * len(buf)
    render_voice(lead, melody, beat, 0, 0.24, gate=0.92, wave="square", duty=0.25,
                 attack=0.02, decay=0.2, sustain=0.6, release=0.08,
                 vib=0.2, vib_rate=5.0, vib_delay=0.25)
    lead = lowpass(lead, 3200)
    lead = echo(lead, 0.75 * beat, 0.3, 2)  # écho circulaire : pas de coupure à la boucle
    mix_into(buf, lead, 0)

    # boîte à musique (triangle aigu, notes pincées)
    box = dict(wave="triangle", attack=0.002, release=0.05, curve=0.18)
    render_voice(buf, arp_line(prog, 5, (0, 1, 2, 3, 2, 1), 0.5), beat, 0, 0.16, gate=0.95, **box)
    # basse douce
    render_voice(buf, bass_line(prog, "half"), beat, 0, 0.38, gate=0.9,
                 wave="triangle", attack=0.01, release=0.08)
    render_drums(buf, [{"k": "x.......x.......", "h": "..-...-...-...-."}] * 12, beat, 0, 0.3)
    return buf


# ---------------------------------------------------------------------------
# Programme principal
# ---------------------------------------------------------------------------
SOUNDS = [
    ("jump.wav", sfx_jump, SFX_PEAK),
    ("coin.wav", sfx_coin, SFX_PEAK),
    ("sword.wav", sfx_sword, SFX_PEAK),
    ("hit.wav", sfx_hit, SFX_PEAK),
    ("stomp.wav", sfx_stomp, SFX_PEAK),
    ("hurt.wav", sfx_hurt, SFX_PEAK),
    ("death.wav", sfx_death, SFX_PEAK),
    ("death_special.wav", sfx_death_special, SFX_PEAK),
    ("rebirth.wav", sfx_rebirth, SFX_PEAK),
    ("aging.wav", sfx_aging, SFX_PEAK),
    ("select.wav", sfx_select, SFX_PEAK),
    ("menu_move.wav", sfx_menu_move, SFX_PEAK),
    ("spring.wav", sfx_spring, SFX_PEAK),
    ("break.wav", sfx_break, SFX_PEAK),
    ("bump.wav", sfx_bump, SFX_PEAK),
    ("powerup.wav", sfx_powerup, SFX_PEAK),
    ("zombie_groan.wav", sfx_zombie_groan, SFX_PEAK),
    ("spit.wav", sfx_spit, SFX_PEAK),
    ("boss_roar.wav", sfx_boss_roar, SFX_PEAK),
    ("boss_slam.wav", sfx_boss_slam, SFX_PEAK),
    ("gate.wav", sfx_gate, SFX_PEAK),
    ("victory.wav", sfx_victory, SFX_PEAK),
    ("game_over.wav", sfx_game_over, SFX_PEAK),
    ("music_level.wav", music_level, MUSIC_PEAK),
    ("music_boss.wav", music_boss, MUSIC_PEAK),
    ("music_menu.wav", music_menu, MUSIC_PEAK),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total = 0
    for name, fn, target in SOUNDS:
        dur, size = write_wav(OUT_DIR / name, fn(), target)
        total += size
        print(f"{name:<18} {dur:6.2f} s  {size / 1024:8.1f} Ko")
    print(f"{len(SOUNDS)} fichiers, {total / 1024 / 1024:.2f} Mo -> {OUT_DIR}")


if __name__ == "__main__":
    main()
