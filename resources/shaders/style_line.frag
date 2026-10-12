#version 330 core
uniform vec4 u_color;
uniform float u_fade;
uniform vec3 u_fade_color;
uniform int u_stipple;
uniform float u_dash_px;
uniform int u_axis_color;
flat in vec3 v_direction;
flat in vec2 v_origin;
noperspective in vec2 v_pixel;
out vec4 fragColor;
void main() {
    float along=length(v_pixel-v_origin);
    if (u_stipple==4 && mod(along,2.0*u_dash_px)>=u_dash_px) discard;
    if (u_stipple==5 && mod(along,u_dash_px)>=1.25) discard;
    vec3 color=u_color.rgb;
    if (u_axis_color==1) {
        vec3 direction=abs(v_direction);
        if (direction.x>.9999) color=vec3(.86,.22,.27);
        else if (direction.y>.9999) color=vec3(.16,.62,.36);
        else if (direction.z>.9999) color=vec3(.20,.40,.78);
    }
    fragColor=vec4(mix(color,u_fade_color,u_fade),u_color.a);
}
