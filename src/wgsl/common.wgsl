// #reorder
struct U {
    d : f32,
    t : f32
}
// #and
fn D(p: vec3f) -> vec3f { // By David Hoskins, MIT License https://www.shadertoy.com/view/4djSRW
    var x = fract(p * vec3(.1031, .1030, .0973));
    x += dot(x, x.yxz + 33.33);
    return fract((x.xxy + x.yxx) * x.zyx);
}
// #and
fn to_index(t: u32, p: vec3u) -> u32 {
    return p.x + p.y * t + p.z * t * t;
}
// #and
fn clamp_to_edge(t: u32, p: vec3i) -> u32 {
    return to_index(t, vec3u(clamp(
        p,
        vec3i(0),
        vec3i(i32(t) - 1)
    )));
}
// #and
fn add_smoke(t: vec4f, p: vec4f) -> vec4f {
    var b = p.w + t.w;
    // #alternative
    if (b == 0) {
        return t;
    }
    return vec4(mix(p.xyz, t.xyz, t.w / b), b);
    // #or
    return select(
        vec4(mix(p.xyz, t.xyz, t.w / b), b),
        t,
        b == 0
    );
    // #endalternative
}
// #and
fn trilerp1(
    t: ptr<storage, array<f32>, read_write>,
    p: vec3f
) -> f32 {
    var b = vec3i(p + .5) - 1; // To avoid negative rounding
    var f = fract(p + .5);
    return mix(
        mix(
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b)],                 (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 0, 0))], f.x),
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 1, 0))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 1, 0))], f.x),
            f.y
        ),
        mix(
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 0, 1))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 0, 1))], f.x),
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 1, 1))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 1, 1))], f.x),
            f.y
        ),
        f.z
    );
};

fn trilerp4(
    t: ptr<storage, array<vec4f>, read_write>,
    p: vec3f
) -> vec4f {
    var b = vec3i(p + .5) - 1; // To avoid negative rounding
    var f = fract(p + .5);
    return mix(
        mix(
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b)],                 (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 0, 0))], f.x),
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 1, 0))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 1, 0))], f.x),
            f.y
        ),
        mix(
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 0, 1))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 0, 1))], f.x),
            mix((*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(0, 1, 1))], (*t)[clamp_to_edge(P_GRID_RES_X, b + vec3(1, 1, 1))], f.x),
            f.y
        ),
        f.z
    );
};
// #and
// Interestingly these don't need to be in any particular place or order, so freely reorder them
// #reorder
@group(0) @binding(0) var<storage, read_write> $pressure : array<f32>; // #and
@group(0) @binding(1) var<storage, read_write> $temperature_in : array<f32>; // #and
@group(0) @binding(2) var<storage, read_write> $temperature_out : array<f32>; // #and
@group(0) @binding(3) var<storage, read_write> $velocity_in : array<vec4f>; // #and
@group(0) @binding(4) var<storage, read_write> $velocity_out : array<vec4f>; // #and
@group(0) @binding(5) var<storage, read_write> $smoke_in : array<vec4f>; // #and
@group(0) @binding(6) var<storage, read_write> $smoke_out : array<vec4f>; // #and
@group(0) @binding(7) var<storage, read_write> $tmp : array<vec4f>; // #and
@group(0) @binding(8) var<uniform> u : U; // #and
@group(0) @binding(9) var T: texture_storage_2d<P_PRESENTATION_FORMAT, write>; // #endreorder

// #endreorder
