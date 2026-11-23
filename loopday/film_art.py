"""Original low-poly sets for the browser and offline film renderers."""

from __future__ import annotations

from typing import Any


SNOW = "#c7d8e3"
ICE = "#6f93a5"
WOOD = "#744d3b"
WARM = "#ffce87"


def box(name: str, x: float, y: float, z: float, w: float, h: float, d: float,
        color: str, *, shape: str = "box", yaw: float = 0, emissive: bool = False) -> dict:
    return {"name": name, "p": [x, y, z], "s": [w, h, d], "color": color,
            "shape": shape, "yaw": yaw, "emissive": emissive}


def _window(prefix: str, x: float, y: float, z: float, width: float = 1.22) -> list[dict]:
    return [
        box(prefix + "_frame", x, y, z, width + .14, 1.32, .13, "#ecdcc4"),
        box(prefix + "_glass", x, y, z + .078, width, 1.17, .033, WARM, emissive=True),
        box(prefix + "_cross", x, y, z + .108, width, .048, .025, WOOD),
        box(prefix + "_upright", x, y, z + .109, .048, 1.16, .025, WOOD),
        box(prefix + "_sill", x, y - .69, z + .15, width + .26, .13, .23, SNOW),
    ]


def _house(name: str, x: float, z: float, facade: str, roof: str, width: float = 5.1) -> list[dict]:
    shapes = [
        box(name, x, 1.79, z, width, 3.58, 3.35, facade),
        box(name + "_pediment", x, 4.18, z, width + .34, 1.39, 3.58, roof, shape="gable"),
        box(name + "_snow", x, 4.31, z, width + .4, 1.32, 3.70, SNOW, shape="gable"),
        box(name + "_door", x, .99, z + 1.715, .85, 1.98, .12, "#2b3b3e"),
        box(name + "_lintel", x, 2.07, z + 1.79, 1.18, .13, .23, "#e2c4a4"),
        box(name + "_step", x, .055, z + 1.92, 1.45, .11, .59, SNOW),
        box(name + "_cornice", x, 3.53, z + 1.70, width + .17, .18, .22, "#e1bca0"),
        box(name + "_base", x, .285, z + 1.67, width, .13, .10, "#746c61"),
        box(name + "_chimney", x + width * .24, 4.31, z - .94, .54, 1.4, .56, "#7a655f"),
        box(name + "_chimney_cap", x + width * .24, 5.04, z - .94, .66, .14, .64, SNOW),
    ]
    for i, dx in enumerate((-.31 * width, .31 * width)):
        shapes.extend(_window(f"{name}_w{i}", x + dx, 2.08, z + 1.705, width * .18))
    return shapes


def _pine(name: str, x: float, z: float, height: float = 3.9) -> list[dict]:
    shapes = [box(name + "_trunk", x, .48, z, .22, .96, .22, "#594535")]
    for i, color in enumerate(("#233f43", "#31514c", "#53736c")):
        size = height * (.49 - .095 * i)
        shapes.append(box(f"{name}_{i}", x, height * (.42 + .21 * i), z, size, height * .44,
                          size, color, shape="cone"))
        shapes.append(box(f"{name}_cap{i}", x, height * (.487 + .21 * i), z, size * .74,
                          height * .36, size * .74, SNOW, shape="cone"))
    return shapes


def _lamp(name: str, x: float, z: float) -> list[dict]:
    return [
        box(name + "_post", x, 1.48, z, .11, 2.93, .11, "#455354"),
        box(name + "_arm", x + .25, 2.86, z, .53, .07, .077, "#455354"),
        box(name + "_bulb", x + .49, 2.73, z, .34, .21, .30, WARM, emissive=True),
        box(name + "_top", x + .49, 2.89, z, .47, .12, .42, "#455354"),
    ]


def _ground(color: str) -> list[dict]:
    return [box("ground", 0, -.099, 0, 56, .13, 52, color)]


