#include <stdio.h>
#include <stdlib.h>

void* x = malloc(30);

void greet(char* name)
{
    printf("Hello, %s\n", name);
}

int main(int argc, char** argv)
{
    int x = 3;

    if(argc == 1) {
        printf("Hello, world!\n");
    }

    for(int i = 1; i < argc; i++)
    {
        greet(argv[i]);
    }

    return 0;
}