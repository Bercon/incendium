// These variables are templated in Javascript: ZWXYQ

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    $temperature_out[W + to_index(Y, global_id)] = (
        $temperature_out[Z + to_index(X, global_id * 2)]
        // #reorder
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(1,0,0))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(0,1,0))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(1,1,0))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(0,0,1))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(1,0,1))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(0,1,1))] // #and
        + $temperature_out[Z + to_index(X, global_id * 2 + vec3(1,1,1))] // #endreorder
    ) / 8;
}
