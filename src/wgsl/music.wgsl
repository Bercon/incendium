@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec2f(0); // #and
    var k = to_index(P_GRID_RES_X, global_id); // #endreorder
    var t = f32(k) / P_SAMPLE_RATE;
    // Z is the note data for music
    var q = array(Z);
    for (var a = 1.; a > .01; a /= 2) {
        for (var j = 0; j < 2; j++) {
            // #reorder
            var u = t + f32(j); // #and
            var m = 0.; // #and
            var r = t * 6; // #endreorder
            for (var a = 3.; a < 99; a /= .99) {
                m += sin(u * a) / a;
                u += a;
            }
            var v = fract(r) + .0001;
            for (var i = i32(r) - P_MELODY_START; v < 9 && i >= 0; i--) {
                // q is the note data for music templated with Javascript
                var n = q[i];
                if (n > 0 && i < P_MELODY_NOTES_LENGTH) {
                    b.x += atan(t / 20) * sin(
                        sin(t * exp2(f32(n) / 12 + 9.6)) * cosh(sin(r + f32(j))) * cosh(t / 90) + m
                    ) * a / 3 * exp2(-.01 / v - v * 1.5 - 1);
                }
                v += 1;
            }

            r /= 16;
            v = fract(r) + .0001;
            for (var i = i32(r); v < 9 && i >= 0; i--) {
                // q has all data combined, so start with offset
                var n = q[i + P_MELODY_NOTES_LENGTH];
                if (n > 0 && i < P_BASS_NOTES_LENGTH) {
                    b.x += atan(t / 20) * sin(
                        sin(t * exp2(f32(n) / 12 + 7.6)) * (3 - v) * 2 + m
                    ) * a / 3 * exp2(-.01 / v - v * 2);
                }
                v += 1;
            }

            b = b.yx;
        }
        t -= .5;
        b = b.yx + D(vec3(t * 10000)).x * (4. - cos(t * .59)) * .0005 * a;
    }
    $pressure[k] = b.x;
    $pressure[k + P_GRID_RES_X * P_GRID_RES_X * P_GRID_RES_X] = b.y;
}
