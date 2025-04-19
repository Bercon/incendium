onclick = d => {

onclick = 0; // prevent clicking again which would reset the intro

navigator.gpu.requestAdapter().then(
    d => d.requestDevice({
        requiredLimits: {
            maxStorageBufferBindingSize: y = P_GRID_RES_X * P_GRID_RES_X * P_GRID_RES_X * 16,
            maxBufferSize: y
        },
    }).then(device => { // Intentionally "device", we can call configure({device, ...})

// While <p> can be style in HTML, we don't want to hide cursor before intro starts.
// Default canvas size is 300x150 which places the Click text so it's visible
// #reorder
c.width = P_CANVAS_WIDTH; // #and
c.height = P_CANVAS_HEIGHT; // #and
c.style=`position: fixed; cursor: none; left: 0; width: 100vw; height: 100vh; top: 0`; // #endreorder

// #ifdef DEBUG
c.style.width = P_CANVAS_WIDTH / window.devicePixelRatio;
c.style.height = P_CANVAS_HEIGHT / window.devicePixelRatio;
B.style.top /= window.devicePixelRatio;
B.style.left /= window.devicePixelRatio;
B.style["font-size"] /= window.devicePixelRatio;
B.style["letter-spacing"] /= window.devicePixelRatio;
// #endif

x = c.getContext(`webgpu`);
x.configure({
    device,
    format: `P_PRESENTATION_FORMAT`,
    usage: 24 // GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.STORAGE_BINDING
});
// #reorder
u = device.createBuffer({
    size: 8, // time & delta f32
    usage: 72 //GPUBufferUsage.COPY_DST |GPUBufferUsage.UNIFORM |
}); // #and

b = [];
for (i = 0; i < 9; i++) // 9 * 256^3*4*4 /1024/1024 == 2304 MB VRAM
    b.push(device.createBuffer({
        size: y,
        usage: i // 0 is staging buffer
            ? 132 //GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC
            : 9 // GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST

    })); // #endreorder
    // 0 staging buffer for copying music VRAM -> RAM
    // 1 pressure, only using 2/4th, stores data from music in the remainder
    // 2 temperatureRead, only using 1/4th
    // 3 temperatureWrite, only using 2/4th (divergence multigrid)
    // 4 velocityRead
    // 5 velocityWrite
    // 6 smokeRead
    // 7 smokeWrite
    // 8 temp, used for blurring

o = i = 0;
layout = device.createBindGroupLayout({ // Intentinoally "layout"
    entries: [
        // We don't want more than 8 buffers, because that's what supported by default without requesting more and that takes bytes
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage` } },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, buffer: {} },
        { binding: i++, visibility: GPUShaderStage.COMPUTE, storageTexture: { format: `P_PRESENTATION_FORMAT` } }
    ]
});

A = `P_MUSIC_DATA`.split("").map(d => d.charCodeAt() - P_MUSIC_CHAR_OFFSET).join(`,`); // Split with "" to use brotli dict

p = [
    `CODE_DIVERGENCE`, // 0
    `CODE_GRADIENT_SUBTRACT`, // 1
    `CODE_LIGHTING`, // 2
    `CODE_RENDER` // 3
];

for (i = 0; i < 4; i++) {
    // blur H: velocity_out -> smoke_out  , X=width, Y=1, Q=width
    // blur V: smoke_out    -> tmp        , X=1, Y=width, Q=height
    // blur H: tmp          -> smoke_out  , ...
    // blur V: smoke_out    -> tmp        , ...
    a = [
        `$velocity_out$smoke_out$tmp$smoke_out`[i], // input, each optimized to single letter
        `$smoke_out$tmp$smoke_out$tmp`[i], // output, each optimized to single letter
        i % 2 ? 1 : P_CANVAS_WIDTH,
        i % 2 ? P_CANVAS_WIDTH : 1,
        i % 2 ? P_CANVAS_HEIGHT : P_CANVAS_WIDTH
    ];
    d = `CODE_BLUR`;
    for (k = 0; k < 5; k++) d = d.replaceAll(`ZWXYQ`[k], a[k]);
    p.push(d)
}

p.push(
    `CODE_COMPOSITE`,
    `CODE_ADVECT`,
    `CODE_MUSIC`
);

// Multigrid templating, end up having duplicates of restrict & interpolate steps, but saves some bytes
q = P_GRID_RES_X;
for (i = 0; i < P_MULTIGRID_LEVELS; i++) { // 6 * 6 = 36
    a = [
        o, // Z = current element offset
        o += q * q * q, // W = coarser element offset
        q, // X = current grid size
        q /= 2 // Y = coarser grid size next level offset
    ];
    for (j = 0; j < 2; j++)
        a[4] = j, // Q = even / odd
        [`CODE_RESTRICT`,`CODE_SOLVE`,`CODE_INTERPOLATE`].map(d => {
            for (k = 0; k < 5; k++) d = d.replaceAll(`ZWXYQ`[k], a[k]);
            p.push(d)
        })
}

p = p.map(d =>
    device.createComputePipeline({
        layout: device.createPipelineLayout({bindGroupLayouts:[layout]}),
        compute: { module: device.createShaderModule({ code: `CODE_COMMON` + d.replaceAll(`Z`, A) }) }
    }));

h = [
    0, P_GRID_RES_BY_4, P_GRID_RES_BY_4, P_GRID_RES_BY_4 // div
];

for (i = 0; i < P_MULTIGRID_LEVELS_MINUS_ONE; i++) { // restrict
    // console.log("restrict", l, " -> ", l + 1);
    a = P_GRID_RES_BY_4 / 2 ** (i + 1);
    h.push(6 * i + 11, a, a, a)
}
for (; i >= 0; i--) { // i is already at correct level after restrict
    // console.log("solve", l);
    a = P_GRID_RES_BY_4 / 2 ** i;
    // for (k = 0; k < P_PRESSURE_ITERATIONS; k++) { // Unrolled
        h.push(6 * i + 12, a, a, a / 2); // solve even
        h.push(6 * i + 15, a, a, a / 2); // solve odd
        h.push(6 * i + 12, a, a, a / 2); // solve even
        h.push(6 * i + 15, a, a, a / 2); // solve odd
    // }
    // console.log("interpolate", l, " -> ", l - 1);
    i && h.push(6 * i + 7, a, a, a) // interpolate
}
l = i = 1;
h.push(
    i++, P_GRID_RES_BY_4, P_GRID_RES_BY_4, P_GRID_RES_BY_4, // grad
    i++, P_GRID_RES_BY_8, P_GRID_RES_BY_8, 1, // light
    i++, P_CANVAS_WIDTH / 8, P_CANVAS_HEIGHT / 8, 1, // render
    i++, P_CANVAS_HEIGHT / 60, 1, 1, // blur h
    i++, P_CANVAS_WIDTH / 60, 1, 1, // blur v
    i++, P_CANVAS_HEIGHT / 60, 1, 1, // blur h
    i++, P_CANVAS_WIDTH / 60, 1, 1, // blur v
    i++, P_CANVAS_WIDTH / 8, P_CANVAS_HEIGHT / 8, 1, // composite
    i++, P_GRID_RES_BY_4, P_GRID_RES_BY_4, P_GRID_RES_BY_4, // advect
    i++, P_GRID_RES_BY_4, P_GRID_RES_BY_4, P_GRID_RES_BY_4 // music
);

// #ifdef DEBUG
// frameTime = performance.now();
// #endif

o = t = j = 0;
(f = d => {

    // #ifdef DEBUG
    if (globalThis.updateVisualTimers !== undefined) {
        o = performance.now() * .001;
        t = globalThis.updateVisualTimers;
        o -= globalThis.updateVisualTimers;
        globalThis.updateVisualTimers = undefined;
    }
    // #endif

    k = j; // Swap read and write buffers required in advect step
    j ^= 1;
    a = o && performance.now() * .001 - o; // Gives 0 until o != 0 i.e. audio started

    device.queue.writeBuffer(
        u,
        0,
        new Float32Array(
            [
                a - t,
                t = a
            ]
        )
    );

    // #ifdef DEBUG
    globalThis.time = t;
    // console.log(t);
    // #endif

    q = device.createCommandEncoder();
    e = q.beginComputePass();
    i = 0;
    g = device.createBindGroup({
        layout,
        entries: [
            { binding: i++, resource: { buffer: b[1] } },
            { binding: i++, resource: { buffer: b[j + 2] } },
            { binding: i++, resource: { buffer: b[k + 2] } },
            { binding: i++, resource: { buffer: b[j + 4] } },
            { binding: i++, resource: { buffer: b[k + 4] } },
            { binding: i++, resource: { buffer: b[j + 6] } },
            { binding: i++, resource: { buffer: b[k + 6] } },
            { binding: i++, resource: { buffer: b[8] } },
            { binding: i++, resource: { buffer: u } },
            { binding: i++, resource: x.getCurrentTexture().createView() }
        ]
    });

    i = l ? 176 : 0; // Generate audio on very first execution
    do {
        // #reorder
        e.setPipeline(p[h[i++]]); // #and
        e.setBindGroup(0, g); // #endreorder
        e.dispatchWorkgroups(h[i++],h[i++],h[i++])
    } while(i < 176)

    e.end();

    l && q.copyBufferToBuffer(b[1], 0, b[0], 0, y);

    device.queue.submit([q.finish()]);

    l &&
        b[0].mapAsync(1).then(d => { // GPUMapMode.READ == 1
            A = new AudioContext({sampleRate: P_SAMPLE_RATE});
            s = A.createBufferSource();
            s.buffer = A.createBuffer(
                2, // channels
                y = P_GRID_RES_X * P_GRID_RES_X * P_GRID_RES_X,
                P_SAMPLE_RATE // sample rate
            );
            m = new Float32Array(b[0].getMappedRange());
            for (i = 0; i < y; i++)
                s.buffer.getChannelData(0)[i] = m[i],
                s.buffer.getChannelData(1)[i] = m[i + y]; // Copy both channels
            s.connect(A.destination);
            s.start();

            // #ifdef DEBUG
            globalThis.audioContext = A;
            globalThis.audioBuffer = s.buffer;
            globalThis.bufferSource = s;
            // #endif

            // Use performance.now() for timing because AudioContext.currentTime only
            // has ~10 ms precision on chrome. Even at 60 fps i.e. 16ms per frame it
            // might be choppy. Hope there is no delay between s.start() and
            // performance.now(), otherwise visuals and audio are out of sync
            o = performance.now() * .001;
            t = 0
        });

    // First run completed, audio generation done
    // #reorder
    l = 0; // #and
    // #alternative
    B.style.opacity = 7 - .5 * t; // #or
    B.style.opacity = 7 - t / 2; // #endalternative

    // #endreorder

    // #ifdef DEBUG
    // now = performance.now()*.001;
    // console.log("Frame time", now - frameTime);
    // frameTime = now;
    // #endif

    requestAnimationFrame(f)
})()

})) // navigator promise

} // onclick