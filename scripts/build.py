
import os
import shutil
from pathlib import Path
import json
import math
import re

from brotli_search import search_brotli_dict_words
from packager import optimizer, compress, printter, parser, options

OUTPUT_DIR = "build"
OUTPUT_TEMPLATED = os.path.join(OUTPUT_DIR, "templated")
OUTPUT_NO_COMMENTS = os.path.join(OUTPUT_DIR, "no_comments")

# Use rgba instead of xyzw as vector accessors
USE_RGBA = True


def intro_parameters():
    # TODO: Altering this isn't currently supported, because of hardcoded values in main.js
    GRID_RES = 256
    # GRID_RES = 320
    # Use 8x8x8 as top level instead of 4x4x4 because it would require special
    # handling at solving step where dispact for Z axis is half i.e. (1, 1, 0.5)
    MULTIGRID_LEVELS = 6
    # MULTIGRID_LEVELS = 5
    SIMULATION_SCALE = 1
    RDX = GRID_RES * SIMULATION_SCALE
    P_CELLS_TOTAL = GRID_RES * GRID_RES * GRID_RES

    params = [
        ("P_CANVAS_WIDTH", "1920"),
        ("P_CANVAS_HEIGHT", "1080"),

        ("P_GRID_RES_X", GRID_RES),
        ("P_GRID_RES_Y", GRID_RES),
        ("P_GRID_RES_Z", GRID_RES),

        ("P_GRID_RES", GRID_RES),
        ("P_GRID_RES_MINUS_ONE", GRID_RES - 1),
        ("P_GRID_RES_BY_2", round(GRID_RES / 2)),
        ("P_GRID_RES_BY_4", round(GRID_RES / 4)),
        ("P_GRID_RES_BY_8", round(GRID_RES / 8)),

        ("P_CELLS_TOTAL", P_CELLS_TOTAL),

        ("P_MULTIGRID_LEVELS_PLUS_ONE", MULTIGRID_LEVELS + 1),
        ("P_MULTIGRID_LEVELS_MINUS_ONE", MULTIGRID_LEVELS - 1),
        ("P_MULTIGRID_LEVELS", MULTIGRID_LEVELS),

        ("P_RDX", RDX),

        ("P_PRESSURE_ITERATIONS", "2"),

        ("P_VELOCITY_DECAY", ".01"),
        ("P_TEMPERATURE_DECAY", ".5"),

        ("P_BURN_RATE", ".8"),
        ("P_BURN_HEAT_EMIT", "12"),
        ("P_BURN_SMOKE_EMIT", ".5"),

        ("P_BOYANCY", ".7"),

        ("P_GLOW_RADIUS", "160"),
        ("P_STEP_LENGTH", ".008"),

        ("P_BLACKBODY_BRIGHTNESS", "3"),
        ("P_OPTICAL_DENSITY", "200"),

        ("P_PRESENTATION_FORMAT", "rgba8unorm"),

        ("P_SAMPLE_RATE", "48000"),

        # From spec
        ("GPUShaderStage.COMPUTE", "4"),
        ("GPUBufferUsage.STORAGE", "128"),
        ("GPUTextureUsage.STORAGE_BINDING", "8"),
        ("GPUTextureUsage.RENDER_ATTACHMENT", "16"),
        ("GPUBufferUsage.UNIFORM", "64"),
        ("GPUBufferUsage.COPY_SRC", "4"),
        ("GPUBufferUsage.COPY_DST", "8"),

        # Parameter renaming
        ("$pressure", "A"),
        ("$temperature_in", "B"),
        ("$temperature_out", "C"),
        ("$velocity_in", "V"),
        ("$velocity_out", "E"),
        ("$smoke_in", "F"),
        ("$smoke_out", "G"),
        ("$tmp", "H"),
        ("global_id", "g"),

        ("to_index", "x"),
        ("clamp_to_edge", "z"),
        ("trilerp1", "y"),
        ("trilerp4", "q"),
        ("add_smoke", "e"),
    ]
    return params


def apply_parameters(s, params):
    for p in params:
        s = s.replace(p[0], str(p[1]))
    return s


