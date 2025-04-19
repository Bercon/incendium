// #alternative

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec3i(global_id); // #and
    var k = to_index(P_GRID_RES_X, global_id); // #endreorder
    $temperature_out[k] = (
          $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(1,0,0))].x * (1 - 2 * f32(global_id.x == P_GRID_RES_MINUS_ONE))
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(1,0,0))].x * (1 - 2 * f32(global_id.x != 0))
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,1,0))].y * (1 - 2 * f32(global_id.y == P_GRID_RES_MINUS_ONE))
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,1,0))].y * (1 - 2 * f32(global_id.y != 0))
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,0,1))].z * (1 - 2 * f32(global_id.z == P_GRID_RES_MINUS_ONE))
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,0,1))].z * (1 - 2 * f32(global_id.z != 0))
    ) / 2 * P_RDX;
}

// #or

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec3i(global_id); // #and
    var k = to_index(P_GRID_RES_X, global_id); // #endreorder
    $temperature_out[k] = (
        $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(1,0,0))].x * select(1., -1., global_id.x == P_GRID_RES_MINUS_ONE)
        - $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(1,0,0))].x * select(1., -1., global_id.x == 0)
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,1,0))].y * select(1., -1., global_id.y == P_GRID_RES_MINUS_ONE)
        - $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,1,0))].y * select(1., -1., global_id.y == 0)
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,0,1))].z * select(1., -1., global_id.z == P_GRID_RES_MINUS_ONE)
        - $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,0,1))].z * select(1., -1., global_id.z == 0)
    ) / 2 * P_RDX;
}

// #or

@compute @workgroup_size(4,4,4)
fn n(@builtin(global_invocation_id) global_id : vec3u) {
    // #reorder
    var b = vec3i(global_id); // #and
    var k = to_index(P_GRID_RES_X, global_id); // #and
    var c = 1 - 2 * vec3f(global_id != vec3(0)); // #and
    var a = 1 - 2 * vec3f(global_id == vec3(P_GRID_RES_MINUS_ONE)); // #endreorder
    $temperature_out[k] = (
        $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(1,0,0))].x * a.x
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(1,0,0))].x * c.x
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,1,0))].y * a.y
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,1,0))].y * c.y
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b + vec3(0,0,1))].z * a.z
        + $velocity_in[clamp_to_edge(P_GRID_RES_X, b - vec3(0,0,1))].z * c.z
    ) / 2 * P_RDX;
}

// #endalternative