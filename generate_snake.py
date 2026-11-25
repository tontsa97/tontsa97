#!/usr/bin/env python3
"""Self-playing snake SVGs (light + dark) with typing trash talk.
The snake can pass through text blocks: letters on the gate row part for it,
but on some runs they stay put and the snake crashes into them.
Pure SMIL/CSS animation: works inside <img> on GitHub, no maintenance needed.
Usage: python generate_snake.py [outdir]
"""
import random
import sys
import textwrap
from collections import deque
from pathlib import Path

SEED = 97
CELL = 14
COLS, ROWS = 60, 34
W, H_GAME = COLS * CELL, ROWS * CELL
H_TERM = 56
H = H_GAME + H_TERM
STEP = 0.11
FOODS_PER_GAME = (8, 14)
PAUSE = 14
ADV = 7.8  # monospace letter advance
LH = 18
NEAR = 3  # cells ahead/behind the snake where letters step aside
FOOD_IN_TEXT = 0.4

# (col0, row0, cols, rows, text); the middle row is the gate the snake can pass through
L, R = 1, 31
BLOCKS = [
    (15, 1, 30, 3, "Hi there", 24),
    (L, 6, 28, 5, "I'm a FiveM developer in the making, mostly into QBCore and QBox. I just like building things in my free time."),
    (R, 6, 28, 5, "Right now I'm working on getting better at Lua for FiveM development, and digging deeper into QBCore and QBox."),
    (L, 13, 28, 5, "Got questions about FiveM or Lua? Ask me, I'm happy to talk about it."),
    (R, 13, 28, 5, "Fun fact: I love gaming, and I'm always poking around to see how new game mechanics work."),
    (L, 20, 28, 5, "I'm from Finland, born in 1997, and I like to go fishing when I'm away from the keyboard."),
    (R, 20, 28, 5, "I learn and practice coding with the help of AI, because why not use modern tools to my advantage?"),
    (L, 27, 28, 5, "I started from scratch with YouTube tutorials and Discord forums. Five years of Lua later, I'm still at it."),
    (R, 27, 28, 5, "I use AI tools to learn faster and make the most of modern tech. So don't wait up, I'm on a mission."),
]

PHRASES = [
    "koodisi on niin paskaa että kahvitkin kaatuu näppäimistölle",
    "tuo funktio on niin pitkä että sille pitäisi olla oma postinumero",
    "git blame sanoo että tämä oli sinä. se tietää.",
    "Stack Overflow esti sinut ennen kuin ehdit kysyä",
    "sun nil-tarkistus on yhtä todellinen kuin kalajutut",
    "ChatGPT pyysi jo siirtoa toiseen keskusteluun",
    "lua-taulukkosi alkaa ykkösestä, itsetuntosi nollasta",
    "tuo bugi ei ole bugi, se on sun persoonallisuus",
    "tuotannossa testaus? rohkeaa. typerää, mutta rohkeaa.",
    "sun koodi toimii vain koska kukaan ei uskalla koskea siihen",
    "console.log ei ole debuggaus-strategia, se on huuto tyhjyyteen",
    "FiveM-serverisi kaatuu nopeammin kuin kalasi karkaa",
    "kommentoit koodin sanalla 'TODO'. vuonna 2021.",
    "sun spagettikoodi saisi italialaiset itkemään",
    "palvelin ei kaatunut, se vain valitsi lopettaa",
    "sinä: 'toimii mulla'. käyttäjät: *itkua*",
    "tuo for-silmukka on ikuinen kuten sun TODO-lista",
    "jopa kääntäjä huokaisi tuota riviä lukiessaan",
    "backupit? sehän on vain pelkuruutta, eikö?",
    "ctrl+z ei auta tähän, ei edes ctrl+alt+delete",
    "olet debugannut tuntikausia. puolipiste oli ihan oikeassa paikassa.",
    "sun resmon näyttää 0.00ms koska skripti ei edes käynnisty",
]

THEMES = {
    "light": dict(bg="#f6f8fa", border="#d0d7de", dot="#d8dee4", block="#e2e8f0", btxt="#24292f",
                  body="#2da44e", head="#1a7f37", food="#cf222e", dead="#fa4549",
                  term="#ffffff", term_txt="#24292f", prompt="#0969da", cursor="#24292f"),
    "dark": dict(bg="#0d1117", border="#30363d", dot="#1b2230", block="#161b22", btxt="#e6edf3",
                 body="#2ea043", head="#56d364", food="#ff7b72", dead="#f85149",
                 term="#010409", term_txt="#e6edf3", prompt="#58a6ff", cursor="#e6edf3"),
}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def gate_row(b):
    return b[1] + b[3] // 2


