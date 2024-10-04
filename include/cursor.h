//
// Created by donat on 03/10/2024.
//

#ifndef CURSOR_H
#define CURSOR_H
#include "sdlEncapsulation.h"

typedef struct
{
    unsigned short r;
    unsigned short g;
    unsigned short b;
    unsigned short a;
}Color;

typedef struct {
    int x;
    int y;
    unsigned short a;
    short visible;
    unsigned short thickness;
    Color color;
} Cursor;


Cursor createCursor(int x, int y, unsigned short a, short visible, unsigned short thickness, Color color);
void cursorJump(Cursor* cursor, int x, int y, SDL_Renderer* renderer);

#endif //CURSOR_H
