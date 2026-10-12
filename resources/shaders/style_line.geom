#version 330 core
layout(lines) in;
layout(triangle_strip, max_vertices=12) out;
in vec3 g_world[];
in float g_clip[];
uniform vec2 u_viewport_px;
uniform float u_line_width;
uniform float u_extension;
uniform float u_endpoint;
uniform float u_depth_width;
uniform vec3 u_eye;
uniform float u_distance;
flat out vec3 v_direction;
flat out vec2 v_origin;
noperspective out vec2 v_pixel;
void point(vec4 c, vec2 offset, float clip) {
    gl_Position = c;
    gl_Position.xy += offset * 2.0 / u_viewport_px * c.w;
    gl_ClipDistance[0] = clip;
    v_pixel = (gl_Position.xy/gl_Position.w*.5+.5)*u_viewport_px;
    EmitVertex();
}
void cap(vec4 p, float clip) {
    float r = u_endpoint*.5;
    point(p,vec2(-r,-r),clip); point(p,vec2(r,-r),clip);
    point(p,vec2(-r,r),clip); point(p,vec2(r,r),clip);
    EndPrimitive();
}
void main() {
    vec4 a=gl_in[0].gl_Position, b=gl_in[1].gl_Position;
    float ca=g_clip[0], cb=g_clip[1];
    // Clip the near-plane crossing before dividing by w: infinite lines
    // and edges crossing the eye must never turn into full-screen quads.
    float da=a.z+a.w, db=b.z+b.w;
    if (da<0.0 && db<0.0) return;
    if (da<0.0) { float t=da/(da-db); a=mix(a,b,t); ca=mix(ca,cb,t); }
    if (db<0.0) { float t=db/(db-da); b=mix(b,a,t); cb=mix(cb,ca,t); }
    if (a.w<=0.0 || b.w<=0.0) return;
    vec2 pa=(a.xy/a.w*.5+.5)*u_viewport_px;
    vec2 pb=(b.xy/b.w*.5+.5)*u_viewport_px;
    vec2 delta=pb-pa;
    if (length(delta)<0.001) return;
    vec2 d=normalize(delta), n=vec2(-d.y,d.x);
    v_origin=pa; v_direction=normalize(g_world[1]-g_world[0]);
    float distance=max(length((g_world[0]+g_world[1])*.5-u_eye),.001);
    float width=max(u_line_width, mix(1.0,u_depth_width,clamp(u_distance/distance*.5,0.0,1.0)));
    point(a,-d*u_extension-n*width*.5,ca);
    point(a,-d*u_extension+n*width*.5,ca);
    point(b, d*u_extension-n*width*.5,cb);
    point(b, d*u_extension+n*width*.5,cb);
    EndPrimitive();
    if (u_endpoint>0.0) { cap(a,ca); cap(b,cb); }
}
