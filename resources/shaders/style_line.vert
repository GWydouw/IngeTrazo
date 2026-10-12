#version 330 core
layout(location=0) in vec3 a_pos;
layout(location=3) in vec4 a_inst0;
layout(location=4) in vec4 a_inst1;
layout(location=5) in vec4 a_inst2;
layout(location=6) in vec4 a_inst3;
uniform mat4 u_mvp;
uniform vec4 u_clip_plane;
uniform int u_clip_enable;
out vec3 g_world;
out float g_clip;
void main() {
    vec4 world = mat4(a_inst0,a_inst1,a_inst2,a_inst3) * vec4(a_pos,1.0);
    g_world = world.xyz;
    g_clip = u_clip_enable == 1 ? dot(world,u_clip_plane) : 1.0;
    gl_Position = u_mvp * world;
}
