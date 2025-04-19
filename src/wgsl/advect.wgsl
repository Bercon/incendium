
@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    var k = to_index(P_GRID_RES_X, global_id);
    var p = vec3f(global_id) + .5 - u.d * $velocity_in[k].xyz * P_RDX;
    // #reorder
    var v = trilerp4(&$velocity_in, p); // #and
    var s = trilerp4(&$smoke_in, p); // #and
    // #alternative
    var w = vec3f(global_id) / P_GRID_RES * 2 - 1; // #or
    var w = vec3f(global_id) / P_GRID_RES_BY_2 - 1; // #endalternative
    // #endreorder
    var t = min(v.w, u.d * P_BURN_RATE); // Amount of fuel burnt
    s.w *= exp(-u.d * select(.8, 1.4, u.t > 120));
    // #reorder
    v = vec4(v.xyz * exp(-u.d * P_VELOCITY_DECAY), v.w - t); // #and
    s = add_smoke(s, vec4(
        select(s.xyz, vec3(.3), u.t < 149), // Emit smoke at current cell smoke color in the end
        t * P_BURN_SMOKE_EMIT)); // #and
    var f = trilerp1(&$temperature_in, p) * exp(-u.d * P_TEMPERATURE_DECAY)
        + t * P_BURN_HEAT_EMIT; // #and
    var a = u.t * 6; // Used by flamethrower part
    // #endreorder

    // Emit

    // #reorder
    // "Droplets / Rain"
    if (u.t < 21.4) {
        for (var i = 0; i < 30; i++) {
            t = max(0, u.t * .1 - .1 - f32(i) / 30);
            var r = D(vec3(floor(t), 9, f32(i) * 90));
            p = vec3(
                2 * r.x - 1 + sin(t * 20 + 6 * r.y) * .1,
                0,
                1.1 - 2.2 * fract(t)
            );
            a = u.d * clamp(-(length(w - p) - .04) / .05, 0, 1);
            // #reorder
            s = add_smoke(s, vec4(vec3(.7), a * 10)); // #and
            f -= 5 * a; // #endreorder
        }
    }
    // #and
    // Brush strokes
    if ((u.t > 21.4 && u.t < 53.4)
        || (u.t > 149 && u.t < 170.7)
    ) {
        for (var i = 0; i < 8 + select(0, 4, u.t > 100); i++) {
            t = u.t / 16 * 3;
            var r = D(vec3(floor(t), 9, f32(i) * 90));
            a = t * 3 * sign(r.y - .5) + 20 * r.x;
            p = vec3(cos(a), sin(a), sin(a / 3) * .5) * (.5 + .4 * r.z)
            + (
                vec3(cos(a), sin(a), 0) * cos(a * 8 + 6 * r.y)
                + vec3(0, 0, 1) * sin(a * 8 + 6 * r.y)
            ) * .1;
            p.y *= step(32, u.t); // Flaten during 2D part
            a = u.d * clamp(-(length(w - p)
                - .08 * smoothstep(0, .2, fract(t))
                - .02 * smoothstep(.95, 1, fract(t))
                - .02 * step(90, u.t)
            ) / .05, 0, 1);

            // #reorder
            v += vec4(
                0,
                0,
                20 * smoothstep(.95, 1, fract(t)),
                4 * step(90, u.t)
            ) * a; // #and
            f -= 10 * a * sign(100 - u.t);  // #and
            s = add_smoke(s,
                vec4(
                    mix(
                        mix(
                            vec3(.8),
                            vec3(.7, 0, 0),
                            step(32, u.t) * step(4, f32(i))
                        ),
                        .5 + .5 * cos(floor(t) + f32(i) * 9 + vec3(0, 2, 4)),
                        step(90, u.t)
                    ),
                    (20 - 18 * step(90, u.t)) * a
                )
            ); // #endreorder
        }
    }
    // #and
    // Colliding rings
    if (u.t > 58 && u.t < 82) {
        t = u.t / 16 * 6 - .5;
        // #alternative
        p = 1.4 * D(vec3(floor(t), 9, 9)) - .7; // #or
        p = (D(vec3(floor(t), 9, 9)) * 2 - 1) * .7; // #endalternative
        for (var i = 0; i < 2; i++) {
            p *= -1;
            a = u.d * clamp(-(length(w - p) - .2) / .03, 0, 1) * smoothstep(.95, 1, sin(fract(t) * 3) * sin(fract(t) * 3));
            // #reorder
            v += vec4(normalize(-p + D(vec3(floor(t), 9, f32(i))) * .2), 0) * 30 * a; // #and
            s = add_smoke(s, vec4(.5 + .5 * cos(floor(t) + f32(i) * 9 + vec3(0, 2, 4)), 30 * a)); // #and
            f -= 20 * a; // #endreorder
        }
    }
    // #and
    // Explosions
    if (u.t > 83 && u.t < 104
        && array(Z)[i32(u.t * 6) - P_MELODY_START]
         + array(Z)[i32(u.t * 6) - P_MELODY_START - 1] > 0
    ) {
        t = u.t * 6 - .5;
        for (var i = 0; i < 4; i++) {
            p = (1 - D(vec3(floor(t), 9, f32(i))) * 2) * .8;
            a = u.d * clamp(-(length(w - p) - .2 * sin(fract(t) * 3) * sin(fract(t) * 3)) / .03, 0, 1);
            var r = normalize(w - p) * 2 + f32(i) + w * 9; // Noise position
            v += vec4(
                normalize(w - p) * (.5 + (sin(r.x) / 2 * sin(r.y * 1.5) * sin(r.z * 2.5))) // Noise
                * 100,
                0) * a;
            s = add_smoke(s, vec4(.5 + .5 * cos(floor(t) + f32(i) * 9 + vec3(0, 2, 4)), 10 * a));
        }
    }
    // #and
    // Rotating flaming spheres
    if (
        (u.t > 106.7 && u.t < 138)
        || (u.t > 173.3 && u.t < 174)
    ) {
        for (var i = 0; i < i32(1 + (u.t - 106.7) / 16 * 6); i++) {
            t = u.t * .5 + 6 * f32(i) / (1 + (u.t - 80) / 6);
            p = vec3(sin(t), cos(t), sin(t * .5) * .2 - .75) * .6;
            a = u.d * clamp(-(length(w - p) - .1) / .03, 0, 1);
            var r = normalize(w - p) * 2 + f32(i) + w * 9; // Noise position
            v += vec4(
                normalize(w - p) * (.5 + (sin(r.x) / 2 * sin(r.y * 1.5) * sin(r.z * 2.5))) // Noise
                * 30,
                9 + 9 * sin(u.t * 10 + f32(i))
            ) * a;
        }
    }
    // #and
    // Flamethrower
    if (u.t > 139 && u.t < 149) {
        v += vec4(.04, sin(a), cos(a), 10)
            * u.d * clamp(-(length(w + vec3(0, 0, .2)) - .1) / .03, 0, 1)
            * 30 * (1 + sin(u.t * 60));
    }
    // #and
    if (u.t > 86 && u.t < 87) { // Center push down
        v.z -= u.d * (1 - abs(w.x));
    }
    // #and
    if ( // Vortex
        (u.t > 95 && u.t < 101)
        || (u.t > 122 && u.t < 128)
        || (u.t > 155 && u.t < 165)
    ) {
        v.x += w.y * u.d * .2;
        v.y += -w.x * u.d * .2;
    }

    // #endreorder
    p = vec3(0, 0, 1); // Gravity direction

    // #reorder
    if (u.t > 128 && u.t < 136) { // Gravity to torus
        a = .7;
        a /= length(w.xz) + .001;
        p = vec3(w.x, 0, w.z) * a - w;
        p /= length(p) + .001;
    }
    // #and
    if (u.t > 136 && u.t < 170) { p = w; } // Gravity to center
    // #endreorder

    // #reorder
    $velocity_out[k] = v + vec4(p, 0) * f * u.d * P_BOYANCY;  // #and
    $smoke_out[k] = s; // #and
    $temperature_out[k] = f; // #endreorder
}
