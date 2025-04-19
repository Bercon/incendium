// These variables are templated in Javascript: ZWXYQ

// Render: smoke_out -> velocity_out
// blur H: velocity_out -> smoke_out, X=width, Y=1, Q=width
// blur V: smoke_out -> tmp, X=1, Y=width, Q=height
// blur H: tmp -> smoke_out
// blur V: smoke_out -> tmp
// comp: velocity_out, tmp -> canvas

@compute @workgroup_size(60)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec4(0.); // #and
    var j = P_GLOW_RADIUS; // #and
    var o = i32(global_id.x) * X; // #endreorder
    for (var i = 0; i < j; i++) {
        b += Z[o + Y * i];
    }
    for (var i = 0; i < Q; i++) {
        // #reorder
        var l = i - P_GLOW_RADIUS - 1; // #and
        var r = i + P_GLOW_RADIUS; // #endreorder
        // #reorder
        if (l >= 0) {
            b -= Z[o + Y * l];
            j--;
        } // #and
        if (r < Q) {
            b += Z[o + Y * r];
            j++;
        } // #endreorder
        // Because of floating point errors, color may end up being negative
        // W[o + Y * i] = max(vec4(0), b / f32(j));
        W[o + Y * i] = b / f32(j); // Negative values doesn't seem to be a big issue
    }
}
