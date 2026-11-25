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
COLS, ROWS = 60, 20
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
BLOCKS = [
    (3, 2, 28, 5, "I started my coding journey from scratch, learning Lua programming through YouTube tutorials and Discord forums."),
    (32, 2, 27, 5, "Over the past 5 years, I've been immersed in Lua coding, honing my skills and expanding my knowledge."),
    (3, 10, 28, 5, "I also use AI tools to aid in learning and development, making the most of modern technology."),
    (33, 11, 26, 3, "So don't wait up, because I'm on a mission."),
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
        snake = deque([(3, 8), (2, 8), (1, 8)])
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


def blocks_svg(th, frames, nodge):
    total = len(frames)
    dur = fmt(total * STEP)
    # snake columns on each gate row, per frame
    gate_cols = []
    for f in frames:
        per = {}
        for (c, r), s in f.items():
            bi = GATE.get((c, r))
            if bi is not None and s != 3:
                per.setdefault(bi, []).append(c)
        gate_cols.append(per)
    font = "ui-monospace,SFMono-Regular,Consolas,Menlo,monospace"
    out = []
    for bi, (c0, r0, cw, rh, text) in enumerate(BLOCKS):
        x, y, w, h = c0 * CELL, r0 * CELL, cw * CELL, rh * CELL
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{th["block"]}" '
                   f'stroke="{th["border"]}" stroke-dasharray="3 3"/>')
        lines = textwrap.wrap(text, 44)
        mid = len(lines) // 2
        gy = gate_row(BLOCKS[bi]) * CELL + CELL / 2
        for k, ln in enumerate(lines):
            n = len(ln)
            ty = gy + (k - mid) * LH
            left = x + w / 2 - n * ADV / 2
            for i, ch in enumerate(ln):
                if ch == " ":
                    continue
                tx = left + i * ADV + ADV / 2
                anim = ""
                if k == mid:
                    lc = int(tx // CELL)
                    near = [0 if bi in nodge[t] else
                            int(any(abs(c - lc) <= NEAR for c in gate_cols[t].get(bi, ())))
                            for t in range(total)]
                    if any(near):
                        kp = letter_keyframes(near)
                        kts = ";".join(fmt(t / total) for t, _ in kp)
                        dy = -9 if (i + k) % 2 == 0 else 9
                        dx = 3 if i % 2 == 0 else -3
                        tv = ";".join(f"{dx} {dy}" if s else "0 0" for _, s in kp)
                        ov = ";".join("0.15" if s else "1" for _, s in kp)
                        anim = (f'<animateTransform attributeName="transform" type="translate" dur="{dur}s" '
                                f'repeatCount="indefinite" keyTimes="{kts}" values="{tv}"/>'
                                f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
                                f'keyTimes="{kts}" values="{ov}"/>')
                ch = ch.replace("&", "&amp;").replace("<", "&lt;")
                out.append(f'<text x="{fmt(tx)}" y="{fmt(ty)}" text-anchor="middle" dominant-baseline="central" '
                           f'font-family="{font}" font-size="13" font-weight="600" fill="{th["btxt"]}">{ch}{anim}</text>')
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
                   for c in range(COLS) for r in range(ROWS) if (c, r) not in OBST)
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
