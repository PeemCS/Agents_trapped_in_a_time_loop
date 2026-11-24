"""Local illustrated stage for the Rialto film. All positions and physical beats are reconstructions."""

from functools import lru_cache
import math
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1280, 720
FONT = Path("/System/Library/Fonts/Supplemental")


@lru_cache(maxsize=32)
def font(size=22, bold=False, serif=False):
    return ImageFont.truetype(
        str(
            FONT
            / ("Georgia.ttf" if serif else "Arial Bold.ttf" if bold else "Arial.ttf")
        ),
        size,
    )


def grad(top, bottom, size=(1280, 570)):
    a = tuple(bytes.fromhex(top))
    b = tuple(bytes.fromhex(bottom))
    im = Image.new("RGB", size)
    d = ImageDraw.Draw(im)
    for y in range(size[1]):
        t = y / (size[1] - 1)
        d.line(
            (0, y, size[0], y),
            fill=tuple(round(x * (1 - t) + z * t) for x, z in zip(a, b)),
        )
    return im


def sign(d, x, y, text, small=False):
    f = font(14 if small else 23, True)
    box = d.textbbox((0, 0), text, font=f)
    w = box[2] + 34
    d.rounded_rectangle(
        (x, y, x + w, y + (34 if small else 48)),
        5,
        fill="#132e36",
        outline="#809295",
        width=2,
    )
    d.text((x + 17, y + (8 if small else 10)), text, font=f, fill="#f2d796")


def person(d, x, y, scale, who="Phil", pose="stand", walk=0):
    def xy(k):
        return (round(x + k[0] * scale), round(y + k[1] * scale))

    def poly(pts, c):
        d.polygon([xy(p) for p in pts], fill=c)

    def line(pts, c, w):
        d.line(
            [xy(p) for p in pts], fill=c, width=max(1, round(w * scale)), joint="curve"
        )

    def oval(box, c):
        d.ellipse((*xy(box[:2]), *xy(box[2:])), fill=c)

    coat, collar, hair, skin = {
        "Phil": ("#784733", "#d69563", "#3d2d2b", "#d19d7c"),
        "Rita": ("#16636b", "#d4a047", "#4e332c", "#cc9e84"),
        "Larry": ("#8c683e", "#d8b67a", "#584331", "#d9ab8b"),
        "Alma": ("#70576d", "#d4b4a6", "#bcb2a2", "#c59c82"),
    }[who]
    if pose == "sleep":
        oval((-57, -7, 112, 7), "#263338")
        poly([(-38, -5), (57, -8), (49, -22), (-12, -29), (-37, -20)], coat)
        line([(47, -15), (81, -11), (101, -7)], "#25343c", 10)
        oval((-46, -35, -18, -12), skin)
        line([(-47, -27), (-42, -35), (-26, -34)], hair, 8)
        return
    oval((-36, -5, 40, 7), "#394449")
    a = math.sin(walk) * 11 if walk and pose != "play" else 0
    if pose == "sit":
        line([(-8, -35), (-29, -26), (-28, -3)], "#28373c", 9)
        line([(4, -32), (7, -18), (18, -1)], "#34434a", 10)
    else:
        line([(-8, -39), (-11 - a, -3)], "#26333a", 10)
        line([(5, -39), (12 + a, -2)], "#37454b", 11)
    poly([(-14, -78), (6, -80), (19, -66), (22, -35), (-23, -34), (-22, -62)], coat)
    poly([(-10, -78), (2, -66), (8, -79)], collar)
    line([(-3, -69), (-3, -40)], "#4d4340", 2)
    if who == "Rita":
        poly([(-8, -77), (-15, -65), (-22, -37), (-11, -40), (-6, -65)], collar)
    oval((-14, -103, 11, -75), skin)
    poly(
        [
            (-15, -91),
            (-13, -101),
            (-2, -108),
            (9, -103),
            (13, -97),
            (4, -96),
            (-4, -98),
        ],
        hair,
    )
    if who == "Alma":
        oval((-23, -100, -9, -85), hair)
    direction = -1 if pose in ("play", "record", "mic") else 1
    line([(direction * 6, -93), (direction * 8, -93)], "#5b4942", 1.6)
    line([(direction * 7, -84), (direction * 3, -83)], "#a47160", 1.3)
    if pose in ("record", "phone", "play", "offer", "deliver", "mic"):
        hand = {
            "record": (-27, -67),
            "mic": (-32, -62),
            "deliver": (37, -54),
            "phone": (9, -91),
            "play": (-37, -62 + 2 * math.sin(walk)),
            "offer": (40, -58),
        }[pose]
        if pose == "play":
            line([(-12, -71), (-18, -58), (-43, -62 - 2 * math.sin(walk))], collar, 5)
        line([(direction * 13, -70), (direction * 23, -56), hand], coat, 9)
        oval((hand[0] - 4, hand[1] - 4, hand[0] + 4, hand[1] + 4), skin)
        if pose == "phone":
            line([(9, -97), (14, -94), (14, -84), (9, -82)], "#1d3337", 5)
        if pose == "record":
            poly([(-20, -77), (-33, -77), (-33, -67), (-21, -67)], "#29383c")
            poly([(-33, -75), (-39, -78), (-39, -66), (-33, -68)], "#2c3c40")
        if pose == "mic":
            line([(-31, -62), (-41, -68)], "#3f4541", 3)
            oval((-47, -74, -39, -66), "#2b3637")
        if pose == "deliver":
            oval((32, -64, 55, -42), "#c5bea1")
            for dx, dy in ((36, -53), (45, -60), (49, -50)):
                oval((dx, dy, dx + 4, dy + 4), "#405052")
    else:
        line([(12, -72), (18, -53), (14, -46)], coat, 8)
        oval((11, -49, 17, -43), skin)


