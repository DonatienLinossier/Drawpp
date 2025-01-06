header = """ 
#include <SDL2/SDL.h>
#include <stdio.h>

#include "sdlEncapsulation.h"


                    
int main(int argc, char* args[]) {
                    
    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;
                    
    if (initSDL(&window, &renderer) != 0) 
    {
    return -1;
    }
    
    int returnStatement = 0;
    Dpp_Canvas drawCanvas; // Will be filled by beginCanvas
    
    // Start of the generated code
    """

footer = """ 
    //End of the generated code

    runCanvasViewer(renderer, window, drawCanvas);
                    
    return returnStatement;
}"""