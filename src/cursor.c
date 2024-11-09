//
// Created by donat on 03/10/2024.
//
#ifndef CURSOR_C
#define CURSOR_C


#include "cursor.h"


// Function to create a Cursor
Cursor createCursor(int x, int y, unsigned short a, short visible, unsigned short thickness, Color color) {
    Cursor cursor;
    cursor.x = x;                // Set the x position
    cursor.y = y;                // Set the y position
    cursor.a = a;                // Set the attribute
    cursor.visible = visible;     // Set the visibility
    cursor.thickness = thickness; // Set the thickness
    cursor.color = color;         // Set the color

    return cursor;               // Return the constructed cursor
}

void cursorJump(Cursor* cursor, int x, int y, SDL_Renderer* renderer) {
    SDL_SetRenderDrawColor(renderer, cursor->color.r, cursor->color.g, cursor->color.b, cursor->color.a);
    int lastPosX = cursor->x;
    int lastPosY = cursor->y;
    cursor->x+=x;
    cursor->y+=y;
    //TODO: check if the cursor is visible before drawing it
    SDL_RenderDrawLine(renderer, lastPosX, lastPosY, cursor->x, cursor->y);
}






#endif