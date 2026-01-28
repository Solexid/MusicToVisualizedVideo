//!DESC Circle Projection Shader - libplacebo compatible with dynamic scaling
//!HOOK LUMA
//!HOOK RGB
//!COMPONENTS 4
//!BIND HOOKED

vec4 hook()
{
    // Get texture size
    vec2 tex_size = HOOKED_size;

    // Sample the input texture multiple times to estimate luma density
    float total_luma = 0.0;
    int samples = 16;

    // Sample in a grid pattern
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            vec2 sample_pos = vec2(
                float(i) / 3.0,
                float(j) / 3.0
            );
            total_luma += HOOKED_tex(sample_pos).r;
        }
    }

    // Calculate average luma
    float avg_luma = total_luma / float(samples);

    // Calculate scale based on luma: more luma = smaller scale (zoom in)
    // Scale range: 0.5 (minimum) to 2.0 (maximum)
    // At 100% luma: scale = 0.5 (zoomed in)
    // At 0% luma: scale = 2.0 (zoomed out)
    float scale = 1.25 - (avg_luma * 2);

    // Convert to pixel coordinates centered at 0,0
    vec2 pixel = (HOOKED_pos * tex_size) - tex_size * 0.5;

    // Calculate distance from center
    float dist = sqrt(pixel.x * pixel.x + pixel.y * pixel.y);

    // Calculate angle from center
    float angle = atan(pixel.y, pixel.x);

    // Apply the same formula as the geq filter for circular projection
    // W/PI*(PI+atan2(H/2-Y,X-W/2))
    float mapped_angle = mod(tex_size.x / 3.14159265359 * (3.14159265359 + angle), tex_size.x);

    // H-2*hypot(H/2-Y,X-W/2)
    float mapped_dist = tex_size.y - 2.0 * dist;

    // Convert back to UV coordinates
    vec2 mapped_uv = vec2(
        mapped_angle / tex_size.x,
        mapped_dist / tex_size.y
    );

    // Apply scale to the UV coordinates
    vec2 scaled_uv = mapped_uv / scale;

    // Sample the texture at the mapped coordinates
    vec4 mapped_color = HOOKED_tex(scaled_uv);

    // Create circular boundary with transparency (scale radius with the scale factor)
    float radius = tex_size.y * 0.5 / scale;
    float edge = smoothstep(radius, radius * 0.7, dist);

    // Apply transparency outside the circle
    mapped_color.a *= edge;

    return mapped_color;
}
