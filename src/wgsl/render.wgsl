@compute @workgroup_size(8,8)
fn n(@builtin(global_invocation_id) global_id: vec3u) {
    var b = vec2f(global_id.xy);
    var r = D(vec3(vec2f(global_id.xy), u.t)); // Same as composite.wgsl
    // #alternative
    var c = (b + r.xy - .5 * vec2f(P_CANVAS_WIDTH, P_CANVAS_HEIGHT)) / P_CANVAS_WIDTH; // #or
    var c = (b + r.xy - vec2f(P_CANVAS_WIDTH, P_CANVAS_HEIGHT) / 2) / P_CANVAS_WIDTH; // #endalternative

    var o = smoothstep(32, 36, u.t); // Orthographic / pinhole transition
    var t = max(0, u.t - 32) * o;
    var a = 2.8 - .8 * abs(cos(t * .1));
    var p = vec3( // Camera position
        sin(t * .3) * a,
        cos(t * .3) * a,
        sin(t * .1) - .2 * o
    );
    // Camera basis
    var z = normalize(-p);
    var x = normalize(vec3(z.y, -z.x, 0));
    var y = cross(z, x);
    // Basic pinhole camera dir
    var d = z
        + c.x * x // * fov
        + c.y * y; // * fov
    // Ortho projection blend
    p = mix(
        // #alternative
        p + x * c.x * 2 + y * c.y * 2 + y * .4375, // #or
        p + x * c.x * 2 + y * c.y * 2 + y * (P_CANVAS_WIDTH - P_CANVAS_HEIGHT) / P_CANVAS_WIDTH, // #endalternative
        p,
        o);
    d = normalize(mix(z, d, o));
    // Ray-box intersection
    // #reorder
    x = (-1 - p) / d;// #and
    y = (1 - p) / d; // #endreorder
    z = min(x, y);
    x = max(x, y);
    // #reorder
    t = max(z.x, max(z.y, z.z));// #and
    o = min(x.x, min(x.y, x.z)); // #endreorder
    x = vec3(0); // Color
    if (t <= o) { // Hit
        // #reorder
        a = 1; // #and
        t = P_STEP_LENGTH * r.z + max(0, t); // #endreorder
        while (t < o) { // Raymach loop
            // #alternative
            var s = trilerp4(&$smoke_out, .5 + .5 * (p + d * t + 1) * P_GRID_RES); // #or
            var s = trilerp4(&$smoke_out, .5 + (p + d * t + 1) * P_GRID_RES_BY_2); // #endalternative
            // #reorder
            s.w *= P_STEP_LENGTH * P_OPTICAL_DENSITY;// #and
            t += P_STEP_LENGTH;// #endreorder
            a *= exp(-s.w);
            x += a * s.xyz * s.w;
        }
    }
    $velocity_out[global_id.x + global_id.y * P_CANVAS_WIDTH] = vec4(x, 1);
}