def _street() -> list[dict]:
    shapes = _ground(SNOW)
    shapes.extend([
        box("road", 0, -.012, .35, 30, .014, 3.88, "#657b85"),
        box("sidewalk", 0, .04, -2.15, 31, .08, 1.57, "#a0b4bd"),
        box("curb", 0, .07, -1.27, 33, .14, .11, "#e1e9e8"),
        box("puddle", -1.40, .01, 1.03, 1.74, .016, .86, ICE, shape="disc"),
        box("puddle_reflection", -1.43, .021, 1.02, 1.26, .008, .51, "#a8c1c5", shape="disc"),
        box("chair", 3.2, .4, -2.55, 1.25, .12, .42, WOOD),
        box("chair_back", 3.2, .69, -2.76, 1.25, .43, .09, WOOD),
    ])
    shapes.extend(_house("diner", -3.05, -5.4, "#9c6058", "#344650"))
    shapes.extend(_house("store", 2.46, -5.47, "#c49874", "#4f514d"))
    shapes.extend(_house("store2", 8.4, -5.65, "#6b9090", "#42565c"))
    shapes.extend(_house("store3", -9.02, -5.62, "#bfad96", "#61555e"))
    for i in range(8):
        x = -14 + i * 4.2
        shapes.append(box(f"snowbank_{i}", x, .038, 3.18 + i % 3 * .23, 4.0, .16, 1.22, "#dce4e7",
                          shape="disc", yaw=i * .27))
    for i, (x, z) in enumerate(((-16.2, -12.3), (13.8, -14.2), (16.9, -10.3), (-17.2, -4.3), (19.4, -16.1))):
        shapes.extend(_pine(f"street_backdrop_{i}", x, z, 5.0 + i % 2 * 1.5))
    shapes.extend([
        box("diner_awning", -3.05, 2.83, -3.45, 2.50, .23, .77, "#526a6d"),
        box("diner_awning_edge", -3.05, 2.74, -3.06, 2.52, .065, .08, WARM, emissive=True),
        box("diner_awning_snow", -3.05, 2.98, -3.40, 2.4, .083, .67, SNOW),
        box("town_noticeboard", 5.31, 1.30, -2.74, .67, .97, .15, "#785e50"),
        box("town_post", 5.31, .43, -2.74, .10, 1.21, .10, "#69534b"),
    ])
    for i, x in enumerate((-6.5, 5.2, 10.6)):
        shapes.extend(_lamp(f"street_lamp{i}", x, -2.86))
    for i, x in enumerate((-11.2, 12.8)):
        shapes.extend(_pine(f"street_pine{i}", x, -2.9, 3.6 + i * .8))
    return shapes


def _bedroom() -> list[dict]:
    shapes = _ground("#92705a")
    shapes.extend([
        box("wall_back", 0, 2.65, -3.3, 11.8, 5.3, .18, "#b3a391"),
        box("wall_left", -5.85, 2.65, -1.17, .17, 5.3, 4.26, "#968577"),
        box("rail", 0, .64, -3.15, 11.8, .16, .14, "#6d534c"),
        box("window", -2.48, 2.72, -3.18, 2.43, 2.28, .15, "#736355"),
        box("winter_window", -2.48, 2.72, -3.08, 2.25, 2.13, .074, "#83abbe", emissive=True),
        box("winter_window_vertical", -2.48, 2.72, -3.03, .087, 2.11, .057, "#a3957a"),
        box("winter_window_horizontal", -2.48, 2.72, -3.03, 2.26, .077, .055, "#a3957a"),
        box("curtain_left", -3.85, 2.64, -2.92, .35, 2.62, .17, "#4e6e70"),
        box("curtain_right", -1.11, 2.64, -2.92, .35, 2.62, .17, "#4e6e70"),
        box("bed_base", -2.35, .35, -.70, 2.73, .56, 3.47, "#4f372f"),
        box("bed_mattress", -2.35, .69, -.70, 2.67, .23, 3.33, "#ddd3bf"),
        box("bed_cover", -2.35, .84, -.34, 2.75, .12, 2.63, "#557d80"),
        box("bed_strip", -2.35, .91, .44, 2.74, .032, .33, "#a8996f"),
        box("bed_pillow", -2.35, .88, -1.82, 1.21, .21, .65, "#e7d5b8"),
        box("bed_head", -2.35, .77, -2.35, 2.79, 1.54, .19, "#63483a"),
        box("nightstand", .12, .60, -.31, 1.46, 1.18, 1.10, "#6e4937"),
        box("tabletop", .12, 1.23, -.31, 1.57, .12, 1.21, "#ad7c55"),
        box("drawer", .12, .73, .248, 1.23, .36, .077, "#7b5945"),
        box("drawer_handle", .12, .73, .296, .20, .044, .051, "#dbad73"),
        box("radio_base", -.04, 1.45, -.39, .96, .39, .48, "#302c29"),
        box("radio_border", -.04, 1.46, -.139, .76, .27, .08, "#6e4e3e"),
        box("radio_screen", -.04, 1.46, -.091, .69, .21, .025, "#312824"),
        box("radio_band", -.04, 1.651, -.49, .79, .027, .11, "#5f4a40"),
        box("radio_button", .28, 1.67, -.25, .17, .044, .11, "#96816a"),
        box("pencil_left", .31, 1.325, .085, .36, .055, .055, "#eaa74b"),
        box("pencil_right", .67, 1.325, .085, .36, .055, .055, "#eaa74b"),
        box("pencil_tip", .84, 1.325, .085, .04, .045, .046, "#574136"),
        box("room_light", 1.34, .069, -2.29, 3.52, .015, 1.75, "#bc9a73", yaw=-.13),
        box("rug", -1.45, .012, 1.31, 5.1, .02, 1.91, "#81534e"),
        box("rug_stripe", -1.45, .024, 1.29, 4.88, .006, 1.57, "#9c6b61"),
        box("skirting", 0, .155, -3.151, 11.8, .28, .07, "#775d51"),
        box("frame", .93, 2.71, -3.15, .87, .68, .10, "#79625d"),
        box("winter_print", .93, 2.71, -3.10, .71, .51, .029, "#8dabb1"),
        box("print_pine", .83, 2.67, -3.08, .27, .32, .029, "#58786f", shape="gable"),
    ])
    for i in range(24):
        x = -5.5 + i * .47
        if -4 < x < -1.1:
            continue
        shapes.append(box(f"wallpaper_{i}", x, 1.87, -3.202, .036, 3.73, .017, "#ad9a88"))
    return shapes


