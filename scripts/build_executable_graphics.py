
import os
import shutil
from pathlib import Path
import re

from brotli_search import search_brotli_dict_words
from packager import optimizer, compress, printter, parser, options

# Use rgba instead of xyzw as vector accessors
USE_RGBA = True

def intro_parameters():
    GRID_RES = 384
    MULTIGRID_LEVELS = 5
    SIMULATION_SCALE = 1
    RDX = GRID_RES * SIMULATION_SCALE
    DX = 1 / RDX # TODO: template like this?
    P_CELLS_TOTAL = GRID_RES * GRID_RES * GRID_RES
    SIM_ITERS = 120

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
        ("P_SIMULATION_SCALE", SIMULATION_SCALE),
        ("P_DX", DX),
        ("P_ALPHA_DIV", f"({GRID_RES} * {GRID_RES} * {SIMULATION_SCALE} * {SIMULATION_SCALE})"),

        ("P_PRESSURE_ITERATIONS", 2),

        ("P_SMOKE_DECAY", "5"),
        ("P_VELOCITY_DECAY", ".1"),
        ("P_TEMPERATURE_DECAY", "3"),

        ("P_BURN_RATE", "1"),
        ("P_BURN_HEAT_EMIT", "5"),
        ("P_BURN_SMOKE_EMIT", ".1"),

        ("P_BOYANCY", ".5"),

        ("P_ITERATIONS", round(SIM_ITERS)),
        ("P_TOTAL_ITERATIONS", round(SIM_ITERS * 6)),
        ("P_ITERATIONS_BEFORE_ENV", round(SIM_ITERS * 5)),

        ("P_GLOW_RADIUS", "200"),
        ("P_STEP_LENGTH", ".002"),

        ("P_BLACKBODY_BRIGHTNESS", "70"),
        ("P_OPTICAL_DENSITY", "200"),

        ("u.d", ".02"), # Timestep

        ("P_PI", 3.141),

        ("P_PRESENTATION_FORMAT", "rgba8unorm"),

        # From spec
        ("GPUShaderStage.COMPUTE", 4),
        ("GPUBufferUsage.STORAGE", 128),
        ("GPUTextureUsage.STORAGE_BINDING", 8),
        ("GPUTextureUsage.RENDER_ATTACHMENT", 16),
        ("GPUBufferUsage.UNIFORM", 64),
        ("GPUBufferUsage.COPY_SRC", 4),
        ("GPUBufferUsage.COPY_DST", 8),

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
        ("trilerp1", "P"),
        ("trilerp4", "q"),
        ("add_smoke", "M"),

        ("bezier4", "J"),
        ("bezier4d", "K"),
        ("bezier1", "L"),
        ("bezier1d", "X"),
        ("spline", "N"),
        ("surface", "Y"),
    ]
    return params


def apply_parameters(s, params):
    for p in params:
        # print("Replace", p[0], str(p[1]))
        s = s.replace(p[0], str(p[1]))
    return s


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


def _cost_func(root):
    global args
    html_text = printter.format(root)
    html_brotli = compress.compress_html_file(html_text, slow=False) # Using slow here is way too slow
    return compress.get_bootstraped_size(html_brotli)

def parse_phoenix(filename):
    phoenix_vertices = ""
    phoenix_grids = []
    def parse_grid(s):
        data_part, comment_part = s.split("//")
        comment_part = "P_" + comment_part.strip()
        data_part = data_part.strip().rstrip(",")
        numbers = data_part.split(",")
        formatted_numbers = [f"{float(n):.3f}".lstrip("0") for n in numbers]
        formatted_data = ",".join(formatted_numbers)
        return (comment_part, formatted_data)

    with open(filename) as f:
        for l in f.readlines():
            if "," in l:
                phoenix_grids.append(parse_grid(l))
            else:
                phoenix_vertices += l.split("//")[0].strip()

    return phoenix_vertices, phoenix_grids


