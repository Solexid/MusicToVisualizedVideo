//!DESC Circular wave projection (GPU replacement for geq)
//!HOOK LUMA
//!HOOK RGB
//!COMPONENTS 4
//!BIND HOOKED

vec4 hook()
{
    vec2 tex_size = HOOKED_size;
    float PI = 3.14159265359;

    // Current fragment in pixel coordinates
    vec2 pixel = HOOKED_pos * tex_size;

    // Vector from center — note Y is inverted to match geq coordinate system
    // geq uses atan2(H/2-Y, X-W/2) where Y=0 is top
    vec2 from_center = vec2(
        pixel.x - tex_size.x * 0.5,
        tex_size.y * 0.5 - pixel.y
    );

    // Angle from center (same as atan2 in geq)
    float angle = atan(from_center.y, from_center.x);

    // Map angle to source X: W/PI * (PI + angle), wrapped
    float mapped_x = mod(tex_size.x / PI * (PI + angle), tex_size.x);

    // Map distance from center to source Y: H - 2 * distance
    float dist = length(from_center);
    float mapped_y = tex_size.y - 2.0 * dist;

    // Convert to UV coordinates
    vec2 uv = vec2(mapped_x, mapped_y) / tex_size;

    // Sample source texture at mapped coordinates
    vec4 color = HOOKED_tex(uv);

    // Circular mask — hide pixels outside radius H/2
    float radius = tex_size.y * 0.5;
    if (dist > radius) {
        color.a = 0.0;
    }

    return color;
}
