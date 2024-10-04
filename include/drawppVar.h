//
// Created by donat on 03/10/2024.
//

#ifndef DRAWPPVAR_H
#define DRAWPPVAR_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    char* name;
    double value;
} DoubleVar;

typedef struct {
    char* name;
    int value;
} IntVar;


typedef struct {
    IntVar* intTab;
    int intTab_size;
    DoubleVar* doubleTab;
    int doubleTab_size;
} VariableHandler;

//
// Created by donat on 03/10/2024.
//

//Todo: sanitize data before using strings ! (What if the  use \0 ? or if the string doesn't end ?)

#include "drawppVar.h"


VariableHandler vh_create();

void vh_createInt(VariableHandler* varhdler, const char* name, const int value);

int vh_getInt(VariableHandler* vh, const char* name);

void vh_addToInt(VariableHandler* vh, const char* name, int value);



void vh_createDouble(VariableHandler* varhdler, const char* name, const double value);

int vh_getDouble(VariableHandler* vh, const char* name);

void vh_addToDouble(VariableHandler* vh, const char* name, double value);




void vh_debug_getAllVar(const VariableHandler* vh);


#endif //DRAWPPVAR_H
