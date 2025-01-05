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
    
    //Start of the generated code
    
    // Set the draw color to white
    SDL_SetRenderDrawColor(renderer, 255, 255, 255, 255);
    
    // Clear the screen with pure and innocent whiteness
    SDL_RenderClear(renderer);
    
    // Put the draw color back to black
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    """

footer = """ 
    //End of the generated code

    SDL_RenderPresent(renderer);
    
    // Wait until the user closes the window to exit the application.
    int running = 1;
    SDL_Event event;
    while (running) {
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = 0;
            }
        }
    }
    
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
                    
    return returnStatement;
}"""