/*
 * Draw camera-projected triangles over an RGB frame without an OpenGL context.
 * Every vertex supplies screen x, screen y, and positive camera distance.
 */
#include <math.h>
#include <stdint.h>
#include <string.h>

static int bound(int value, int maximum) {
    return value < 0 ? 0 : value > maximum ? maximum : value;
}

void loopday_raster(int width, int height, int count, const float *triangles,
                    const uint8_t *shades, uint8_t *rgb, float *depth) {
    memset(depth, 0, (size_t)width * (size_t)height * sizeof(float));
    for (int triangle = 0; triangle < count; ++triangle) {
        const float *point = triangles + triangle * 9;
        const uint8_t *shade = shades + triangle * 3;
        float ax = point[0], ay = point[1], ar = 1.0f / point[2];
        float bx = point[3], by = point[4], br = 1.0f / point[5];
        float cx = point[6], cy = point[7], cr = 1.0f / point[8];

        int left = bound((int)floorf(fminf(ax, fminf(bx, cx))), width);
        int top = bound((int)floorf(fminf(ay, fminf(by, cy))), height);
        int right = bound((int)ceilf(fmaxf(ax, fmaxf(bx, cx))), width);
        int bottom = bound((int)ceilf(fmaxf(ay, fmaxf(by, cy))), height);

        float area = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
        if (fabsf(area) < 0.00001f || left >= right || top >= bottom) continue;

        float dax = (by - cy) / area, day = (cx - bx) / area;
        float dbx = (cy - ay) / area, dby = (ax - cx) / area;
        float delta_x = (ar - cr) * dax + (br - cr) * dbx;
        float initial_x = (float)left + .5f - cx;
        for (int y = top; y < bottom; ++y) {
            float offset_y = (float)y + .5f - cy;
            float a = dax * initial_x + day * offset_y;
            float b = dbx * initial_x + dby * offset_y;
            float zr = (ar - cr) * a + (br - cr) * b + cr;
            int offset = y * width + left;
            for (int x = left; x < right; ++x, ++offset) {
                if (a >= 0.0f && b >= 0.0f && a + b <= 1.0f && zr >= depth[offset]) {
                    depth[offset] = zr;
                    uint8_t *pixel = rgb + offset * 3;
                    pixel[0] = shade[0];
                    pixel[1] = shade[1];
                    pixel[2] = shade[2];
                }
                a += dax;
                b += dbx;
                zr += delta_x;
            }
        }
    }
}
