#!/usr/bin/env python3
"""Generates self-playing snake SVGs (light + dark) with typing trash talk.
Pure SMIL/CSS animation: works inside <img>/<picture> on GitHub, no maintenance needed.
Usage: python generate_snake.py [outdir]
"""
import random
import sys
from collections import deque
from pathlib import Path

SEED = 97
CELL = 14
COLS, ROWS = 60, 14
W, H_GAME = COLS * CELL, ROWS * CELL
H_TERM = 56
H = H_GAME + H_TERM
STEP = 0.11  # seconds per move
FOODS_PER_GAME = (9, 16)
GAMES = 3
PAUSE = 14  # frozen steps after crash

# obstacle text blocks (col0, row0, cols, rows, lines)
BLOCKS = [
    (5, 2, 22, 3, [("tontsa97", 26, 700)]),
    (33, 6, 22, 3, [("FiveM · Lua · QBox", 17, 600)]),
    (8, 9, 17, 2, [("QBCore dev", 15, 600)]),
    (36, 1, 18, 2, [("Suomi 🇫🇮 · 1997", 14, 600)]),
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


def blocked_cells():
    s = set()
    for c0, r0, cw, rh, _ in BLOCKS:
        for c in range(c0, c0 + cw):
            for r in range(r0, r0 + rh):
                s.add((c, r))
    return s


OBST = blocked_cells()
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


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


def simulate(rng):
    """Returns list of frames; frame = dict cell -> state (1 body, 2 head, 3 food, 4 dead)."""
    frames = []
    for _ in range(GAMES):
        snake = deque([(1, 7), (0, 7)])  # head first
        snake = deque([(3, 12), (2, 12), (1, 12)])
        target = rng.randint(*FOODS_PER_GAME)
        eaten = 0

        def new_food():
            free = [(c, r) for c in range(COLS) for r in range(ROWS)
                    if (c, r) not in OBST and (c, r) not in snake]
            return rng.choice(free)

        food = new_food()
        crash_cell = None
        path = []
        dying = False
        guard = 0
        while crash_cell is None and guard < 4000:
            guard += 1
            frame = {c: 1 for c in snake}
            frame[snake[0]] = 2
            frame[food] = 3
            frames.append(frame)
            if not path:
                body = set(list(snake)[:-1])
                if eaten >= target:
                    dying = True
                    # head for the nearest wall/obstacle/body and slam into it
                    p = bfs(snake[0], lambda x: any(
                        (not inside((x[0] + d[0], x[1] + d[1]))) or (x[0] + d[0], x[1] + d[1]) in OBST
                        for d in DIRS), body | OBST)
                    if p is None:
                        p = []
                    path = p
                    if not path:
                        # already adjacent: pick a blocking direction
                        for d in DIRS:
                            n = (snake[0][0] + d[0], snake[0][1] + d[1])
                            if not inside(n) or n in OBST:
                                crash_cell = snake[0]
                                break
                        break
                else:
                    path = bfs(snake[0], lambda x: x == food, body | OBST) or []
                    if not path:
                        break
            nxt = path.pop(0)
            snake.appendleft(nxt)
            if nxt == food:
                eaten += 1
                food = new_food()
            else:
                snake.pop()
            if dying and not path:
                # final move into a blocking cell
                for d in DIRS:
                    n = (snake[0][0] + d[0], snake[0][1] + d[1])
                    if not inside(n) or n in OBST:
                        crash_cell = snake[0]
                        break
        # crash: snake turns red, flicker, hold
        dead = {c: 4 for c in snake}
        for i in range(PAUSE):
            f = dict(dead) if i % 2 == 0 else {c: 1 for c in snake}
            if i >= PAUSE - 4:
                f = {}
            frames.append(f)
    return frames


def fmt(x):
    return f"{x:.5f}".rstrip("0").rstrip(".") or "0"


def build_cells(frames, th):
    total = len(frames)
    dur = total * STEP
    colors = {0: "transparent", 1: th["body"], 2: th["head"], 3: th["food"], 4: th["dead"]}
    cells = {}
    for i, f in enumerate(frames):
        for c in f:
            cells.setdefault(c, None)
    out = []
    for (c, r) in sorted(cells):
        series = [frames[i].get((c, r), 0) for i in range(total)]
        kt, vals = [], []
        for i, s in enumerate(series):
            if not vals or vals[-1] != s:
                kt.append(i / total)
                vals.append(s)
        if len(vals) == 1:
            continue
        shape = (f'<rect x="{c * CELL + 1}" y="{r * CELL + 1}" width="{CELL - 2}" height="{CELL - 2}" '
                 f'rx="3" fill="transparent"><animate attributeName="fill" calcMode="discrete" dur="{fmt(dur)}s" '
                 f'repeatCount="indefinite" keyTimes="{";".join(fmt(k) for k in kt)}" '
                 f'values="{";".join(colors[v] for v in vals)}"/></rect>')
        out.append(shape)
    return "\n".join(out), dur


def typing(th, rng):
    cw, fs = 8.4, 14
    x0, y0 = 40, H_GAME + 34
    order = PHRASES[:]
    rng.shuffle(order)
    t = 0.0
    slots = []
    for p in order:
        t += rng.uniform(1.5, 4.0)  # idle gap
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
    # cursor: x position + visibility over the whole timeline
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
    # enforce monotonic keyTimes
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


def blocks_svg(th):
    out = []
    for c0, r0, cw, rh, lines in BLOCKS:
        x, y, w, h = c0 * CELL, r0 * CELL, cw * CELL, rh * CELL
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{th["block"]}" '
                   f'stroke="{th["border"]}" stroke-dasharray="3 3"/>')
        for txt, size, weight in lines:
            out.append(f'<text x="{x + w / 2}" y="{y + h / 2}" text-anchor="middle" dominant-baseline="central" '
                       f'font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="{size}" '
                       f'font-weight="{weight}" fill="{th["btxt"]}">{txt}</text>')
    return "\n".join(out)


def build(name, th, frames):
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
{blocks_svg(th)}
{cells}
<text x="16" y="{H_GAME + 34}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14" fill="{th["prompt"]}">$</text>
{typing(th, rng)}
</svg>'''
    return svg, dur


def main():
    outdir = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    outdir.mkdir(parents=True, exist_ok=True)
    frames = simulate(random.Random(SEED))
    for name, th in THEMES.items():
        svg, dur = build(name, th, frames)
        (outdir / f"snake-{name}.svg").write_text(svg, encoding="utf-8")
        print(name, f"{len(svg) / 1024:.0f} KB, loop {dur:.1f}s, {len(frames)} frames")


if __name__ == "__main__":
    main()

