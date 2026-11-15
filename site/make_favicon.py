"""Draw the site's icon: the arms of Samogitia, simplified (a black bear with a white collar on a red shield).

Usage: python3 site/make_favicon.py
Writes site/favicon.svg, site/favicon-32.png and site/apple-touch-icon.png (180 px, on the site's
background colour) from one list of shapes, so the three agree. It is our own flat drawing, made
to stay readable at 16 px, not a heraldic rendering. Needs Pillow for the two PNGs.
"""
from pathlib import Path

from PIL import Image, ImageDraw

SITE = Path(__file__).resolve().parent
RED, BLACK, WHITE, ROOM = '#b01f24', '#15110f', '#ffffff', '#d5d8cf'
# on a 64 x 64 field; the bear stands upright and faces left
SHIELD = [(6, 4), (58, 4), (58, 33)], [(58, 49), (45, 57), (32, 62)], [(19, 57), (6, 49), (6, 33)]   # corner points, then two cubic curves
SHAPES = [
    ('line', BLACK, 15, (36, 27), (38.5, 42)),      # body
    ('ellipse', BLACK, (26, 16.5), 8, 7),           # head
    ('line', BLACK, 6, (22, 18.5), (14.5, 20.5)),   # muzzle
    ('ellipse', BLACK, (30.5, 9.4), 3.2, 3.2),      # ear
    ('line', BLACK, 5.6, (32, 26), (17.5, 27.5)),   # upper forepaw
    ('line', BLACK, 5.6, (33, 33), (20, 37.5)),     # lower forepaw
    ('line', BLACK, 7, (36, 44), (28, 53)),         # hind legs
    ('line', BLACK, 7, (41, 44), (44, 54)),
    ('line', BLACK, 5, (27.5, 53.5), (23.5, 53.5)), # feet
    ('line', BLACK, 5, (43.5, 54.5), (39, 54.5)),
    ('line', WHITE, 3.8, (24, 25.4), (35, 20.6)),   # collar
]


def cubic(p0, p1, p2, p3, n=24):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d for a, b, c, d in zip(p0, p1, p2, p3))
            for t in (i / n for i in range(1, n + 1))]


def svg():
    (a, b, c), (c1, c2, tip), (c3, c4, d) = SHIELD
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">',
           f'<path fill="{RED}" d="M{a[0]} {a[1]}H{b[0]}V{c[1]}C{c1[0]} {c1[1]} {c2[0]} {c2[1]} {tip[0]} {tip[1]}C{c3[0]} {c3[1]} {c4[0]} {c4[1]} {d[0]} {d[1]}Z"/>']
    for kind, colour, *r in SHAPES:
        if kind == 'line':
            w, p, q = r
            out.append(f'<path stroke="{colour}" stroke-width="{w}" stroke-linecap="round" fill="none" d="M{p[0]} {p[1]}L{q[0]} {q[1]}"/>')
        else:
            (cx, cy), rx, ry = r
            out.append(f'<ellipse fill="{colour}" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>')
    return '\n'.join(out) + '\n</svg>\n'


def png(size, background=None, inset=0):
    k = 8 * size / 64 * (1 - 2 * inset)             # drawn 8 times too large, then reduced
    o = 8 * size * inset
    P = lambda p: (o + p[0] * k, o + p[1] * k)
    im = Image.new('RGBA', (8 * size, 8 * size), background or (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    (a, b, c), (c1, c2, tip), (c3, c4, d) = SHIELD
    dr.polygon([P(p) for p in [a, b, c] + cubic(c, c1, c2, tip) + cubic(tip, c3, c4, d)], fill=RED)
    for kind, colour, *r in SHAPES:
        if kind == 'line':
            w, p, q = r
            dr.line([P(p), P(q)], fill=colour, width=round(w * k))
            for e in (p, q):
                x, y = P(e); dr.ellipse([x - w * k / 2, y - w * k / 2, x + w * k / 2, y + w * k / 2], fill=colour)
        else:
            (cx, cy), rx, ry = r
            x, y = P((cx, cy)); dr.ellipse([x - rx * k, y - ry * k, x + rx * k, y + ry * k], fill=colour)
    return im.resize((size, size), Image.LANCZOS)


if __name__ == '__main__':
    (SITE / 'favicon.svg').write_text(svg())
    png(32).save(SITE / 'favicon-32.png')
    png(180, ROOM, .1).convert('RGB').save(SITE / 'apple-touch-icon.png')
    print('favicon.svg, favicon-32.png, apple-touch-icon.png')
