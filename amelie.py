#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created by Juan Rodríguez Monti - juan.rodriguezmonti@gmail.com based on
the core work developed by SuperBiasedMan, available at 
http://codereview.stackexchange.com/questions/98247/wordsearch-generator
"""

import random
import itertools

from copy import deepcopy
from random import randint

letters = "qwertyuiopasdfghjklzxcvbnm"

def makeGrid(words, size=[10,10], attempts=10):
    '''Run attemptGrid trying attempts number of times.

    Size contains the height and width of the board.
    Word is a list of words it should contain.'''

    for _ in range(attempts):
        try:
            return attemptGrid(words, size)
        except RuntimeError as e:
            pass
    else:
        print "ERROR - Couldn't create valid board"
        raise e

def attemptGrid(words, size):
    '''attempt a grid of letters to be a wordsearch

    Size contains the height and width of the board.
    Word is a list of words it should contain.
    Returns the 2D list grid and a dictionary of the words as keys and 
    lists of their co-ordinates as values.'''

    #Make sure that the board is bigger than even the biggest word
    sizeCap = (size[0] if size[0] >= size[1] else size[1])
    sizeCap -= 1
    if any(len(word) > sizeCap for word in words):
        print "ERROR: Too small a grid for supplied words."
        return

    grid = [[' ' for _ in range(size[0])] for __ in range(size[1])]

    #Insert answers and store their locations
    answers = {}
    for word in words:
        grid, answer = insertWord(word,grid)
        answers[word] = answer

    #add other characters to fill the empty space
    for i,j in itertools.product(range(size[1]),range(size[0])):
        if grid[i][j] == ' ':
            grid[i][j] = letters[randint(0,len(letters)-1)]

    return grid, answers

def insertWord(word, grid, invalid=None):
    '''Insert a word into the letter grid

    'word' will be inserted into the 2D list grid.
    invalid is either None or a list of coordinates
    These coordinates are denote starting points that don't work.
    Returns an updated grid as well as a list of the added word's indices.'''

    height, width = len(grid), len(grid[0])
    length = len(word)

    #Detect whether the word can fit horizontally or vertically.
    hori = width >= length + 1  
    vert = height >= length + 1  
    if hori and vert:
        #If both can be true, flip a coin to decide which it will be
        hori = bool(randint(0,1))
        vert = not hori

    line = [] #For storing the letters' locations
    if invalid is None:
        invalid = [[None,None,True],[None,None,False]]

    #Height * width is an approximation of how many attempts we need
    for _ in range(height*width):
        if hori:
            x = randint(0,width-1-length)
            y = randint(0,height-1)
        else:
            x = randint(0,width-1)
            y = randint(0,height-1-length)
        if [y,x,hori] not in invalid:
            break
    else:
        # Probably painted into a corner, raise an error to retry.
        raise(RuntimeError)

    start = [y, x, hori] #Saved in case of invalid placement
    #Now attempt to insert each letter
    for letter in word:
        if grid[y][x] in (' ', letter):
            line.append([y,x])
            if hori:
                x += 1
            else:
                y += 1
        else:
            #We found a place the word can't fit
            #Mark the starting point as invalid
            invalid.append(start)
            return insertWord(word, grid, invalid)

    #Since it's a valid place, write to the grid and return
    for i,cell in enumerate(line):
        grid[cell[0]][cell[1]] = word[i]
    return grid, line

def printGrid(grid):
    '''Print the grid in a friendly format.'''

    width = len(grid[0])
    print ("+" + ('---+' * width))

    fileword = file("grandma.txt", "w")
    fileword.write("\n"+"= Amelie wordsearch generator ="+"\n")
    fileword.write("The words to search are:"+"\n")

    for word in words:
        activeWord = random.choice(words)
        words.remove(activeWord)    
        fileword.write(activeWord)    
        fileword.write("\n")

    fileword.write("_" + "____" * width)
    fileword.write("\n")

    for i,line in enumerate(grid):
        print ("| " + " | ".join(line) + " |")
        print ("-" + ('----' * width))
        fileword.write("| " + " | ".join(line) + " |")
        fileword.write("\n")
    
    fileword.close()

words = ["ventarron", "regalo", "pasado","guapeza","cafetin","enfermo",
         "dimensional", "dictionary", "lacklustre", "derrota", "iguala",
         "rango", "tango", "pelota", "conquista", "corazones", "ocasion", 
         "aquel", "pasado", "guapeza", "bolita", "fulero", "queres", "cuantas",
         "quiero", "baraja", "treinta", "entraba", "carpeta", "bondades", "caballo",
         "meta", "carrera", "sobon", "buena", "cabe", "mina"]

grid, answers = makeGrid(words, [20,48])
printGrid(grid)
