//
// Created by donat on 03/10/2024.
//

#include "sdlEncapsulation.h"
#include <stdio.h>


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

void drawCircle(SDL_Renderer* renderer, int centerX, int centerY, int radius) {
    for (int angle = 0; angle < 360; angle++) {
        // Convert angle to radians
        double radians = angle * (M_PI / 180);
        // Calculate x and y using the circle equation
        int x = centerX + (int)(radius * cos(radians));
        int y = centerY + (int)(radius * sin(radians));
        SDL_RenderDrawPoint(renderer, x, y);
    }
}

void drawCircleFill(SDL_Renderer* renderer, int centerX, int centerY, int radius) {
    for (int i = -radius; i <= radius; i++) {
        for (int j = -radius; j <= radius; j++) {
            if (pow(i, 2) + pow(j, 2) <= radius * radius) {
                SDL_RenderDrawPoint(renderer, centerX + i, centerY + j);
            }
        }
    }
}

void drawRect(SDL_Renderer* renderer, int x, int y, int width, int height) {
    SDL_RenderDrawLine(renderer, x, y, x+width, y);
    SDL_RenderDrawLine(renderer, x+width, y, x+width, y+height);
    SDL_RenderDrawLine(renderer, x+width, y+height, x, y+height);
    SDL_RenderDrawLine(renderer, x, y+height, x, y);
}

void drawRectFill(SDL_Renderer* renderer, int x, int y, int width, int height) {
    for(int i =0; i<width; i++)
    {
        for(int j =0; j<height; j++)
        {
            SDL_RenderDrawPoint(renderer, x+i, y+j);
        }
    }
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
