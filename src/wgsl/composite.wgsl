
// comp: velocity_out, tmp -> canvas
@compute @workgroup_size(8, 8)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    var b = pow(
        $velocity_out[global_id.x + global_id.y * P_CANVAS_WIDTH]
        + pow($tmp[global_id.x + global_id.y * P_CANVAS_WIDTH], vec4(1.5)) * .15, // Glow
        vec4(.55)
    );
    b = // Increase saturation
        // #alternative
        b * 1.5 - .5 * dot(b, vec4(.21, .71, .07, .0)) // #or
        mix(vec4(dot(b, vec4(.21, .71, .07, 0))), b, 1.5) // #endalternative
        + D(vec3(vec2f(global_id.xy), u.t)).x / 255; // Debanding
    b.w = 1;
    textureStore(T, global_id.xy, b);
}
