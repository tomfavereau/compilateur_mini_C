# compilateur_mini_C

# Authors
Tom Faverau
Alicia Shao

## What is needed

- A Linux distribution
- nasm
- gcc
- python3
- lark
- How to compile

## How to compile 

python3 file.c (filename.asm : optional)
nasm -f elf64 filename.asm
gcc -no-pie filename.o

## Contribution

We both work together on each part.

## Description

This project provides a compiler for a subset of C which supports one type: int and one structure: array.

We found the implementation of big numbers very difficult, particularly their interactions with arrays. We believe it is preferable to retain the type, and that is what we tried to do in the end, but we did not have the time to finish it. The functions for allocation, addition, and comparison are coded in assembly language in the file compil_with_big_numbers.

## What can be improved

As we tried to implement big numbers, we had time to think of some improvements for our compiler.

### Pointers
Since we have arrays, a pointer is nothing more than an array of length 1.

### Functions
For each function, define an array: function_name_pointer in assembly. Each time we call the function, we store the result in the array and return the result in rax.

We will try to improve our compiler during the next few weeks.
