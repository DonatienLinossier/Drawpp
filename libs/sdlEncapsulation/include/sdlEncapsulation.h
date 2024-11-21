//
// Created by donat on 03/10/2024.
//

#ifndef SDLENCAPSULATION_H
#define SDLENCAPSULATION_H

#include <SDL2/SDL.h>

int initSDL(SDL_Window **window, SDL_Renderer **renderer);

void drawCircle(SDL_Renderer* renderer, int centerX, int centerY, int radius);

void drawCircleFill(SDL_Renderer* renderer, int centerX, int centerY, int radius);



void drawRect(SDL_Renderer* renderer, int x, int y, int width, int height);

void drawRectFill(SDL_Renderer* renderer, int x, int y, int width, int height);



#endif //SDLENCAPSULATION_H