def read_json(filename):
    with open(filename) as f:
        return json.load(f)


def read_file(filename):
    with open(filename) as f:
        return f.read()


def write_file(filename, content):
    with open(filename, "w") as js:
        js.write(content)


def rename_vector_accessors(wgsl_code: str) -> str:
    """
    Replaces all vector swizzle accessors (.xyzw) in WGSL code with (.rgba) format,
    ensuring they are followed by a terminating symbol (;,)]= , space, or end of line).
    """
    mapping = {
        'x': 'r', 'y': 'g', 'z': 'b', 'w': 'a'
    }
    def replace_match(match):
        return '.' + ''.join(mapping[ch] for ch in match.group(1)) + match.group(2)
    return re.sub(r'\.([xyzw]{1,4})([;,)\]= \t\r\n]|$)', replace_match, wgsl_code)


def find_unoptimized_decimal_numbers(s):
    """
    Searches for numbers in the format 0.xxx or xxx.0 in the given string.
    :param s: Input string
    """
    pattern = r'\b0\.\d+\b|\b\d+\.0\b'
    for i in re.findall(pattern, s):
        print(f"Found unoptimized decimal number: {i}")


def process_music_to_params(music, params):
    MAX_NOTE = 28

    row_notes_len = 16
    notes_per_second = 6
    melody_start_notes = 32

    if max(music["melody"]) > MAX_NOTE or max(music["bass"]) > MAX_NOTE:
        raise Exception(f"Music has a note larger than {MAX_NOTE}, revise compression to alphabet")

    total_length = len(music["melody"]) + len(music["bass"])
    params.append(("P_MELODY_NOTES_LENGTH", len(music["melody"])))
    params.append(("P_BASS_NOTES_LENGTH", len(music["bass"])))
    params.append(("P_MUSIC_NOTES_LENGTH", total_length))

    params.append(("P_MELODY_START", melody_start_notes))

    start_char = ord('a')
    params.append(("P_MUSIC_CHAR_OFFSET", start_char))

    music_data = ""
    for c in music["melody"]: music_data += chr(start_char + c)
    for c in music["bass"]: music_data += chr(start_char + c)
    params.append(("P_MUSIC_DATA", music_data))


    row_timestamps = ""
    for row_idx in range(math.ceil(len(music["melody"]) / row_notes_len)):
        row_notes = []
        for row_note_idx in range(row_notes_len):
            note_idx = row_idx * row_notes_len + row_note_idx
            if note_idx < len(music["melody"]):
                note = music["melody"][note_idx]
                row_notes.append(f"{note:2d}")
        row_start_ts = float(melody_start_notes + row_idx * row_notes_len) / notes_per_second
        row_timestamps += f"{row_start_ts:6.2f}: {', '.join(row_notes)}\n"
    write_file(os.path.join(OUTPUT_DIR, "music_row_timestamps.txt"), row_timestamps)
    # print(music_data)


def _cost_func(root):
    global args
    html_text = printter.format(root)
    html_brotli = compress.compress_html_file(html_text, slow=False) # Using slow here is way too slow
    return compress.get_bootstraped_size(html_brotli)