def _diner() -> list[dict]:
    shapes = _ground("#57727a")
    shapes.extend([
        box("cafe_back", 0, 2.47, -3.38, 14.2, 5.0, .21, "#b68b76"),
        box("cafe_wall_panels", 0, .68, -3.24, 14.2, 1.39, .085, "#527f7b"),
        box("cafe_trim", 0, 1.41, -3.18, 14.2, .13, .15, "#ecce9d"),
        box("cafe_counter", 3.82, .67, -1.91, 4.42, 1.33, 1.03, "#49706c"),
        box("cafe_countertop", 3.82, 1.37, -1.91, 4.56, .14, 1.20, "#c8a887"),
        box("booth_seat", -3.16, .39, -1.07, 1.69, .29, .66, "#8b495c"),
        box("booth_back", -3.16, .86, -1.34, 1.74, 1.12, .18, "#aa586a"),
        box("booth_table", -3.16, .86, -.34, 1.51, .115, .62, "#cfa47f"),
        box("booth_leg", -3.17, .45, -.35, .14, .86, .14, "#654e4c"),
    ])
    for i in range(28):
        x, z = (i % 7 - 3) * 1.4, (i // 7 - 1) * 1.46
        shade = "#a2a4a2" if (i % 7 + i // 7) % 2 else "#75818a"
        shapes.append(box(f"cafe_tile_{i}", x, -.017, z, 1.36, .018, 1.43, shade))
    for index, x in enumerate((-4.53, -.85, 2.89)):
        shapes.extend(_window(f"cafe_window_{index}", x, 2.69, -3.23, 1.63))
    return shapes


def _piano() -> list[dict]:
    shapes = [
        box("piano_body", -.27, .80, -.79, 2.38, 1.58, 1.03, "#382c31"),
        box("piano_top", -.27, 1.61, -.79, 2.53, .15, 1.17, "#593e3d"),
        box("piano_front", -.27, 1.11, -.252, 2.31, .59, .09, "#6b493e"),
        box("piano_board", -.27, .97, -.03, 2.45, .132, .64, "#4f3536"),
        box("piano_bench", -.27, .47, .86, .96, .12, .49, "#6b4c3f"),
        box("piano_bench_left", -.62, .22, .86, .10, .44, .33, "#513f39"),
        box("piano_bench_right", .08, .22, .86, .10, .44, .33, "#513f39"),
    ]
    for i in range(14):
        x = -1.34 + i * .163
        shapes.append(box(f"white_key_{i}", x, 1.048, .009, .146, .082, .47, "#efe3c5"))
        if i % 7 in {0, 1, 3, 4, 5}:
            shapes.append(box(f"black_key_{i}", x + .081, 1.098, -.091, .085, .086, .274, "#342d33"))
    return shapes


def _ballroom() -> list[dict]:
    shapes = _ground("#8b6554")
    shapes.extend([
        box("hall_back", 0, 2.65, -4.05, 16, 5.3, .21, "#986455"),
        box("hall_left", -8.0, 2.63, .17, .21, 5.26, 8.48, "#855d51"),
        box("hall_left_panel", -7.867, .72, .17, .08, 1.46, 8.48, "#674846"),
        box("hall_lower", 0, .60, -3.92, 16, 1.2, .13, "#674946"),
        box("curtain_rail", 0, 4.38, -3.58, 9.86, .12, .13, "#c8a274"),
        box("stage", -.61, .105, -.62, 6.75, .19, 3.57, "#7c4f45"),
        box("front_step", -.61, .047, 1.31, 6.53, .075, .27, "#bea480"),
        box("dance_floor", 1.93, .017, 2.25, 7.7, .027, 4.79, "#aa795b"),
        box("pendant_cord", -.8, 4.35, -.75, .095, 1.2, .095, "#735b46"),
        box("pendant_ring", -.8, 3.77, -.75, 1.35, .19, .90, "#9f8155"),
        box("pendant_lamp", -.8, 3.65, -.75, 1.13, .107, .73, "#ffcb84", emissive=True),
    ])
    for index in range(10):
        shapes.append(box(f"dance_board_{index}", -1.75 + .77 * index, .032, 2.25, .023, .006, 4.77, "#a37059"))
    for i in range(22):
        x = -4.7 + i * .445
        shapes.append(box(f"curtain_{i}", x, 2.55, -3.54, .41, 3.6, .23,
                          "#80414c" if i % 2 else "#693947"))
    for i, x in enumerate((-5.58, 5.58)):
        shapes.extend(_lamp(f"hall_light_{i}", x, -2.8))
    shapes.extend(_piano())
    return shapes


def _road() -> list[dict]:
    shapes = _ground(SNOW)
    shapes.append(box("county_road", 0, -.016, -1.2, 7.05, .017, 45, "#71808a"))
    for i in range(-8, 6):
        shapes.append(box(f"stripe_{i}", 0, -.002, i * 1.48, .062, .008, .65, "#bfc1ad"))
    for i, (x, z) in enumerate(((-5.2, -6.45), (4.8, -8.3), (-6.4, -3.7), (6.0, -3.8),
                                (-8.6, -11.0), (7.4, -14.2), (-4.6, -16.4), (-7.5, -.2))):
        shapes.extend(_pine(f"road_tree_{i}", x, z, 3.9 + i % 3 * .63))
    shapes.extend([
        box("gate_left", -2.75, .62, -2.51, .12, 1.25, .15, "#514f55"),
        box("gate_right", 2.75, .62, -2.51, .12, 1.25, .15, "#514f55"),
        box("road_barrier", 0, .93, -2.51, 5.67, .24, .17, "#a97755"),
        box("gate_sign", 0, 1.16, -2.39, 1.06, .46, .12, "#d3a364"),
        box("van_side", -3.58, .97, 1.65, 1.82, 1.55, 3.95, "#728b93", yaw=.06),
        box("van_top", -3.57, 1.79, 1.63, 1.88, .16, 3.63, "#abb6ad", yaw=.06),
        box("van_window", -3.57, 1.48, 3.638, 1.52, .39, .08, "#344e65", yaw=.06),
        box("van_bumper", -3.59, .37, 3.63, 1.83, .18, .18, "#49464a", yaw=.06),
    ])
    return shapes


def _alley() -> list[dict]:
    shapes = _ground("#bcccd4")
    shapes.extend([
        box("alley_track", 0, -.014, .16, 3.91, .022, 17.66, "#8397a0"),
        box("alley_left", -3.26, 2.6, -.69, 1.2, 5.2, 13.2, "#796264"),
        box("alley_right", 3.35, 2.6, -1.77, 1.4, 5.0, 12.6, "#747c7c"),
        box("alley_window", -2.63, 2.89, -3.14, .12, 1.07, 1.18, WARM, emissive=True),
        box("alley_bins", 1.95, .49, -2.61, .73, .93, .63, "#4a6167"),
        box("alley_bin_cap", 1.95, .97, -2.61, .86, .078, .77, "#6c7b7e"),
        box("alley_bench", -1.86, .48, -1.13, 1.51, .16, .49, "#755648"),
    ])
    for i in range(8):
        z = -7.0 + i * 1.60
        shapes.append(box(f"iceline_{i}", -2.29, .034, z, .73, .14, .96, SNOW, yaw=.10 * i))
    shapes.extend(_lamp("alley_lamp", -2.36, -2.5))
    return shapes


def _square() -> list[dict]:
    shapes = _ground("#b6cbd8")
    shapes.extend([
        box("square_path", 0, .001, 0, 9, .012, 9.5, "#8da6b0"),
        box("ceremony_base", 0, .25, -2.42, 4.85, .51, 2.92, "#716351"),
        box("ceremony_rail", 0, 1.52, -3.60, 4.76, .10, .10, "#7c6652"),
        box("lectern", 0, 1.05, -1.94, .84, 1.10, .64, "#705c4a"),
        box("lectern_top", 0, 1.63, -1.94, 1.07, .091, .78, "#ac8c60"),
        box("weather_crate", .71, .86, -2.68, .97, .71, .82, "#855c44"),
        box("weather_crate_door", .71, .92, -2.255, .74, .52, .061, "#654438"),
        box("animal_body", .71, 1.12, -2.16, .39, .27, .32, "#96734f"),
        box("animal_head", .71, 1.27, -1.99, .26, .24, .21, "#a48158"),
        box("animal_nose", .71, 1.26, -1.87, .09, .052, .038, "#403d36"),
        box("animal_ear_left", .619, 1.386, -2.007, .070, .061, .052, "#866249"),
        box("animal_ear_right", .800, 1.386, -2.007, .070, .061, .052, "#866249"),
    ])
    for i in range(9):
        x = (i - 4) * .91
        shapes.append(box(f"rail_{i}", x, .99, -3.60, .10, 1.09, .12, "#8d745d"))
    for i, x in enumerate((-7.3, -4.6, -2.6, 3.3, 5.4, 8.1)):
        shapes.extend(_pine(f"square_tree_{i}", x, -5.32 - i % 2 * .90, 4 + i % 3 * .70))
    for i, x in enumerate((-4.4, 4.2)):
        shapes.extend(_lamp(f"square_lamp_{i}", x, -2.96))
    return shapes


def _rescue_tree() -> list[dict]:
    shapes = _street()
    shapes.extend([
        box("rescue_trunk", -1.65, 1.41, 1.05, .37, 2.82, .40, "#765b50"),
        box("rescue_branch", -1.17, 1.97, 1.06, 1.12, .14, .22, "#7f6253", yaw=.1),
        box("rescue_barebranch", -2.18, 2.18, 1.05, .91, .11, .16, "#7f6253", yaw=-.1),
        box("rescue_snow", -1.15, 2.068, 1.06, 1.09, .072, .25, SNOW, yaw=.09),
        box("rescue_foliage", -1.66, 2.95, 1.05, 1.57, 1.35, 1.32, "#536f6e", shape="cone"),
        box("rescue_cap", -1.66, 3.11, 1.05, 1.15, 1.30, 1.1, SNOW, shape="cone"),
    ])
    return shapes


def _recital_room() -> list[dict]:
    shapes = _ground("#ab835f")
    shapes.extend([
        box("music_wall", 0, 2.55, -3.25, 10.6, 5.1, .20, "#95a299"),
        box("music_rail", 0, .53, -3.11, 10.6, .16, .10, "#739292"),
        box("music_rug", .12, .012, 1.06, 5.6, .022, 3.42, "#98665c"),
        box("music_rug_inset", .12, .024, 1.06, 5.33, .008, 3.12, "#b38467"),
        box("bookshelf", -3.7, 1.41, -2.56, 1.59, 2.82, .74, "#8e674e"),
        box("sheet_music", -.42, 1.52, -.06, .53, .28, .04, "#e4d6b8"),
    ])
    shapes.extend(_window("music_window", 2.88, 2.72, -3.12, 1.92))
    for i, color in enumerate(("#a3b2a1", "#6b7c8a", "#c8a474", "#a27665", "#566b63")):
        shapes.append(box(f"songbook_{i}", -4.18 + .24 * i, 1.51, -2.10,
                          .18, .64 - .035 * (i % 3), .19, color))
    shapes.extend(_piano())
    return shapes


ACTOR_LOOKS = {
    "phil": ("#b67d55", "#324b57", "#d7a07c", "#523d34"),
    "rita": ("#a94d57", "#eed0a4", "#e0a688", "#5d3e37"),
    "ned": ("#958257", "#d7a35b", "#d7a580", "#6d5845"),
    "larry": ("#48667c", "#8293a0", "#be8f71", "#463e3b"),
    "older_man": ("#607176", "#b48e77", "#c9957c", "#a9b5ac"),
    "child": ("#8d5d81", "#ebbd6d", "#cf9d83", "#674736"),
}


def actor_model(actor: str) -> list[dict]:
    coat, scarf, skin, hair = ACTOR_LOOKS.get(actor, ("#78907e", "#bba782", "#c99475", "#65534b"))
    shapes = [
        box("coat", 0, 1.07, 0, .68, .81, .51, coat, shape="bevel"),
        box("shirt", 0, 1.24, .266, .18, .38, .051, scarf),
        box("scarf", 0, 1.51, .032, .62, .12, .53, scarf),
        box("scarf_tail", -.12, 1.32, .285, .10, .38, .043, scarf),
        box("face", 0, 1.77, .036, .49, .48, .44, skin, shape="bevel"),
        box("hair", 0, 2.015, -.007, .52, .16, .48, hair, shape="bevel"),
        box("hair_back", 0, 1.85, -.176, .48, .342, .085, hair, shape="bevel"),
        box("mouth", 0, 1.675, .263, .104, .021, .021, "#644b49"),
        box("nose", 0, 1.77, .266, .067, .095, .054, skin),
    ]
    for side, x in (("left", -.15), ("right", .15)):
        shapes.extend([
            box(side + "_leg", x, .424, 0, .244, .63, .255, "#35444c"),
            box(side + "_foot", x, .091, .056, .267, .174, .411, "#28353a", shape="bevel"),
            box(side + "_arm", x * 2.85, 1.08, .012, .182, .68, .224, coat),
            box(side + "_hand", x * 2.85, .735, .025, .143, .19, .161, skin, shape="bevel"),
            box(side + "_eye", x * .64, 1.80, .262, .048, .053, .019, "#3b343d"),
        ])
    if actor == "rita":
        shapes.append(box("hair_tail", -.213, 1.63, -.143, .149, .64, .18, hair))
        shapes.append(box("coat_button", .093, 1.02, .271, .039, .048, .036, "#6c3b42"))
    elif actor == "ned":
        shapes.append(box("briefcase", .421, .51, .036, .27, .281, .124, "#644c45"))
        shapes.append(box("hat", 0, 2.047, .024, .56, .23, .48, "#6b654f", shape="bevel"))
        shapes.append(box("hat_brim", 0, 1.979, .052, .67, .049, .56, "#766a53", shape="bevel"))
        shapes.append(box("glasses_bridge", 0, 1.807, .285, .31, .018, .018, "#594d46"))
        for side, x in (("left", -.150), ("right", .150)):
            shapes.append(box(side + "_glasses", x, 1.775, .267, .017, .064, .021, "#594d46"))
    elif actor == "larry":
        shapes.append(box("camera", .51, 1.32, .169, .31, .26, .40, "#36474d", shape="bevel"))
        shapes.append(box("lens", .51, 1.32, .407, .21, .18, .16, "#2e3b45", shape="bevel"))
        shapes.append(box("lens_glass", .51, 1.32, .492, .094, .104, .027, "#668997", shape="bevel"))
        shapes.append(box("cap", -.009, 2.048, -.028, .53, .173, .51, "#526277", shape="bevel"))
        shapes.append(box("cap_brim", -.009, 1.979, .256, .39, .043, .17, "#526277", shape="bevel"))
    return shapes


def build_art() -> dict[str, Any]:
    """Each actor and set is built from original geometry and flat colors."""
    return {
        "version": 1,
        "sets": {
            "inn": _bedroom(),
            "main_st": _street(),
            "diner": _diner(),
            "knob": _square(),
            "country_rd": _road(),
            "hotel": _ballroom(),
            "piano_teacher": _recital_room(),
            "alley": _alley(),
            "outskirts": _road(),
            "rescue_tree": _rescue_tree(),
        },
        "actors": {actor: actor_model(actor) for actor in ACTOR_LOOKS},
        "actor_colors": {actor: look[0] for actor, look in ACTOR_LOOKS.items()},
    }
