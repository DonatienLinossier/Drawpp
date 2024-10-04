#Donatien
#Note : The class will have to keep record of the type of each variable
#TODO: There will be a trouble with the varTypeDict. Several variables can have the same name if there are in differents contexts.
#from translater import translater
header = """ 
#include <SDL2/SDL.h>
#include <stdio.h>

#include "cursor.h"
#include "sdlEncapsulation.h"
#include "drawppVar.h"
                    
int main(int argc, char* args[]) {
                    
    SDL_Window *window = NULL;
    SDL_Renderer *renderer = NULL;
                    
    if (initSDL(&window, &renderer) != 0) 
    {
    return -1;
    }
                    
    VariableHandler vh = vh_create();\n"""

footer = """ 
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
                    
    return 0;
}"""

#class CTranslater(translater):
class CTranslater:
    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename, "w")
        self.header()
        self.varTypeDict = {}

    def header(self):

        self.file.write(header)

    def addVariable(self, type, name, value):
        match type:
            case "int":
                self.file.write("vh_createInt(&vh, \"" + name + "\", " + str(value) + ");\n")
            case "double":
                self.file.write("vh_createDouble(&vh, \"" + name + "\", " + str(value) + ");\n")

        self.varTypeDict[name] = type

    def addToVariable(self, name, value):
        type = self.varTypeDict[name]
        match type:
            case "int":
                self.file.write("vh_addToInt(&vh, \"" + name + "\", " + str(value) + ");\n")
            case "double":
                self.file.write("vh_addToDouble(&vh, \"" + name + "\", " + str(value) + ");\n")

    def getVariable(self, name):
        type = self.varTypeDict[name]
        match type:
            case "int":
                self.file.write("vh_getInt(&vh, \"" + name + "\");\n")
            case "double":
                self.file.write("vh_addToDouble(&vh, \"" + name + "\");\n")

    def __del__(self):

        self.file.write(footer)
        self.file.close()


if __name__ == '__main__':
    test = CTranslater("output/test.c")
    test.addVariable("int", "test", 5)
    test.addToVariable("test", 5)
