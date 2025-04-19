# INCENDIUM

INCENDIUM is a demoscene 4kb intro, meaning all code that generates the visuals and music fits into 4096 bytes. Participated to 4kb intro category at Revision 2025 demoscene party.

The entry is packaged as Windows PowerShell script which plays the compressed intro in web browser. The visuals and music are both generated using WebGPU.

You can checkout a recording at https://youtu.be/U8FXJpO9Vck.

## Requirements

* Operating systems default browser must support WebGPU. Currently it means Chrome, Edge, or other new Chromium based browser. Non-nightly/beta Firefox and Safari won't work.
* Nvidia RTX 4080 level GPU to run 1080p 60hz. Running at 60hz is important for smooth artifact free fluid simulation

## Setup

Building intro and package it (install requirements: `pip install -R requirements.txt`):
```
python scripts/build.py
```

Drag'n'drop `build/index.html` to browser. To run packaged entry, double click `builld/entry.cmd`

There also debug version that has seek bar `intro_player.html`. However, since this is a simulation and seeking simply jumps to given timestamp, it will not look exactly as it would if you let the intro play out.

The final entry was packaged with heavier settings than the defaults, try overkill settings like this to drop the size below 4kb:
```
python scripts/build.py --slow -s 100000 -D 15
```

## Highlights

* Fluid simulation, rendering and music is all done with WebGPU compute shaders
* 3D fluid simulator with multigrid solver that uses red-black Gauss-Seidel iteration to run faster and to read/write same buffer
* Box blur computed using accumulation to get any kernel size at fixed 4 lookups per pixel. Gaussian blur is approximated by running box blur twice
* Volumetric shadows, restricted to primary axis light directions
* Baking lighting, so raymarcher only does 1 vec4 lookup per step
* 324 byte PowerShell bootstrapper for Brotli compressed webpage (40 bytes less than on used in [Felid](https://demozoo.org/graphics/342293/)), might be possible to compress it even more?

## Compression

The intro uses Brotli compression that is quite unpredictable, *adding* characters sometimes decreases the size of the results. Flipping order of rows, using different characters and so on, which don't change the size of the data being compress can change the size of the compressed result by tens of bytes. A *packager* which is heavily based on [Pakettic](https://github.com/vsariola/pakettic) will suffle rows and try different variants of code to find the optimal layout. Running without this with ```python scripts/build.py --no_optimization``` gives 4187 bytes, while with enough suffling, we can drop this to 4093, improving compressiong by 94 bytes.

There is still room for improvement with the packager, it doesn't try variable renaming, swapping operation order, trying different variants such as `a/2` and `a*.5` which give the same result. All things Pakettic does for TIC-80 code. These could further improve the compression and make using the tool more automatic with less need for manually annotating the code. However, this requires implementing proper WGSL parsing which does take some amount of effort.

## Packaging and bootstrapping

The entry is compressed HTML page with brotli. Since brotli compressed content can only be served via web server, not locally opening the file we need a web server. This is achieved with Windows PowerShell script that serves the file itself with suitable offset once as via Windows builtin HTTP server. Technique introduce first (I think?) by Muhmac / Speckdrumm in Felid:  https://demozoo.org/graphics/342293/

PowerShell bootstrap code eats 324 bytes.

Default browser is launched. This intro requires WebGPU only supported in Chromium browsers like Edge or Chrome. If default browser is Firefox, intro will not work.
