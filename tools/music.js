var BUFFER_DIM = 256;

// Render a clip of the audio buffer for debugging purposes:
function renderAudioBuffer(buffer) {
    const canvasWidth = 2000;
    const canvasHeight = 200;
    AudioCanvas.width = canvasWidth;
    AudioCanvas.height = canvasHeight;
    const ctx = AudioCanvas.getContext('2d');
    ctx.clearRect(0, 0, C.width, C.height);
    const stepWidth = C.width / buffer.length;
    ctx.beginPath();
    for (let i = 0; i < buffer.length; i++) {
        const x = i * stepWidth;
        const y = (buffer[i] + 1) * (C.height / 2); // Convert -1..1 range to 0..canvasHeight
        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }
    ctx.stroke();
}

async function playWithDevice(device, musicWgsl) {
    var startTime = performance.now();

    var x = C.getContext`webgpu`; // Canvas
    x.configure({
        device,
        format: `rgba8unorm`,
        usage: 24 // GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.STORAGE_BINDING
    });

    // For passing data from JS to WGSL
    // var u = device.createBuffer({
    //     size: 8,
    //     usage: 72 // GPUBufferUsage.COPY_DST | GPUBufferUsage.UNIFORM
    // });

    // Fluid sim runs in 256^3 * 16 buffers = 268435456 bytes = 256 MB
    // 180s 48000 rate stereo audio: 48000*180*4*2 = 65.91796875 MB == no problem!

    var BUFFER_SIZE = BUFFER_DIM * BUFFER_DIM * BUFFER_DIM * 16; // 16 = rgba f32
    var webgpuBuffer = device.createBuffer({size: BUFFER_SIZE, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC});
    var stagingBuffer = device.createBuffer({
        size: BUFFER_SIZE,
        // Mappable and destination for copying
        usage: GPUBufferUsage.MAP_READ | GPUBufferUsage.COPY_DST,
    });

    var layout = device.createBindGroupLayout({
        entries: [
            { binding: 0, visibility: GPUShaderStage.COMPUTE, buffer: { type: `storage`, } },
            // { binding: 1, visibility: GPUShaderStage.COMPUTE, buffer: {} }, // TODO: probably don't need data from JS?
        ]
    });

    var f = d =>
        device.createComputePipeline({
            layout: device.createPipelineLayout({bindGroupLayouts:[layout]}),
            compute: { module: device.createShaderModule({ code: d }) }
        });

    var pipeline = f(musicWgsl);

    // Write some data to gpu buffer in JS
    // device.queue.writeBuffer(
    //     u,
    //     0,
    //     new Float32Array(
    //         [
    //             P_SPEED * (a - t) * (t > 165 || (t > 54 && t < 56) || (t > 76 && t < 80) ? .5 : 1),
    //             t = a

    //         ]
    //     ),
    //     0,
    //     2
    // );
    var commandEncoder = device.createCommandEncoder();
    var e = commandEncoder.beginComputePass();
    var i = 0;
    var g = device.createBindGroup({
        layout,
        entries: [
            { binding: i++, resource: { buffer: webgpuBuffer } },
            // { binding: i++, resource: { buffer: u } }, // TODO: probably don't need data from JS?
        ]
    });


    e.setPipeline(pipeline);
    e.setBindGroup(0, g);
    // How many times each computer shader is execude, cubic i.e. x*y*z = total workgroup invocations
    // so shader, and since shader also has workgroup gx*gx*gz, total number of times code is run:
    // x*y*y * gx*gx*gz = total executions
    e.dispatchWorkgroups(256 / 4, 256 / 4, 256 / 4);
    e.end();

    commandEncoder.copyBufferToBuffer(webgpuBuffer, 0, stagingBuffer, 0, BUFFER_SIZE);

    device.queue.submit([commandEncoder.finish()]);

    await stagingBuffer.mapAsync(GPUMapMode.READ);
    const arrayBuffer = stagingBuffer.getMappedRange();

    const audioData = new Float32Array(arrayBuffer);

    // Cleanup, garbage collection would likely also do this once things go out of scope

    var SAMPLE_RATE = 48000;
    var A = new AudioContext({sampleRate:SAMPLE_RATE});
    var LEGNTH = 180;
    var AUDIO_BYTES = LEGNTH * SAMPLE_RATE;
    var x = A.createBuffer(
        2, // 2 channels
        AUDIO_BYTES,
        SAMPLE_RATE,
    );

    // console.log(audioData.slice(AUDIO_BYTES / 4, AUDIO_BYTES / 4 + 100));

    // Assuming audio is sequentially stored, first left channel, then right channel
    x.getChannelData(0).set(audioData.subarray(0, AUDIO_BYTES)); // Copy left channel
    x.getChannelData(1).set(audioData.subarray(AUDIO_BYTES, 2 * AUDIO_BYTES)); // Copy right channel

    var s = A.createBufferSource();
    s.buffer = x;
    s.connect(A.destination);

    s.start();
    console.log("Playing. Generated in", performance.now() - startTime, "milliseconds");

    const RENDER_SLICE_START_SECONDS = 10;
    const RENDER_SLICE_SECONDS = 5;
    renderAudioBuffer(audioData.subarray(
        RENDER_SLICE_START_SECONDS * SAMPLE_RATE,
        (RENDER_SLICE_START_SECONDS + RENDER_SLICE_SECONDS) * SAMPLE_RATE));

    stagingBuffer.unmap(); // TODO: Not required in intro
    stagingBuffer.destroy(); // TODO: Not required in intro
    webgpuBuffer.destroy(); // TODO: Not required in intro

}