GATE = {}   # cell -> block index
OBST = set()
for bi, b in enumerate(BLOCKS):
    g = gate_row(b)
    for c in range(b[0], b[0] + b[2]):
        for r in range(b[1], b[1] + b[3]):
            if r == g:
                GATE[(c, r)] = bi
            else:
                OBST.add((c, r))


def inside(p):
    return 0 <= p[0] < COLS and 0 <= p[1] < ROWS


def bfs(start, goal_fn, blocked):
    prev = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if goal_fn(cur) and cur != start:
            path = []
            while cur != start:
                path.append(cur)
                cur = prev[cur]
            return path[::-1]
        for d in DIRS:
            n = (cur[0] + d[0], cur[1] + d[1])
            if inside(n) and n not in prev and n not in blocked:
                prev[n] = cur
                q.append(n)
    return None


def hits_wall(p):
    return any((not inside((p[0] + d[0], p[1] + d[1]))) or (p[0] + d[0], p[1] + d[1]) in OBST for d in DIRS)


def simulate(rng):
    """Returns (frames, nodge). frame: cell -> state (1 body, 2 head, 3 food, 4 dead);
    nodge[i]: set of block indexes whose letters do NOT step aside in that frame."""
    frames, nodge = [], []
    kinds = ["wall", "letter", "letter"]
    rng.shuffle(kinds)
    for kind in kinds:
        snake = deque([(3, 4), (2, 4), (1, 4)])
        target = rng.randint(*FOODS_PER_GAME)
        eaten = 0
        ndset = set()

        def new_food():
            gate = [c for c in GATE if c not in snake]
            if gate and rng.random() < FOOD_IN_TEXT:
                return rng.choice(gate)
            free = [(c, r) for c in range(COLS) for r in range(ROWS)
                    if (c, r) not in OBST and (c, r) not in GATE and (c, r) not in snake]
            return rng.choice(free)

        def emit(food=None):
            f = {c: 1 for c in snake}
            f[snake[0]] = 2
            if food:
                f[food] = 3
            frames.append(f)
            nodge.append(set(ndset))

        food = new_food()
        path, phase, final = [], "eat", None
        guard = 0

        def start_die():
            nonlocal path, phase, final
            phase = "die"
            body = set(list(snake)[:-1])
            if kind == "letter":
                gates = []
                for bi, b in enumerate(BLOCKS):
                    g = gate_row(b)
                    gates.append(((b[0] - 1, g), (b[0], g), bi))
                    gates.append(((b[0] + b[2], g), (b[0] + b[2] - 1, g), bi))
                rng.shuffle(gates)
                for entry, gcell, bi in gates:
                    if not inside(entry) or entry in body:
                        continue
                    p = [] if snake[0] == entry else bfs(snake[0], lambda x: x == entry, body | OBST)
                    if p is not None:
                        path, final = p, gcell
                        ndset.add(bi)
                        return
            if hits_wall(snake[0]):
                path = []
            else:
                path = bfs(snake[0], hits_wall, body | OBST) or []

        while guard < 6000:
            guard += 1
            emit(food)
            if not path and phase == "eat":
                if eaten >= target:
                    start_die()
                else:
                    p = bfs(snake[0], lambda x: x == food, set(list(snake)[:-1]) | OBST)
                    if p:
                        path = p
                    else:
                        start_die()
            if path:
                nxt = path.pop(0)
                snake.appendleft(nxt)
                if nxt == food:
                    eaten += 1
                    food = new_food()
                else:
                    snake.pop()
                continue
            if phase == "die" and final:
                snake.appendleft(final)
                snake.pop()
                emit()
            break
        dead = {c: 4 for c in snake}
        alive = {c: 1 for c in snake}
        for i in range(PAUSE):
            if i >= PAUSE - 4:
                f = {}
            else:
                f = dict(dead) if i % 2 == 0 else dict(alive)
            frames.append(f)
            nodge.append(set(ndset))
    return frames, nodge


