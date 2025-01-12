//
// Created by donat on 03/10/2024.
//

#include "sdlEncapsulation.h"
#include <stdio.h>

// A 2D vector using doubles.
typedef struct {
    double x;
    double y;
} Dpp_Vec2;

typedef struct {
    //     X    Y
    double a00, a01,
           a10, a11;
} Matrix2D;

Dpp_Vec2 apply(Matrix2D transform, Dpp_Vec2 point) {
    return (Dpp_Vec2){
        .x = transform.a00 * point.x + transform.a01 * point.y,
        .y = transform.a10 * point.x + transform.a11 * point.y
    };
}

Dpp_Vec2 sub(Dpp_Vec2 a, Dpp_Vec2 b) {
    return (Dpp_Vec2){
        .x = a.x - b.x,
        .y = a.y - b.y
    };
}

Dpp_Vec2 add(Dpp_Vec2 a, Dpp_Vec2 b) {
    return (Dpp_Vec2) {
        .x = a.x + b.x,
        .y = a.y + b.y
    };
}

SDL_FPoint vec2ToSDL(Dpp_Vec2 vec) {
    return (SDL_FPoint){(float)vec.x, (float)vec.y};
}

int initSDL(SDL_Window **window, SDL_Renderer **renderer) {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

    *window = SDL_CreateWindow("SDL Line Drawing", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 1000, 800,
        SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE);
    if (*window == NULL) {
        printf("Window could not be created! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

    *renderer = SDL_CreateRenderer(*window, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (*renderer == NULL) {
        printf("Renderer could not be created! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

    // Enable bi-linear texture scaling
    SDL_SetHint( SDL_HINT_RENDER_SCALE_QUALITY, "1" );

    return 0; // Success
}

void drawCircleFill(SDL_Renderer* renderer, double centerX, double centerY, double radius) {
    for (int i = -(int)round(radius); i <= radius; i++) {
        for (int j = -(int)round(radius); j <= radius; j++) {
            if (pow(i, 2) + pow(j, 2) <= radius * radius) {
                SDL_RenderDrawPointF(renderer, (float)(centerX + (double)i), (float)(centerY + (double)j));
            }
        }
    }
}

void drawThickLine(SDL_Renderer *renderer, double x1, double y1, double x2, double y2, double thickness) {
    double dx = x2 - x1;
    double dy = y2 - y1;
    double length = sqrt(dx * dx + dy * dy);

    // Normalize direction vector
    double nx = dx / length;
    double ny = dy / length;

    // Perpendicular vector for thickness
    double px = -ny * (thickness / 2.0);
    double py = nx * (thickness / 2.0);

    // Fetch the current draw color to put them in our vertices
    SDL_Color color;
    SDL_GetRenderDrawColor(renderer, &color.r, &color.g, &color.b, &color.a);

    // Define the four corners of the thick line as a rectangle
    SDL_Vertex vertices[4] = {
        {.position = {(float)(x1 + px), (float)(y1 + py)}, .color = color}, // Top-left
        {.position = {(float)(x2 + px), (float)(y2 + py)}, .color = color}, // Top-right
        {.position = {(float)(x2 - px), (float)(y2 - py)}, .color = color}, // Bottom-right
        {.position = {(float)(x1 - px), (float)(y1 - py)}, .color = color}  // Bottom-left
    };

    // Indices for the two triangles forming the rectangle
    int indices[6] = {0, 1, 2, 2, 3, 0};

    SDL_RenderGeometry(renderer, NULL, vertices, 4, indices, 6);
}

// Utility function to rotate the four points of a rectangle, around the given pivot point.
// Used by: drawFilledRectangle, drawThickRectangle
static void applyRotation(Dpp_Vec2 points[4], Dpp_Vec2 pivot, double angleInRadians) {
    // Derived from Euler's formula
    Matrix2D rotMathis = {
        .a00 = cos(angleInRadians), .a01 = -sin(angleInRadians),
        .a10 = sin(angleInRadians), .a11 = cos(angleInRadians)
    };

    // Apply matrix transformations to all the points.
    for (int i = 0; i < 4; i++) {
        points[i] = add(apply(rotMathis, sub(points[i], pivot)), pivot);
    }
}

void drawRectangleFill(SDL_Renderer *renderer, double x, double y, double width, double height, double angleInRadians) {
    // Calculate the four points of the rectangle, and rotate them by using the first point as pivot.
    Dpp_Vec2 points[] = {
        {x, y},                     // Lower left corner
        {x, y + height},            // Upper left corner
        {x + width, y + height},    // Upper right corner
        {x + width, y},             // Lower right corner
    };
    applyRotation(points, points[0], angleInRadians);

    // Fetch the current draw color to put them in our vertices
    SDL_Color color;
    SDL_GetRenderDrawColor(renderer, &color.r, &color.g, &color.b, &color.a);

    // Make up the vertices
    SDL_Vertex vertices[] = {
        {.position = vec2ToSDL(points[0]), .color = color},
        {.position = vec2ToSDL(points[1]), .color = color},
        {.position = vec2ToSDL(points[2]), .color = color},
        {.position = vec2ToSDL(points[3]), .color = color}
    };
    // And the triangles
    int indices[] = {
        0, 1, 2, // llc -> ulc -> urc
        2, 3, 0 // urc -> lrc -> llc
    };

    // Draw!!!
    SDL_RenderGeometry(renderer, NULL, vertices, 4, indices, 6);
}

void drawRectangleOutline(SDL_Renderer* renderer, double x, double y, double width, double height,
    double angleInRadians, double thickness) {
    // Cap the thickness to avoid drawing outside the rectangle.
    if (thickness > width) {
        thickness = width;
    } else if (thickness > height) {
        thickness = height;
    }

    // Calculate the four points of the rectangle.
    Dpp_Vec2 points[] = {
        {x, y},                     // Lower left corner
        {x, y + height},            // Upper left corner
        {x + width, y + height},    // Upper right corner
        {x + width, y},             // Lower right corner
    };

    // Calculate the four "adjusted" points of the rectangles.
    // Those are used to draw horizontal lines (ulc->urc & lrc->llc) correctly in respect to thickness.
    double ht = thickness / 2; // Half thickness
    Dpp_Vec2 adjustedPoints[] = {
        {x - ht, y},                      // Lower left corner EXTENDED to the left
        {x - ht, y + height},             // Upper left corner EXTENDED to the left
        {x + width + ht, y + height},  // Upper right corner EXTENDED to the right
        {x + width + ht, y},           // Lower right corner EXTENDED to the right
    };

    // Apply the rotation to both points, with lower left corner as the pivot.
    applyRotation(points, points[0], angleInRadians);
    applyRotation(adjustedPoints, points[0], angleInRadians);

    // Draw all lines, clockwise.
    // llc -> ulc
    drawThickLine(renderer, points[0].x, points[0].y, points[1].x, points[1].y, thickness);
    // ulc -> urc (adjusted for thickness!)
    drawThickLine(renderer, adjustedPoints[1].x, adjustedPoints[1].y, adjustedPoints[2].x, adjustedPoints[2].y, thickness);
    // urc -> lrc
    drawThickLine(renderer, points[2].x, points[2].y, points[3].x, points[3].y, thickness);
    // lrc -> llc (adjusted for thickness!)
    drawThickLine(renderer, adjustedPoints[3].x, adjustedPoints[3].y, adjustedPoints[0].x, adjustedPoints[0].y, thickness);
}

void drawCircleOutline(SDL_Renderer *renderer, double centerX, double centerY, double radius, double thickness) {
    double radiusSquared = radius * radius;
    double innerRadiusSquared = (radius - thickness) * (radius - thickness);

    long long radiusInt = (long long) round(radius);

    for (long long y = -radiusInt; y <= radiusInt; y++) {
        for (long long x = -radiusInt; x <= radiusInt; x++) {
            double distanceSquared = (double)(x * x + y * y);

            if (distanceSquared <= radiusSquared && distanceSquared >= innerRadiusSquared) {
                SDL_RenderDrawPointF(renderer, (float)(centerX + (double) x),(float)(centerY + (double) y));
            }
        }
    }
}

void drawPixel(SDL_Renderer *renderer, double x, double y) {
    SDL_RenderDrawPointF(renderer, (float)x, (float)y);
}

bool beginCanvas(SDL_Renderer *renderer, int width, int height, Dpp_Canvas *outCanvas) {
    // Check that the width and height both greater than zero.
    if (width <= 0 || height <= 0) {
        printf("Canvas creation failed! Invalid dimensions: width=%d; height=%d\n", width, height);
        return false;
    }

    // Make sure we don't have a NULL canvas. (would be dumb)
    if (outCanvas == NULL) {
        printf("Canvas creation failed! outCanvas is NULL!\n");
        return false;
    }

    // Create the render texture for our canvas.
    SDL_Texture *texture = SDL_CreateTexture(
        renderer,
        SDL_PIXELFORMAT_RGBA8888,
        SDL_TEXTUREACCESS_TARGET,
        width,
        height
    );

    // Make sure the texture was created correctly
    if (!texture) {
        SDL_Log("Canvas creation failed! Failed to create texture: %s\n", SDL_GetError());
        return false;
    }

    // Configure the canvas with the texture we got (and the dimensions, of course)
    outCanvas->texture = texture;
    outCanvas->width = width;
    outCanvas->height = height;

    // Redirect all drawing functions to the canvas' texture.
    SDL_SetRenderTarget(renderer, texture);

    // Set the draw color to white
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);

    // Clear the screen with pure and innocent whiteness
    SDL_RenderClear(renderer);

    // Back to black color
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);

    // All good!!!
    return true;
}

void runCanvasViewer(SDL_Renderer *renderer, SDL_Window* window, Dpp_Canvas canvas) {
    // Reset the render target (previously set to the canvas texture)
    SDL_SetRenderTarget(renderer, NULL);

    // Convert canvas dimensions to floats for easier calculations.
    float canvasWidthF = (float) canvas.width;
    float canvasHeightF = (float) canvas.height;

    // Get the dimensions of the window to resize the canvas appropriately.
    int windowWidth, windowHeight;
    SDL_GetWindowSize(window, &windowWidth, &windowHeight);

    // Zoom of the canvas, always handled multiplicatively (*= & /=)
    float canvasScale;

    // Calculate the canvas scale necessary to have the canvas not go off the screen
    // (must be zoomed-down enough to see it entirely).
    //
    // Basically, let's try with the "width" component for now:
    // Let displayedWidth = canvasScale*canvasWidth
    // displayedWidth <= windowWidth <==>  canvasScale*canvasWidth <= windowWidth
    //                               <==>  canvasScale <= windowWidth/canvasWidth
    //
    // So, to get the widest possible image without going off the screen, we can take
    //      canvasScale = windowWidth/canvasWidth
    //
    // And, of course, we want the same to apply for the height too. So to have both dimensions happy,
    // we have:
    //     canvasScale = min(windowWidth/canvasWidth, windowHeight/canvasHeight)
    if ((float)windowWidth/canvasWidthF <= (float)windowHeight/canvasHeightF) {
        // Canvas is wider than window.
        canvasScale = (float)windowWidth/canvasWidthF;
    } else {
        // Canvas is taller than window.
        canvasScale = (float)windowHeight/canvasHeightF;
    }

    // Current camera offset for the canvas, will be computed to fit the image right now!
    float canvasOffsetX;
    float canvasOffsetY;

    // Now that we found the right zoom for our canvas to fit the window, we need
    // to center it. It's not really hard. Remind yourself that (X, Y) = (0, 0) in the top-left corner,
    // so we need to have:
    //          x + canvasWidth/2 = windowCenterX
    //     <==> x + canvasWidth/2 = windowWidth/2
    //     <==> x = windowWidth/2 - canvasWidth/2
    //     <==> x = (windowWidth - canvasWidth)/2
    //
    // Same thing for height, you get the idea...
    //
    // Now you might have noticed that canvas width/height is not correct because we have scaled it.
    // and that could be true! But we already adjust the camera translation to center the canvas when it's
    // zoomed/dezoomed. So this works properly.
    canvasOffsetX = ((float) windowWidth - canvasWidthF)/2;
    canvasOffsetY = ((float) windowHeight - canvasHeightF)/2;

    // Panning/zooming speed with keyboard/mouse
    const float kbPanSpeed = 200; // pixels/s moved while holding keys
    const float mouseZoomMult = 1.05f; // -> x% bigger or smaller per wheel scroll

    // Last rendered frame time (in system units)
    uint64_t ticks = SDL_GetPerformanceCounter();

    // Last frame mouse coordinates for panning
    int lastMouseX = 0;
    int lastMouseY = 0;

    // Whether the mouse is currently panning the canvas (mouse button pressed)
    bool mousePanning = false;

    // Begin the main SDL loop. Once the user quits the app, "running" becomes false.
    bool running = true;
    SDL_Event event;
    while (running) {
        // Update the frame time.
        const uint64_t prevTicks = ticks;
        ticks = SDL_GetPerformanceCounter();

        // Compute the delta time (in seconds) between this frame and the previous.
        const float deltaTime = (float) (ticks - prevTicks) / (float) SDL_GetPerformanceFrequency();

        // Poll for any interesting events that might come up
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                // Bye!
                // (We're still going to present one frame for nothing but that's no big deal)
                running = false;
            } else if (event.type == SDL_MOUSEWHEEL) {
                // Zoom in and out based on the number of wheel ticks
                int amount = event.wheel.y;
                if (amount > 0) {
                    // Zoom in -> multiply n times
                    for (int i = 0; i < amount; i++) canvasScale *= mouseZoomMult;
                } else {
                    // Zoom out -> divide n times
                    for (int i = 0; i < -amount; i++) canvasScale /= mouseZoomMult;
                }
            } else if (event.type == SDL_MOUSEBUTTONDOWN || event.type == SDL_MOUSEBUTTONUP) {
                // Pan (or stop panning) the canvas when the mouse button is down (or up).
                if (event.button.button == SDL_BUTTON_LEFT) {
                    // SDL_MOUSEBUTTONDOWN => panning on
                    // SDL_MOUSEBUTTONUP => panning off
                    mousePanning = event.type == SDL_MOUSEBUTTONDOWN;
                }
            }
        }

        // Update the mouse coordinates for this frame.
        const int prevMouseX = lastMouseX;
        const int prevMouseY = lastMouseY;
        SDL_GetMouseState(&lastMouseX, &lastMouseY);

        // Apply panning if the left mouse button is down, by computing the difference of mouse coordinates between
        // this frame and the previous one.
        if (mousePanning) {
            canvasOffsetX += (float)(lastMouseX - prevMouseX);
            canvasOffsetY += (float)(lastMouseY - prevMouseY);
        }

        // Apply panning if any arrow key is pressed, in the right direction.
        // To do this, we gather the state of all keys on the keyboard (on or off).
        const Uint8* keys = SDL_GetKeyboardState(NULL);
        if (keys[SDL_SCANCODE_LEFT]) {
            canvasOffsetX -= kbPanSpeed * deltaTime;
        }
        if (keys[SDL_SCANCODE_RIGHT]) {
            canvasOffsetX += kbPanSpeed * deltaTime;
        }
        if (keys[SDL_SCANCODE_UP]) {
            canvasOffsetY -= kbPanSpeed * deltaTime;
        }
        if (keys[SDL_SCANCODE_DOWN]) {
            canvasOffsetY += kbPanSpeed * deltaTime;
        }

        // Clear the screen with a black background
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);

        // Draw the canvas texture in respect to the camera position (offset and zoom).
        // Side node: canvas.xy * (canvasScale-1)/2 is the displacement necessary to have the
        //            canvas centered while zooming, since SDL uses a (X+, Y-) coordinate system.
        SDL_FRect outputRect = {
            .x = canvasOffsetX - canvasWidthF * (canvasScale-1)/2,
            .y = canvasOffsetY - canvasHeightF * (canvasScale-1)/2,
            .w = canvasWidthF * canvasScale,
            .h = canvasHeightF * canvasScale
        };
        SDL_RenderCopyF(renderer, canvas.texture, NULL, &outputRect);

        // Finally, present our masterpiece to the screen.
        SDL_RenderPresent(renderer);
    }

    // The user has quit the app. Destroy everything and quit SDL.
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
}