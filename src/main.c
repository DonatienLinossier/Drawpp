#include <SDL2/SDL.h>
#include <stdio.h>

#include "cursor.h"
#include "sdlEncapsulation.h"
#include "drawppVar.h"


int main(int argc, char* args[]) {

    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;

    // Initialize SDL
    if (initSDL(&window, &renderer) != 0) {
        return -1;
    }

    VariableHandler vh = vh_create();

    char* test_int = "testInt";
    vh_createInt(&vh, test_int, 5);
    printf("%d", vh_getInt(&vh, test_int));

    char* test_int2 = "testInt2";
    vh_createInt(&vh, test_int2, 50);
    printf("%d", vh_getInt(&vh, test_int));

    char* test_int3 = "testInt3";
    vh_createInt(&vh, test_int3, 100);
    printf("%d", vh_getInt(&vh, test_int));

    char* test_double = "testDouble";
    vh_createDouble(&vh, test_double, 5.2);
    printf("%d", vh_getInt(&vh, test_double));

    char* test_double2 = "testDouble2";
    vh_createDouble(&vh, test_double2, 15.5);
    printf("%d", vh_getInt(&vh, test_double));

    char* test_double3 = "testDouble3";
    vh_createDouble(&vh, test_double3, 10.5);
    printf("%d", vh_getInt(&vh, test_double));

    vh_addToInt(&vh, test_int2, 5);

    vh_addToInt(&vh, test_double2, 6.2);

    vh_addToInt(&vh, test_int3, -10);

    vh_addToInt(&vh, test_double3, -9.2);

    vh_debug_getAllVar(&vh);




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