def window(d, x, y, w, h, night=False):
    d.rectangle((x - 8, y - 8, x + w + 8, y + h + 8), fill="#6d5547")
    d.rectangle((x, y, x + w, y + h), fill="#2d5160" if night else "#a1b3b0")
    for j in range(5):
        xx = x + j * w / 4 - 15
        d.polygon(
            [
                (xx, y + h),
                (xx + 4, y + h - 32),
                (xx + 8, y + h - 59),
                (xx + 13, y + h - 26),
                (xx + 22, y + h),
            ],
            fill="#607c78",
        )
    d.line((x + w / 2, y, x + w / 2, y + h), width=6, fill="#796453")
    d.line((x, y + h * 0.55, x + w, y + h * 0.55), width=5, fill="#796453")
    d.polygon(
        [(x - 13, y - 12), (x + 38, y - 12), (x + 12, y + h), (x - 11, y + h)],
        fill="#8d604a",
    )
    d.polygon(
        [
            (x + w - 20, y - 12),
            (x + w + 11, y - 12),
            (x + w + 12, y + h),
            (x + w - 7, y + h),
        ],
        fill="#8d604a",
    )


def reel(d, x, y, r, angle):
    d.ellipse((x - r, y - r, x + r, y + r), fill="#bcc0ac", outline="#283b3a", width=5)
    for j in range(5):
        a = angle + 2 * math.pi * j / 5
        xx = x + r * 0.57 * math.cos(a)
        yy = y + r * 0.57 * math.sin(a)
        z = r * 0.18
        d.ellipse((xx - z, yy - z, xx + z, yy + z), fill="#364747")
    d.ellipse((x - 4, y - 4, x + 4, y + 4), fill="#2e3a39")