def main():
    global args

    if args.clean and os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    for folder in [OUTPUT_TEMPLATED, OUTPUT_NO_COMMENTS]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    params = intro_parameters()
    params = sorted(params, key=lambda x: len(x[0]), reverse=True)

    music = read_json("src/music.json")
    process_music_to_params(music, params)

    wgsl_source = []
    for f in [
        ("CODE_COMMON", "src/wgsl/common.wgsl"),
        ("CODE_COMPOSITE", "src/wgsl/composite.wgsl"),
        ("CODE_BLUR", "src/wgsl/blur.wgsl"),
        ("CODE_ADVECT", "src/wgsl/advect.wgsl"),
        ("CODE_DIVERGENCE", "src/wgsl/divergence.wgsl"),
        ("CODE_GRADIENT_SUBTRACT", "src/wgsl/gradient_subtract.wgsl"),
        ("CODE_LIGHTING", "src/wgsl/lighting.wgsl"),
        ("CODE_RENDER", "src/wgsl/render.wgsl"),
        ("CODE_RESTRICT", "src/wgsl/restrict.wgsl"),
        ("CODE_INTERPOLATE", "src/wgsl/interpolate.wgsl"),
        ("CODE_SOLVE", "src/wgsl/solve.wgsl"),
        ("CODE_MUSIC", "src/wgsl/music.wgsl"),
    ]:
        wgsl_source.append([f[0], read_file(f[1]) + "\n"])

    main_js = read_file("src/main.js") + "\n"

    for entry in wgsl_source:
        entry[1] = apply_parameters(entry[1], params)
        if USE_RGBA:
            entry[1] = rename_vector_accessors(entry[1])
        write_file(os.path.join(OUTPUT_TEMPLATED, entry[0] + ".wgsl"), entry[1])
    main_js = apply_parameters(main_js, params)
    main_js = apply_parameters(main_js, wgsl_source)
    write_file(os.path.join(OUTPUT_TEMPLATED, "main.js"), main_js)

    index_html = read_file("src/index.html")
    index_html = index_html.replace("CODE_MAIN", main_js)
    write_file(os.path.join(OUTPUT_TEMPLATED, "index.html"), index_html)

    root_node = parser.parse_document(index_html)

    def _best_func(state, cost):
        # TODO: save state if we want intermediate results
        # print("Best so far", cost, "bytes")
        pass

    if not args.no_optimization:
        with optimizer.Solutions(root_node, args.seed, args.queue_length, args.processes, _cost_func, _best_func, _initializer, (args)) as solutions:
            if args.algorithm == 'lahc':
                root_node = optimizer.lahc(solutions, steps=args.steps, list_length=args.lahc_history, init_margin=args.margin)
            elif args.algorithm == 'dlas':
                root_node = optimizer.dlas(solutions, steps=args.steps, list_length=args.dlas_history, init_margin=args.margin)
            else:
                root_node = optimizer.anneal(solutions, steps=args.steps, start_temp=args.start_temp, end_temp=args.end_temp, seed=args.seed)
        print("")

    no_comments_pretty = printter.format(root_node, pretty=True, comments=False)
    write_file(os.path.join(OUTPUT_NO_COMMENTS, "index.html"), no_comments_pretty)

    optimized_content = printter.format(root_node)
    find_unoptimized_decimal_numbers(optimized_content)
    write_file(os.path.join(OUTPUT_DIR, "index.html"), optimized_content)

    # A bit hacky way of stripping HTML from optimized code to use it in player
    debug_content = printter.format(root_node, pretty=True, flags={"DEBUG": True})
    pattern = re.compile(r'<script>(.*?)</script>', re.DOTALL)
    debug_js_only = pattern.findall(debug_content)[0]
    playerHtml = read_file("tools/intro_player.html")
    playerHtml = playerHtml.replace("CODE_MAIN", debug_js_only)
    write_file(os.path.join(OUTPUT_DIR, "intro_player.html"), playerHtml)

    search_brotli_dict_words(os.path.join("scripts", "brotli_dictionary.bin"), os.path.join(OUTPUT_DIR, "index.html"), os.path.join(OUTPUT_DIR, "brotli_highlight.html"))

    OUTPUT="build/HBC-00024_INCENDIUM.cmd"
    compressed = compress.compress_html_file(optimized_content, slow=args.slow)
    bootstrapped = compress.bootstrap(compressed)
    with open(OUTPUT, 'wb') as file:
        file.write(bootstrapped)
    final_size = os.stat(OUTPUT).st_size
    over_budget = ""
    if final_size > 4096: over_budget = f" ({final_size - 4096} bytes over budget)"
    print(f'Final intro size in bytes is {final_size}{over_budget}')

def _initializer(a):
    global args
    args = a

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(__doc__)
    p.add_argument("--clean", help="Clean build folder", action="store_true")
    p.add_argument("--slow", help="Runs slow extra optimizations that save couple bytes", action="store_true")
    p.add_argument("--no_optimization", help="Skips optimization entirely", action="store_true")

    options.packager_arguments(p)

    global args
    args = p.parse_args()
    main()