def fmt(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") or "0"


def build_cells(frames, th):
    total = len(frames)
    dur = total * STEP
    colors = {0: "transparent", 1: th["body"], 2: th["head"], 3: th["food"], 4: th["dead"]}
    cells = set()
    for f in frames:
        cells.update(f)
    out = []
    for (c, r) in sorted(cells):
        kt, vals = [], []
        for i in range(total):
            s = frames[i].get((c, r), 0)
            if not vals or vals[-1] != s:
                kt.append(i / total)
                vals.append(s)
        if len(vals) == 1:
            continue
        out.append(f'<rect x="{c * CELL + 1}" y="{r * CELL + 1}" width="{CELL - 2}" height="{CELL - 2}" '
                   f'rx="3" fill="transparent"><animate attributeName="fill" calcMode="discrete" dur="{fmt(dur)}s" '
                   f'repeatCount="indefinite" keyTimes="{";".join(fmt(k) for k in kt)}" '
                   f'values="{";".join(colors[v] for v in vals)}"/></rect>')
    return "\n".join(out), dur


def letter_keyframes(near):
    """near: list of 0/1 per frame -> sorted (frame_index, state) keypoints with a short ease."""
    total = len(near)
    pts = {0: near[0]}
    last = 0
    for i in range(1, total):
        if near[i] != near[i - 1]:
            st = i - 2 if i - 2 > last else (i - 1 if i - 1 > last else None)
            if st is not None:
                pts[st] = near[i - 1]
            pts[i] = near[i]
            last = i
    pts[total] = near[-1]
    return sorted(pts.items())


def graphemes(s):
    out, i = [], 0
    while i < len(s):
        if 0x1F1E6 <= ord(s[i]) <= 0x1F1FF and i + 1 < len(s):
            out.append(s[i:i + 2])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return out


def blocks_svg(th, frames, nodge):
    total = len(frames)
    dur = fmt(total * STEP)
    gate_cols = []
    for f in frames:
        per = {}
        for (c, r), s in f.items():
            bi = GATE.get((c, r))
            if bi is not None and s != 3:
                per.setdefault(bi, []).append(c)
        gate_cols.append(per)
    font = "ui-monospace,SFMono-Regular,Consolas,Menlo,monospace"
    cache = {}
    out = []
    for bi, blk in enumerate(BLOCKS):
        c0, r0, cw, rh, text = blk[:5]
        size = blk[5] if len(blk) > 5 else 13
        adv = ADV * size / 13
        x, y, w, h = c0 * CELL, r0 * CELL, cw * CELL, rh * CELL
        lines = textwrap.wrap(text, 44 if size == 13 else 30)
        fill = th['btxt'] if size == 13 else th['prompt']
        gy = gate_row(blk) * CELL + CELL / 2
        for k, ln in enumerate(lines):
            off = (k - (len(lines) - 1) / 2) * LH
            toks = graphemes(ln)
            ws = [2 if ord(t[0]) >= 0x2600 else 1 for t in toks]
            left = x + w / 2 - sum(ws) * adv / 2 if size > 20 else x + 6
            pos = 0
            for tk, wd in zip(toks, ws):
                tx = left + (pos + wd / 2) * adv
                pos += wd
                if tk == " ":
                    continue
                anim = ""
                if abs(off) <= 9:
                    lc = int(tx // CELL)
                    if (bi, lc) not in cache:
                        cache[(bi, lc)] = [0 if bi in nodge[t] else
                                           int(any(abs(c - lc) <= NEAR for c in gate_cols[t].get(bi, ())))
                                           for t in range(total)]
                    near = cache[(bi, lc)]
                    if any(near):
                        kp = letter_keyframes(near)
                        kts = ";".join(fmt(t / total) for t, _ in kp)
                        dy = -9 if pos % 2 == 0 else 9
                        dx = 3 if pos % 3 == 0 else -3
                        tv = ";".join(f"{dx} {dy}" if s else "0 0" for _, s in kp)
                        ov = ";".join("0.15" if s else "1" for _, s in kp)
                        anim = (f'<animateTransform attributeName="transform" type="translate" dur="{dur}s" '
                                f'repeatCount="indefinite" keyTimes="{kts}" values="{tv}"/>'
                                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                                f'keyTimes="{kts}" values="{ov}"/>')
                tk = tk.replace("&", "&amp;").replace("<", "&lt;")
                out.append(f'<text x="{fmt(tx)}" y="{fmt(gy + off)}" text-anchor="middle" dominant-baseline="central" '
                           f'font-family="{font}" font-size="{size}" font-weight="{600 if size == 13 else 700}" '
                           f'fill="{fill}">{tk}{anim}</text>')
    return "\n".join(out)

def typing(th, rng):
    cw, fs = 8.4, 14
    x0, y0 = 40, H_GAME + 34
    order = PHRASES[:]
    rng.shuffle(order)
    t = 0.0
    slots = []
    for p in order:
        t += rng.uniform(1.5, 4.0)
        type_t = len(p) * 0.055
        hold = 2.6
        slots.append((p, t, type_t, hold))
        t += type_t + hold + 0.4
    total = t + 1.5
    parts, cur_x = [], []
    for i, (p, st, tt, hold) in enumerate(slots):
        n = len(p)
        tw = n * cw
        kt = [0.0]
        vals = [0.0]
        for k in range(1, n + 1):
            kt.append((st + tt * k / n) / total)
            vals.append(k * cw)
        kt.append((st + tt + hold) / total)
        vals.append(0.0)
        parts.append(
            f'<clipPath id="c{i}"><rect x="{x0}" y="{H_GAME + 14}" height="30" width="0">'
            f'<animate attributeName="width" calcMode="discrete" dur="{fmt(total)}s" repeatCount="indefinite" '
            f'keyTimes="{";".join(fmt(k) for k in kt)}" values="{";".join(fmt(v) for v in vals)}"/></rect></clipPath>'
            f'<text x="{x0}" y="{y0}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="{fs}" '
            f'fill="{th["term_txt"]}" textLength="{fmt(tw)}" lengthAdjust="spacingAndGlyphs" clip-path="url(#c{i})">'
            f'{p.replace("&", "&amp;").replace("<", "&lt;")}</text>')
        cur_x.append((st, tt, hold, tw))
    kt, xs, vis = [0.0], [0.0], [0]
    for (st, tt, hold, tw) in cur_x:
        n = max(1, round(tw / cw))
        for k in range(0, n + 1):
            kt.append((st + tt * k / n) / total)
            xs.append(k * cw)
            vis.append(1)
        kt.append((st + tt + hold) / total)
        xs.append(0.0)
        vis.append(0)
    for i in range(1, len(kt)):
        if kt[i] <= kt[i - 1]:
            kt[i] = kt[i - 1] + 1e-6
    ktv = ";".join(fmt(k) for k in kt)
    cursor = (
        f'<g><animate attributeName="opacity" calcMode="discrete" dur="{fmt(total)}s" repeatCount="indefinite" '
        f'keyTimes="{ktv}" values="{";".join(map(str, vis))}"/>'
        f'<rect class="cur" x="{x0}" y="{H_GAME + 18}" width="8" height="18" fill="{th["cursor"]}">'
        f'<animate attributeName="x" calcMode="discrete" dur="{fmt(total)}s" repeatCount="indefinite" '
        f'keyTimes="{ktv}" values="{";".join(fmt(x0 + v) for v in xs)}"/></rect></g>'
    )
    return "\n".join(parts) + "\n" + cursor


def build(th, frames, nodge):
    rng = random.Random(SEED + 1)
    cells, dur = build_cells(frames, th)
    dots = "".join(f'<circle cx="{c * CELL + CELL / 2}" cy="{r * CELL + CELL / 2}" r="0.9" fill="{th["dot"]}"/>'
                   for c in range(COLS) for r in range(ROWS))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Itsestään pelaava snake ja koodaus-trashtalk">
<style>.cur{{animation:b 1s steps(1) infinite}}@keyframes b{{50%{{opacity:0}}}}</style>
<rect width="{W}" height="{H}" rx="10" fill="{th["bg"]}" stroke="{th["border"]}"/>
<rect x="1" y="{H_GAME}" width="{W - 2}" height="{H_TERM - 1}" rx="9" fill="{th["term"]}"/>
<line x1="0" y1="{H_GAME}" x2="{W}" y2="{H_GAME}" stroke="{th["border"]}"/>
{dots}
{blocks_svg(th, frames, nodge)}
{cells}
<text x="16" y="{H_GAME + 34}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14" fill="{th["prompt"]}">$</text>
{typing(th, rng)}
</svg>'''
    return svg, dur


def main():
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    frames, nodge = simulate(random.Random(SEED))
    for name, th in THEMES.items():
        svg, dur = build(th, frames, nodge)
        (outdir / f"snake-{name}.svg").write_text(svg, encoding="utf-8")
        print(name, f"{len(svg) / 1024:.0f} KB, loop {dur:.1f}s, {len(frames)} frames")


if __name__ == "__main__":
    main()
