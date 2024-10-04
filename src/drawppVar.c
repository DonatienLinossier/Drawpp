//
// Created by donat on 03/10/2024.
//

//Todo: sanitize data before using strings ! (What if the  use \0 ? or if the string doesn't end ?)

#include "../include/drawppVar.h"

//TODO: Maybe look for a mapper for the variables. (that will link the name of the variable to its type)
//TODO: Block the creation of a var with the same name of an existing one.
//TODO: Change the value of a var;
VariableHandler vh_create() {
    VariableHandler varhdler;
    varhdler.intTab = NULL;
    varhdler.intTab_size = 0;
    varhdler.doubleTab = NULL;
    varhdler.doubleTab_size = 0;
    return varhdler;
}

void vh_createInt(VariableHandler* varhdler, const char* name, const int value) {
    if (varhdler == NULL) {
        printf("Error: VariableHandler is Null\n");
        return;
    }
    if (name == NULL) {
        printf("Error: Name of the variable is Null\n");
        return;
    }


    IntVar* tmp_ptr = realloc(varhdler->intTab, (varhdler->intTab_size + 1) * sizeof(IntVar));
    if (tmp_ptr == NULL) {
        printf("Error: Memory allocation failed\n");
        return;
    }
    varhdler->intTab = tmp_ptr;


    IntVar newInt;
    newInt.name = strdup(name);
    if (newInt.name == NULL) {
        printf("Error: Memory allocation for string failed\n");
        return;
    }
    newInt.value = value;


    varhdler->intTab[varhdler->intTab_size] = newInt;
    varhdler->intTab_size++;
}

int vh_getInt(VariableHandler* vh, const char* name)
{
    if(vh==NULL) {
        printf("Error: VariableHandler is Null");
        return 0;
        //TODO: handle Error
    }
    if(name==NULL) {
        printf("Error: Name of the variable is Null");
        return 0;
        //TODO: handle Error
    }
    printf("Entering");
    for(int i =0; i<vh->intTab_size; i++)
    {
        printf("%d", i);
        if(!strcmp(name, vh->intTab[i].name))
        {
            return vh->intTab[i].value;
        }
    }

    return 0;
    //Todo: Return not found
}


void vh_addToInt(VariableHandler* vh, const char* name, int value)
{
    if(vh==NULL) {
        printf("Error: VariableHandler is Null");
        return;
        //TODO: handle Error
    }
    if(name==NULL) {
        printf("Error: Name of the variable is Null");
        return;
        //TODO: handle Error
    }

    for(int i =0; i<vh->intTab_size; i++)
    {
        printf("%d", i);
        if(!strcmp(name, vh->intTab[i].name))
        {
            vh->intTab[i].value += value;
        }
    }
}


int vh_getDouble(VariableHandler* vh, const char* name)
{
    if(vh==NULL) {
        printf("Error: VariableHandler is Null");
        return 0;
        //TODO: handle Error
    }
    if(name==NULL) {
        printf("Error: Name of the variable is Null");
        return 0;
        //TODO: handle Error
    }
    for(int i =0; i<vh->doubleTab_size; i++)
    {
        if(strcmp(name, vh->doubleTab[i].name))
        {
            return vh->doubleTab[i].value;
        }
    }

    return 0;
    //Todo: Return not found
}


void vh_createDouble(VariableHandler* varhdler, const char* name, const double value) {
    if (varhdler == NULL) {
        printf("Error: VariableHandler is Null\n");
        return;
    }
    if (name == NULL) {
        printf("Error: Name of the variable is Null\n");
        return;
    }


    DoubleVar* tmp_ptr = realloc(varhdler->doubleTab, (varhdler->doubleTab_size + 1) * sizeof(DoubleVar));
    if (tmp_ptr == NULL) {
        printf("Error: Memory allocation failed\n");
        return;
    }
    varhdler->doubleTab = tmp_ptr;


    DoubleVar newDouble;
    newDouble.name = strdup(name);
    if (newDouble.name == NULL) {
        printf("Error: Memory allocation for string failed\n");
        return;
    }
    newDouble.value = value;


    varhdler->doubleTab[varhdler->doubleTab_size] = newDouble;
    varhdler->doubleTab_size++;
}

void vh_addToDouble(VariableHandler* vh, const char* name, const double value)
{
    if(vh==NULL) {
        printf("Error: VariableHandler is Null");
        return;
        //TODO: handle Error
    }
    if(name==NULL) {
        printf("Error: Name of the variable is Null");
        return;
        //TODO: handle Error
    }

    for(int i =0; i<vh->doubleTab_size; i++)
    {
        printf("%d", i);
        if(!strcmp(name, vh->doubleTab[i].name))
        {
            vh->doubleTab[i].value += value;
        }
    }
}


void vh_debug_getAllVar(const VariableHandler* vh)
{
    printf("\nInt : \n");
    for(int i =0; i<vh->intTab_size; i++)
    {
        printf("    %s : %d\n", vh->intTab[i].name, vh->intTab[i].value);
    }

    printf("\nDouble : \n");

    for(int i =0; i<vh->doubleTab_size; i++)
    {
        printf("    %s : %f\n", vh->doubleTab[i].name, vh->doubleTab[i].value);
    }

}