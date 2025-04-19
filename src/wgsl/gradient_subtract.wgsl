@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec3i(global_id); // #and
    var k = to_index(P_GRID_RES_X, global_id); // #endreorder
    $velocity_in[k] -= vec4(
        $pressure[clamp_to_edge(P_GRID_RES_X, b + vec3(1,0,0))] - $pressure[clamp_to_edge(P_GRID_RES_X, b - vec3(1,0,0))],
        $pressure[clamp_to_edge(P_GRID_RES_X, b + vec3(0,1,0))] - $pressure[clamp_to_edge(P_GRID_RES_X, b - vec3(0,1,0))],
        $pressure[clamp_to_edge(P_GRID_RES_X, b + vec3(0,0,1))] - $pressure[clamp_to_edge(P_GRID_RES_X, b - vec3(0,0,1))],
        0) / 2 * P_RDX;
}
