//
// Created by donat on 03/10/2024.
//

#ifndef SDLENCAPSULATION_H
#define SDLENCAPSULATION_H

#include <SDL2/SDL.h>
#include <stdbool.h>

// Contains all information about a Draw++ canvas: its render texture and dimensions.
typedef struct {
    // The render texture of the canvas, with all drawings redirected to it.
    SDL_Texture* texture;
    int width;
    int height;
} Dpp_Canvas;

int initSDL(SDL_Window **window, SDL_Renderer **renderer);

void drawThickLine(SDL_Renderer *renderer, double x1, double y1, double x2, double y2, double thickness);

void drawRectangleFill(SDL_Renderer *renderer, double x, double y, double width, double height, double angleInRadians);

void drawRectangleOutline(SDL_Renderer* renderer, double x, double y, double width, double height,
    double angleInRadians, double thickness);

void drawCircleFill(SDL_Renderer* renderer, double centerX, double centerY, double radius);

void drawCircleOutline(SDL_Renderer *renderer, double centerX, double centerY, double radius, double thickness);

void drawPixel(SDL_Renderer *renderer, double x, double y);

// Begins drawing on a new canvas with the given dimensions. Outputs the created canvas on outCanvas.
// All SDL drawing functions will draw on the canvas' texture rather than on the default surface, until
// runCanvasViewer is called.
// By default, the canvas is emptied with a white background, and a black draw color.
// Returns false when the canvas creation failed (might happen if the texture is too big), else returns true.
bool beginCanvas(SDL_Renderer* renderer, int width, int height, Dpp_Canvas* outCanvas);

// Starts an interactive viewer for a canvas, with panning and zooming features.
// This function runs forever until the user quits the application.
// It also is responsible for destroying any SDL-related resources once that happens.
void runCanvasViewer(SDL_Renderer* renderer, SDL_Window* window, Dpp_Canvas canvas);


#endif //SDLENCAPSULATION_H