def set_stage(scene, t, who, action, other=False):
    palette = {
        "town": ("486979", "d3cfb9"),
        "terminal": ("253d47", "aab0a2"),
        "ballroom": ("613f44", "bb9275"),
        "Rialto": ("273b48", "8b7a65"),
        "patch": ("253944", "6f7975"),
        "hotel": ("605753", "c1ab88"),
        "roadside": ("537586", "d2d6bc"),
        "coat_check": ("4c5250", "99896e"),
        "archive": ("24363c", "4c6463"),
        "depot": ("253f54", "a39976"),
    }
    im = grad(*palette[scene])
    d = ImageDraw.Draw(im)
    if scene in ("town", "roadside"):
        d.ellipse((996, 70, 1060, 134), fill="#eac79a")
        for k in range(2):
            base = 284 + 45 * k
            pts = (
                [(-80, base + 10)]
                + [
                    (x, base - 48 * math.sin(x / 185 + k) - 15 * math.cos(x / 57 + k))
                    for x in range(0, 1381, 50)
                ]
                + [(1380, 450), (-80, 450)]
            )
            d.polygon(pts, fill=["#78908c", "#627f7c"][k])
        for j in range(11):
            x = j * 125 - 50
            y = 314 + 12 * math.sin(j * 2)
            h = 65 + 20 * (j % 3)
            d.rectangle(
                (x, y, x + 107, y + h), fill=["#92867a", "#7b7c72", "#8c8074"][j % 3]
            )
            d.polygon([(x - 8, y), (x + 45, y - 36), (x + 117, y)], fill="#d4d2bb")
            for a in range(3):
                d.rectangle(
                    (x + 15 + a * 27, y + 15, x + 26 + a * 27, y + 39), fill="#cbba91"
                )
        d.polygon([(0, 430), (1280, 383), (1280, 570), (0, 570)], fill="#b8c3b6")
        d.polygon([(0, 466), (1280, 402), (1280, 474), (0, 560)], fill="#616b68")
        if scene == "town":
            x = int(-145 + 1260 * t)
            yy = round(450 - x * 0.046)
            d.rounded_rectangle(
                (x, yy - 55, x + 219, yy + 7),
                13,
                fill="#b98b53",
                outline="#354b4c",
                width=3,
            )
            d.rounded_rectangle((x + 10, yy - 47, x + 206, yy - 20), 4, fill="#2f505b")
            for j in range(8):
                d.line(
                    (x + 15 + 24 * j, yy - 46, x + 15 + 24 * j, yy - 19),
                    fill="#d7bc88",
                    width=3,
                )
            for dx in (36, 178):
                d.ellipse((x + dx - 12, yy - 7, x + dx + 12, yy + 17), fill="#243337")
                d.ellipse((x + dx - 5, yy, x + dx + 5, yy + 10), fill="#8d9692")
            sign(d, 43, 297, "PITTSBURGH  →")
        else:
            d.rounded_rectangle((530, 347, 845, 423), 18, fill="#627779")
            d.polygon([(580, 348), (625, 301), (733, 300), (798, 347)], fill="#55717c")
            d.ellipse((576, 392, 627, 443), fill="#253335")
            d.ellipse((764, 397, 812, 431), fill="#2d3736")
            person(d, 835, 455, 1.35, who, "sit")
    elif scene == "coat_check":
        # Close angle over the unattended counter. The drawing never assigns a dollar amount.
        for x in [80, 240, 400, 560, 720]:
            d.line((x, 130, x, 153), fill="#bb9c72", width=5)
            d.arc((x - 11, 141, x + 11, 163), 0, 180, fill="#b8a985", width=4)
        d.line((54, 122, 764, 122), fill="#a89372", width=7)
        for x, c in [(102, "#5f7069"), (310, "#574c4d"), (646, "#717a6e")]:
            d.polygon(
                [
                    (x, 169),
                    (x + 25, 155),
                    (x + 46, 167),
                    (x + 70, 197),
                    (x + 59, 271),
                    (x + 47, 256),
                    (x + 49, 299),
                    (x - 16, 299),
                    (x - 10, 251),
                    (x - 27, 266),
                    (x - 33, 203),
                ],
                fill=c,
            )
        sign(d, 67, 67, "HEARTHSIDE    /    COAT CHECK")
        d.polygon([(0, 307), (1280, 244), (1280, 570), (0, 570)], fill="#866c56")
        d.polygon([(0, 358), (1280, 298), (1280, 506), (0, 563)], fill="#a48968")
        for j in range(10):
            y = 344 + j * 21
            d.line((0, y, 830, y - 39), fill="#a18361", width=2)
        # Coat, seam and deep side pocket occupy the right foreground.
        d.polygon(
            [
                (961, 118),
                (1068, 83),
                (1238, 94),
                (1280, 120),
                (1280, 570),
                (875, 570),
                (906, 277),
            ],
            fill="#6f4538",
        )
        d.polygon(
            [(953, 135), (1009, 117), (987, 243), (935, 288), (918, 195)],
            fill="#996c50",
        )
        d.polygon([(1081, 104), (1191, 108), (1141, 194), (1098, 195)], fill="#b1845e")
        d.line((1081, 201, 1010, 570), fill="#4e3933", width=5)
        d.polygon([(950, 340), (1115, 329), (1093, 438), (947, 459)], fill="#79513d")
        d.line((952, 350, 1113, 337), fill="#3d3430", width=13)
        # The open envelope's interior remains visible after the transfer.
        d.polygon(
            [(194, 312), (519, 302), (498, 221), (343, 185), (208, 227)],
            fill="#cfb88c",
            outline="#766749",
        )
        d.polygon(
            [(191, 313), (520, 303), (527, 438), (200, 452)],
            fill="#b8a178",
            outline="#776850",
        )
        d.polygon([(191, 313), (520, 303), (492, 337), (224, 347)], fill="#776e57")

        def ease(v):
            v = min(1, max(0, v))
            return v * v * (3 - 2 * v)

        move = ease((t - 0.31) / 0.42)
        cx = 359 + 673 * move
        cy = 302 - 99 * math.sin(move * math.pi) + 50 * move
        if t < 0.78:
            d.polygon(
                [
                    (cx - 39, cy - 7),
                    (cx + 42, cy - 15),
                    (cx + 46, cy + 12),
                    (cx - 35, cy + 20),
                ],
                fill="#8c9e84",
                outline="#50645d",
                width=3,
            )
            d.polygon(
                [
                    (cx - 35, cy - 10),
                    (cx + 40, cy - 20),
                    (cx + 43, cy + 8),
                    (cx - 31, cy + 16),
                ],
                fill="#a7b498",
                outline="#5a705e",
                width=2,
            )
            d.ellipse((cx - 5, cy - 8, cx + 10, cy + 6), outline="#657b65", width=2)
        d.polygon(
            [(192, 324), (347, 372), (521, 315), (527, 438), (200, 452)],
            fill="#dbc49b",
            outline="#8d795b",
            width=2,
        )
        d.text((235, 384), "CREW RETURN FARES", font=font(22, True), fill="#4f5145")
        approach = ease(t / 0.24)
        release = ease((t - 0.77) / 0.23)
        hx = cx + 8 + (1 - approach) * 265 + release * 135
        hy = cy - 18 - (1 - approach) * 71 - release * 59
        d.polygon(
            [
                (hx + 160, hy - 76),
                (hx + 217, hy - 16),
                (hx + 38, hy + 25),
                (hx + 8, hy - 10),
            ],
            fill="#80533f",
            outline="#674438",
        )
        d.polygon(
            [
                (hx + 21, hy - 12),
                (hx + 49, hy + 13),
                (hx + 27, hy + 29),
                (hx + 7, hy + 10),
            ],
            fill="#b28c66",
        )
        d.polygon(
            [
                (hx + 21, hy + 1),
                (hx + 29, hy + 18),
                (hx - 2, hy + 31),
                (hx - 26, hy + 27),
                (hx - 31, hy + 19),
                (hx - 12, hy + 3),
            ],
            fill="#cb9a76",
            outline="#a6785c",
        )
        d.line((hx - 23, hy + 20, hx - 2, hy + 24), fill="#ac7d61", width=2)
    elif scene == "depot":
        d.ellipse((960, 59, 1012, 111), fill="#d6c7a5")
        d.polygon(
            [
                (0, 291),
                (135, 246),
                (257, 282),
                (459, 220),
                (680, 268),
                (890, 215),
                (1280, 280),
                (1280, 470),
                (0, 470),
            ],
            fill="#49636a",
        )
        d.polygon([(0, 374), (1280, 327), (1280, 402), (0, 468)], fill="#536365")
        d.polygon([(0, 423), (1280, 370), (1280, 570), (0, 570)], fill="#a5aaa0")
        for x in (239, 870):
            d.line((x, 176, x, 428), fill="#384c4b", width=12)
        d.polygon([(135, 171), (902, 144), (972, 170), (181, 210)], fill="#36505a")
        sign(d, 460, 186, "LOCAL COACH DEPOT")
        for yy in (347, 367, 387):
            d.rounded_rectangle((406, yy, 784, yy + 11), 4, fill="#7d6551")
        for xx in (433, 756):
            d.line((xx, 397, xx - 6, 447), fill="#3c4a49", width=9)
        person(d, 587, 409, 1.31, who, "sit")
    elif scene == "terminal":
        d.rectangle((0, 0, 1280, 65), fill="#263d46")
        d.polygon([(0, 399), (1280, 360), (1280, 570), (0, 570)], fill="#65746e")
        for x in range(80, 1000, 148):
            window(d, x, 166, 111, 127, True)
        sign(d, 422, 66, "PITTSBURGH   ·   BUS TERMINAL")
        for x in range(82, 1250, 265):
            d.line((x, 489, x + 105, 570), fill="#596965", width=2)
        x, y = 432, 397
        d.rounded_rectangle((x, y - 32, x + 324, y - 9), 5, fill="#80674f")
        d.rounded_rectangle((x - 7, y - 3, x + 338, y + 12), 4, fill="#977b5e")
        for xx in [x + 20, x + 294]:
            d.line((xx, y + 11, xx - 5, y + 47), fill="#3b4845", width=7)
        d.rectangle((945, 251, 1029, 391), fill="#354b4b", outline="#ad9d77", width=4)
        d.rectangle((959, 275, 1007, 353), fill="#83918b")
        for row in range(3):
            for col in range(3):
                d.rectangle(
                    (975 + col * 7, 318 + row * 7, 978 + col * 7, 321 + row * 7),
                    fill="#334845",
                )
        if action == "sleep_at_terminal":
            person(d, 536, 394, 1.48, who, "sleep")
        elif action == "call_sister":
            person(d, 921, 451, 1.73, who, "phone")
        elif action == "arrive_terminal":
            person(d, 292 + 130 * t, 452, 1.53, who, "stand", t * 8)
        else:
            person(d, 589, 420, 1.47, who, "sit")
    elif scene == "Rialto":
        d.rectangle((0, 362, 1280, 570), fill="#504c45")
        d.rectangle((756, 80, 1183, 332), fill="#1c2b31", outline="#ad9772", width=5)
        d.polygon([(780, 99), (1163, 99), (1163, 295), (780, 295)], fill="#aeb1a0")
        d.rectangle((783, 104, 1159, 293), fill="#98a69b")
        sign(d, 47, 102, "RIALTO    /    PROJECTION")
        d.polygon(
            [(281, 278), (326, 280), (770, 114), (770, 290), (324, 304)], fill="#aaa38c"
        )
        d.rounded_rectangle(
            (151, 239, 332, 348), 11, fill="#31434a", outline="#b49b76", width=4
        )
        d.polygon([(327, 264), (361, 254), (361, 289), (327, 281)], fill="#334246")
        reel(d, 195, 214, 54, -t * 1.8)
        reel(d, 293, 210, 46, -t * 1.8)
        d.rectangle((188, 344, 287, 413), fill="#313e3e")
        d.line((146, 418, 326, 418), width=11, fill="#313b3b")
        person(d, 761, 452, 1.58, "Alma", "sit")
        person(
            d,
            879,
            466,
            1.69,
            who,
            (
                "record"
                if action == "film_Alma"
                else "mic"
                if action in ("interview_Alma", "record_Alma")
                else "stand"
            ),
        )
        if other:
            person(d, 965, 470, 1.55, "Larry", "record")
    elif scene == "patch":
        d.rectangle((0, 364, 1280, 570), fill="#475a58")
        sign(d, 64, 76, "REGIONAL LINE    /    STATION")
        for j in range(3):
            x = 133 + j * 134
            d.rounded_rectangle(
                (x, 173, x + 110, 331), 6, fill="#293d40", outline="#9f9c7d", width=3
            )
            for y in range(200, 300, 22):
                for q in range(4):
                    d.ellipse(
                        (x + 18 + q * 20, y, x + 27 + q * 20, y + 9),
                        fill="#dcc67e" if (j + q) % 4 == 1 else "#647b75",
                    )
        d.polygon([(453, 359), (974, 341), (1102, 396), (533, 443)], fill="#998875")
        d.polygon([(531, 442), (1102, 395), (1102, 453), (531, 499)], fill="#535b52")
        for j in range(5):
            yy = 369 + 4 * j
            d.line((559, yy + 17, 854, yy - 7), fill="#334745", width=4)
        reel(d, 965, 347, 35, t * 0.9)
        person(
            d,
            689,
            474,
            1.59,
            who,
            "phone" if action == "transmit_interview" else "deliver",
        )
    elif scene == "ballroom":
        d.rectangle((0, 346, 1280, 570), fill="#9c7657")
        for z in range(15):
            d.line((100 + z * 88, 348, (-200 + z * 125), 570), width=2, fill="#8a6c53")
        for x in (60, 370, 680, 990):
            window(d, x, 100, 186, 170, True)
        for x in range(50, 1250, 90):
            d.ellipse(
                (x, 46 + 20 * math.sin(x / 180), x + 10, 55 + 20 * math.sin(x / 180)),
                fill="#efd199",
            )
        d.polygon(
            [(90, 300), (388, 290), (478, 330), (399, 378), (109, 388)], fill="#293537"
        )
        d.polygon([(105, 310), (328, 179), (405, 298)], fill="#354143")
        for j in range(17):
            d.line((302 + j * 7, 354, 308 + j * 7, 360), fill="#e9dfc3", width=6)
        for x in (148, 388):
            d.line((x, 381, x - 10, 440), fill="#273137", width=10)
        if action in ("rehearse_piano", "play_piano"):
            person(d, 439, 443, 1.4, who, "play", t * 13)
        else:
            person(
                d,
                730 + (18 * math.sin(t * 6) if action == "go_dancing" else 0),
                447,
                1.56,
                who,
                "offer" if action == "ask_Rita_to_dance" else "stand",
                t * 10 if action == "go_dancing" else 0,
            )
        if other:
            person(d, 802, 443, 1.49, "Rita", "offer")
    elif scene == "hotel":
        d.rectangle((0, 358, 1280, 570), fill="#83705e")
        window(d, 75, 105, 329, 186)
        sign(d, 683, 73, "HEARTHSIDE    /    HOTEL")
        d.rectangle((424, 305, 940, 395), fill="#7b5140")
        d.rectangle((440, 295, 918, 350), fill="#d5ccae")
        d.polygon([(522, 307), (935, 311), (970, 382), (544, 374)], fill="#547579")
        d.rectangle((983, 263, 1127, 280), fill="#684e40")
        d.rectangle((999, 278, 1116, 369), fill="#896952")
        d.rounded_rectangle(
            (1005, 213, 1093, 256), 4, fill="#283e41", outline="#b4a583", width=3
        )
        d.text((1015, 221), "6:00", font=font(19, True), fill="#e2bd7e")
        if action not in ("stay_in_bed", "go_to_bed", "wake"):
            person(d, 743, 447, 1.55, who)
        if action in ("stay_in_bed", "go_to_bed"):
            person(d, 562, 325, 1.0, who, "sleep")
    elif scene == "archive":
        d.rectangle((147, 126, 1124, 407), fill="#384d4e", outline="#acaa91", width=4)
        d.rectangle((217, 181, 1005, 347), fill="#c2aa7d", outline="#273e40", width=5)
        d.line((222, 187, 606, 307, 998, 187), fill="#8c795e", width=4)
    return im