function play() {
    // Original:
    // (_=>{
    //     u = t/48000;
    //     if(!t)d=[];
    //     [x,y] = d[m=t%24000]||[0,0];;
    //     for (c=0;c<2;c++) {
    //         a = u+c; p = 0;
    //     for(k=9;k<99;a+=k*=1.1)
    //         p += 4*sin(k*a)/k;
    //     for (j=1;j<=3;j++)
    //     for (i=1;i<=3;i++) {
    //         r = min(u*j/3+i/3,128);
    //          s = r%1;
    //         n = [3,0,6,3,8,3,6,1][r&r/j/4+1&7];
    //         f = j*i*2**(n/12)*50;
    //         e = 2**(-.003/s-9*s-.7-i/4-j/4)
    //         n && (x += sin((sin(f*u*2*PI)*2+p)*sin(u/3*PI/j/32))*e);
    //     }
    //     [x,y] = [y,x];
    //     }
    //     d[m]=[y/2,x/2];
    //     return [x,y];
    //     })()

    var musicWgsl = /*wgsl*/`

    const melody = array(
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0,  0,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0, 13,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        25,  0, 20,  0, 23,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0,  0,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0, 13,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0, 20,  0, 18,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0,  0,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0, 13,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        25,  0, 20,  0, 23,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0,  0,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0, 13,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        23,  0, 20,  0, 18,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 20,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0, 21,  0, 23,  0, 21,  0,  0,  0, 18,  0,  0,  0,
        20,  0,  0,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 20,  0, 20,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0, 21,  0, 23,  0, 25,  0,  0,  0, 18,  0,  0,  0,
        20,  0,  0,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 16,  0,  0,  0, 15,  0,  0,  0,
        16,  0,  0,  0, 23,  0, 23,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0, 23,  0, 25,  0, 23,  0,  0,  0, 18,  0,  0,  0,
        20,  0,  0,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0, 16,  0,  0,  0, 15,  0,  0,  0,
        16,  0,  0,  0, 23,  0, 23,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0, 23,  0, 25,  0, 23,  0,  0,  0, 18,  0,  0,  0,
        20,  0,  0,  0, 13,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        1,  0,  0,  0,  1,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        13, 16, 20, 25, 13, 16, 20, 25, 13, 16, 20, 25, 13, 16, 20, 25,
        13, 18, 21, 25, 13, 18, 21, 25, 13, 18, 21, 25, 13, 18, 21, 25,
        11, 16, 20, 23, 11, 16, 20, 23, 11, 16, 20, 23, 11, 16, 20, 23,
        12, 15, 20, 24, 12, 15, 20, 24, 12, 15, 20, 24, 12, 15, 20, 24,
        13, 16, 20, 25, 13, 16, 20, 25, 13, 16, 20, 25, 13, 16, 20, 25,
        13, 18, 21, 25, 13, 18, 21, 25, 13, 18, 21, 25, 13, 18, 21, 25,
        11, 16, 20, 23, 11, 16, 20, 23, 11, 16, 20, 23, 11, 16, 20, 23,
        12, 15, 20, 24, 12, 15, 20, 24, 12, 15, 20, 24, 12, 15, 20, 24,
        13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25,
        13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25, 12, 16, 19, 24,
        11, 15, 18, 23, 11, 15, 18, 23, 11, 15, 18, 23, 11, 15, 18, 23,
        10, 13, 18, 22, 10, 13, 18, 22, 11, 13, 18, 23, 10, 13, 18, 22,
        13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25,
        13, 17, 20, 25, 13, 17, 20, 25, 13, 17, 20, 25, 12, 16, 19, 24,
        11, 15, 18, 23, 11, 15, 18, 23, 11, 15, 18, 23, 11, 15, 18, 23,
        10, 13, 18, 22, 10, 13, 18, 22, 11, 13, 18, 23, 10, 13, 18, 22,
        13,  0,  0,  0, 13,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        1,  0,  0,  0,  1
    );

    const bass = array(
        1,   0,  1,  0,  1,  0,  1,  0,
        13,  0, 11,  0,  9,  0, 11,  0, 13,  0, 11,  0,  9,  0,  8,  0,
        13,  0,  1,  0, 13,  8, 13,  8, 13,  8, 13,  8, 16, 11, 13,  8,
        16, 11, 13,  8, 13,  0,  1,  0, 13, 18, 16,  8, 13, 18, 16,  8,
        13, 13, 11, 18, 13, 13, 11, 18, 13,  0,  1
    );

    fn rand(co: f32) -> f32 {
       return fract(sin(co*(91.3458)) * 47453.5453);
    }

    fn generateMusicFn(time: f32) -> vec2f {
        var ret = vec2f(0);        

        for (var s=1;s<3;s++) {       
            var u = time+f32(s);
            var m = 0.;
            for (var a=9.;a<99.;a/=.99) {
                 m += sin(u*a)/a;
                u+=a;
            }

            {
                let r = time * 6.0;
                var v = fract(r) + 1e-4;
                var row = i32(r) - 128;
                for (var rd = 0; rd < 9 && row >= 0; rd++) {
                    let n = melody[row];
                    let f = exp2(f32(n) / 12.0 + 9.6);
                    if (n != 0 && row < 933) {
                        ret.x += (sin(
                            sin(time * f) * cosh(sin(r + f32(s))) * cosh(time / 90.0) + m
                        )) * exp2(-1.5 * v - 0.01 / v - 1.0);
                    }
                    v += 1.0;
                    row -= 1;
                }
            }

            {
                let r = time * 6.0 / 16.0;
                var v = fract(r) + 1e-4;
                var row = i32(r);
                for (var rd = 0; rd < 9 && row >= 0; rd++) {
                    let n = bass[row];
                    let f = exp2(f32(n) / 12.0 + 7.6);
                    if (n != 0 && row < 67) { // todo: that 67 should be length of bass array
                        ret.x += (sin(sin(time * f) * (3.0 - v) * 2.0 + m)) * exp2(-2.0 * v - 0.1 / v);
                    }
                    v += 1.0;
                    row -= 1;
                }
            }
    
            ret=ret.yx;
        }        
        return ret*atan(time/20.)/3.+rand(time)*(4.-cos(time*3./16.*3.1415))*.0005;
    }

    @group(0) @binding(0) var<storage, read_write> buffer : array<f32>;
    @compute @workgroup_size(4,4,4)
    fn main(@builtin(global_invocation_id) global_id : vec3<u32>) {
        var index = global_id.x + global_id.y * 256 + global_id.z * 256 * 256;
        if (index > 48000*180) { return; } // TODO: Omit from final intro, early return, buffer is bigger than audio
        var u = f32(index) / 48000;
        var result = vec2f(0);
        for (var a = 1.; a>.01; a/=2.) {
            result += generateMusicFn(u)*a;
            u -= .5;
            result = result.yx;
        }
        // result = vec2f(1) * sin(u * 3.141 * 440 * 2);
        buffer[index] = result.x;
        buffer[index + 48000*180] = result.y;
        // TODO: Could store envelope etc. for visuals here
        // buffer[index + 48000*180*4 * 2] = result.x + result.y;
    }
    `;

    navigator.gpu.requestAdapter().then(
        a=>a.requestDevice({
            requiredLimits: {
                maxStorageBufferBindingSize: BUFFER_DIM * BUFFER_DIM * BUFFER_DIM * 16,
                maxBufferSize: BUFFER_DIM * BUFFER_DIM * BUFFER_DIM * 16
            },
        }).then(d => playWithDevice(d, musicWgsl)));
}
