// These variables are templated in Javascript: ZWXYQ

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    var b = $pressure[W + to_index(Y, global_id)];
    // #reorder
    $pressure[Z + to_index(X, global_id * 2)] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(1,0,0))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(0,1,0))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(1,1,0))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(0,0,1))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(1,0,1))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(0,1,1))] = b; // #and
    $pressure[Z + to_index(X, global_id * 2 + vec3(1,1,1))] = b; // #endreorder
}
