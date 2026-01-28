//!DESC Circle Projection Shader - libplacebo compatible
//!HOOK LUMA
//!HOOK RGB
//!COMPONENTS 4
//!BIND HOOKED

vec4 hook()
{
    // Get current color
    vec4 color = HOOKED_tex(HOOKED_pos);
    
    // Get texture size
    vec2 tex_size = HOOKED_size;
    
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
    
    // Sample the texture at the mapped coordinates
    vec4 mapped_color = HOOKED_tex(mapped_uv);
    
    // Create circular boundary with transparency
    float radius = tex_size.y * 0.5;
    float edge = smoothstep(radius, radius * 0.7, dist);
    
    // Apply transparency outside the circle
    mapped_color.a *= edge;
    
    return mapped_color;
}
