// These variables are templated in Javascript: ZWXYQ

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    var o = vec3(global_id.x, global_id.y, global_id.z * 2 + (global_id.x + global_id.y + global_id.z + Q) % 2);
    // #reorder
    var k = to_index(X, o) + Z; // #and
    var b = vec3i(o); // #endreorder
    $pressure[k] = (
        $pressure[Z + clamp_to_edge(X, b - vec3(1,0,0))]
        // #reorder
        + $pressure[Z + clamp_to_edge(X, b + vec3(1,0,0))] // #and
        + $pressure[Z + clamp_to_edge(X, b - vec3(0,1,0))] // #and
        + $pressure[Z + clamp_to_edge(X, b + vec3(0,1,0))] // #and
        + $pressure[Z + clamp_to_edge(X, b - vec3(0,0,1))] // #and
        + $pressure[Z + clamp_to_edge(X, b + vec3(0,0,1))] // #endreorder
        - $temperature_out[k] / X / X) / 6; // /(X*X)
}