def main():
    global args
    OUTPUT_DIR = "build_executable_graphics"
    OUTPUT_TEMPLATED = os.path.join(OUTPUT_DIR, "templated")
    OUTPUT_NO_COMMENTS = os.path.join(OUTPUT_DIR, "no_comments")

    if args.clean and os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    for folder in [OUTPUT_TEMPLATED, OUTPUT_NO_COMMENTS]:
        Path(folder).mkdir(parents=True, exist_ok=True)

    params = intro_parameters()
    phoenix_vertices, phoenix_grids = parse_phoenix("executable_graphics/phoenix.txt")
    phoenix_numbers = len(phoenix_vertices) / 2
    # print(phoenix_numbers)
    params.append(("PHOENIX_NUM_FLOATS", int(phoenix_numbers)))
    params.append(("PHOENIX_NUM_FLOATS_TWICE", int(phoenix_numbers * 2)))
    params.append(("PHOENIX_NUM_FLOATS_PADDED", int(phoenix_numbers + phoenix_numbers / 3)))
    params.append(("PHOENIX_NUM_VERTICES", int(phoenix_numbers / 3)))
    params.append(("PHOENIX_VERTICES", phoenix_vertices))
    for i in phoenix_grids:
        params.append(i)

    params = sorted(params, key=lambda x: len(x[0]), reverse=True)

    wgsl_source = []
    for f in [
        ("CODE_COMMON", "executable_graphics/wgsl/common.wgsl"),
        ("CODE_COMPOSITE", "executable_graphics/wgsl/composite.wgsl"),
        ("CODE_BLUR", "executable_graphics/wgsl/blur.wgsl"),
        ("CODE_ADVECT", "executable_graphics/wgsl/advect.wgsl"),
        ("CODE_DIVERGENCE", "executable_graphics/wgsl/divergence.wgsl"),
        ("CODE_GRADIENT_SUBTRACT", "executable_graphics/wgsl/gradient_subtract.wgsl"),
        ("CODE_LIGHTING", "executable_graphics/wgsl/lighting.wgsl"),
        ("CODE_RENDER", "executable_graphics/wgsl/render.wgsl"),
        ("CODE_RESTRICT", "executable_graphics/wgsl/restrict.wgsl"),
        ("CODE_INTERPOLATE", "executable_graphics/wgsl/interpolate.wgsl"),
        ("CODE_SOLVE", "executable_graphics/wgsl/solve.wgsl"),
    ]:
        wgsl_source.append([f[0], read_file(f[1]) + "\n"])
    main_js = read_file("executable_graphics/main.js") + "\n"

    for entry in wgsl_source:
        entry[1] = apply_parameters(entry[1], params)
        if USE_RGBA:
            entry[1] = rename_vector_accessors(entry[1])
        write_file(os.path.join(OUTPUT_TEMPLATED, entry[0] + ".wgsl"), entry[1])
    main_js = apply_parameters(main_js, params)
    main_js = apply_parameters(main_js, wgsl_source)
    write_file(os.path.join(OUTPUT_TEMPLATED, "main.js"), main_js)

    index_html = read_file("executable_graphics/index.html")
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

    no_comments_pretty = printter.format(root_node, pretty=True, comments=False)
    write_file(os.path.join(OUTPUT_NO_COMMENTS, "index.html"), no_comments_pretty)

    optimized_content = printter.format(root_node)
    find_unoptimized_decimal_numbers(optimized_content)
    write_file(os.path.join(OUTPUT_DIR, "index.html"), optimized_content)

    optimized_content_debug = printter.format(root_node, pretty=False, flags={"DEBUG": True})
    write_file(os.path.join(OUTPUT_DIR, "index_debug.html"), optimized_content_debug)

    search_brotli_dict_words(os.path.join("scripts", "brotli_dictionary.bin"), os.path.join(OUTPUT_DIR, "index.html"), os.path.join(OUTPUT_DIR, "brotli_highlight.html"))

    OUTPUT="build_executable_graphics/Feenikslintu.cmd"
    compressed = compress.compress_html_file(optimized_content, slow=args.slow)
    bootstrapped = compress.bootstrap(compressed)
    with open(OUTPUT, 'wb') as file:
        file.write(bootstrapped)
    final_size = os.stat(OUTPUT).st_size
    over_budget = ""
    if final_size > 4096: over_budget = f" ({final_size - 4096} bytes over budget)"
    print(f'\nFinal intro size in bytes is {final_size}{over_budget}')


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
