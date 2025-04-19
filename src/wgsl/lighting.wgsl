@compute @workgroup_size(8,8)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    var b = vec3i(global_id);
    var k = vec3(b.x, P_GRID_RES_MINUS_ONE, b.y); // right
    var d = vec3(0, -1, 0); // right
    if (u.t > 21.4) {
        k = vec3(b.x, 0, b.y); // left
        d = vec3(0, 1, 0); // left
    }
    if (u.t > 37.4) {
        k = vec3(b.x, b.y, P_GRID_RES_MINUS_ONE); // top
        d = vec3(0, 0, -1); // top
    }
    // Briefly dim lights when transitioning, compensate with increased ambient light
    var a = smoothstep(0, .5, abs(u.t - 21.4)) * smoothstep(0, .5, abs(u.t - 37.4));
    var c = vec3(1.5) * a; // Light
    for (var i = 0; i < P_GRID_RES_X; i++) {
        var k = to_index(P_GRID_RES_X, vec3u(k + d * i)); // Variable shadowing, bad?
        // #reorder
        var s = $smoke_in[k]; // #and
        var t = $temperature_in[k]; // #endreorder
        $smoke_out[k] = vec4(
            s.xyz * (c // Light
                + vec3(.04 + .5 - .5 * a) // Ambient light
                + mix( // Blackbody color
                    vec3(.5, .3, .1),
                    mix(
                        vec3(1, .6, .3),
                        vec3(.89, .91, 1),
                        clamp((t - 2) / 4, 0, 1)),
                    clamp((t - 1) / 2, 0, 1)
                ) * max(0, t - 1) * P_BLACKBODY_BRIGHTNESS),
            s.w
        );
        c *= exp(-(1 - s.xyz) * s.w * P_OPTICAL_DENSITY / P_GRID_RES_X);
    }
}
