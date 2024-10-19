#include <SDL2/SDL.h>
#include <stdio.h>

#include "cursor.h"
#include "sdlEncapsulation.h"


int main(int argc, char* args[]) {

    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;

    // Initialize SDL
    if (initSDL(&window, &renderer) != 0) {
        return -1;
    }



    Color myColor = {100, 0, 0, 1};

    Cursor c1 = createCursor(100, 100, 0, 1, 10, myColor);
    cursorJump(&c1, 100, 100, renderer);

    drawCircle(renderer, 150, 150, 50);
    drawCircleFill(renderer, 150, 650, 150);
    drawRect(renderer, 200, 200, 50, 140);
    drawRectFill(renderer, 400, 200, 50, 140);

    SDL_RenderPresent(renderer);
    SDL_Delay(3000); // Keep window open for 3 seconds

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();

    return 0;
}