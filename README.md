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

## How to compile 

python3 file.c (filename.asm : optional)

nasm -f elf64 filename.asm

gcc -no-pie filename.o

## Contribution

We both worked together on each part: arrays and big numbers.

## Description

This project provides a compiler for a subset of C which supports one type: int and one structure: array.

We found the implementation of big numbers very difficult, particularly their interactions with arrays. We believe it is preferable to retain the type, and that is what we tried to do in the end, but we did not have the time to finish it. The functions for allocation, addition, and comparison are coded in assembly language in the file compil_with_big_numbers.py.

## Arrays
Arrays are declared with the instruction "var tX[size]", array variables can only start with a t, so int variables can't start with a t.
An array is defined by a pointer to its values and its size (easy access for len(tX)), in the .bss section of the generated .asm file. Once it is declared, the pointer is allocated by a call to malloc. Usual operations are avalaible: access and assignment of the value at index i (tX[i]).

## Big numbers

Big numbers are arrays of digits written in certain base, so we based our implementation off of our arrays. A big number would have been represented by the pointer to its digits. We originally intended to implement big numbers that would completely with digits in base 2^60 which would have replaced int numbers. Three bytes of metadata at the beginning were defined: the real capacity of the array containing the whole number, including the metadata, the size the array containing the actual number, and its sign. We tried to implement the allocation of such a number and and add function for big numbers. Addition and substraction of such numbers are easy, an iteration over the digits is needed while reporting an eventual borrow or carry to the next digit. We tried to cover all cases depending on the sign of the numbers.

We realized multiplication would be impossible with our implementation as overflows would occur by multiplying two big number digits. As per our e-mails, we also realized it was impossible to completely replace int numbers with our big numbers, for example to define the size of our arrays. 

## What can be improved

As we tried to implement big numbers, we had time to think of some improvements for our compiler.

### Fixing our big numbers

Fixing big numbers would require two types of integer, and multiplication would involve like in Python, Fourier transform techniques.

### Pointers
Since we have arrays, a pointer is nothing more than an array of length 1.

### Functions
For each function, define an array: function_name_pointer in assembly. Each time we call the function, we store the result in the array and return the result in rax.

We will try to improve our compiler during the next few weeks.
