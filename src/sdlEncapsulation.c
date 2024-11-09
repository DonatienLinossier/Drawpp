//
// Created by donat on 03/10/2024.
//

#include "sdlEncapsulation.h"


int initSDL(SDL_Window **window, SDL_Renderer **renderer) {
    if (SDL_Init(SDL_INIT_VIDEO) < 0) {
        printf("SDL could not initialize! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

    *window = SDL_CreateWindow("SDL Line Drawing", SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED, 1000, 800, SDL_WINDOW_SHOWN);
    if (*window == NULL) {
        printf("Window could not be created! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

    *renderer = SDL_CreateRenderer(*window, -1, SDL_RENDERER_ACCELERATED);
    if (*renderer == NULL) {
        printf("Renderer could not be created! SDL_Error: %s\n", SDL_GetError());
        return -1;
    }

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