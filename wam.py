#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
import pygame, sys
from pygame.locals import *
import random, copy
from time import time

def sample(a, p):
    """Step sample from a discrete distribution using CDF
    """
    n = len(a)
    r = random.random()
    total = 0           # range: [0,1]
    for i in xrange(n):
        total += p[i]
        if total > r:
            return a[i]
    return a[i]

class World(object):

    def __init__(self):
        """Constructor for the World.
        """
        self.entities = pygame.sprite.LayeredUpdates()
        self.animals = pygame.sprite.LayeredUpdates()
        self.background = pygame.image.load('images/background-hi.png').convert()
        self.hole_positions = None
        self.score = 0
        self.mole = None
        self.mole_dist = None
        
        pygame.mixer.music.load("sounds/background.mp3")

    def add_mole(self, mole_dist):
        """Add the mole to the world.
        """
        if self.mole is None:
            mole = Mole(world = self)
            mole.scale_image(.15)
            self.add_entity(mole)
        print(self.entities)
        self.mole_dist = mole_dist
        
    def add_animals(self, animal_dist):
        """Add animals to the world.
        """
        # add animals
        animal_classes = {'cat': Cat, 'dinosaur': Dinosaur,
                          'hippo': Hippo, 'rabbit': Rabbit,
                          'snail': Snail}

        # empty existing animals
        self.entities.remove(self.animals.sprites())
        self.animals.empty()

        # add new animals
        for animal, count in animal_dist.iteritems():
            for i in xrange(count):
                d = animal_classes[animal](self)
                d.scale_image(.115)
                self.add_entity(d)

    def add_scorebar(self):
        """Add the score bar to the world.
        """
        sb = ScoreBar(self)
        self.add_entity(sb)
        return

    def add_tree(self):
        """Add the tree.
        """
        tree = GameEntity(self, 'tree', pygame.Surface([271,413], SRCALPHA, 32))
        tree.rect = Rect(87,214,121,413)
        self.add_entity(tree)
        
        return
        
    def add_entity(self, entity):
        
        if entity.type == 'mole': self.mole = entity
        if entity.type == 'animal': self.animals.add(entity)
        self.entities.add(entity)

    def render(self, surface):
        """Render the world on a given surface.
        """
        surface.blit(self.background, (0,0))
        for entity in [e for e in self.entities if e.type != 'mole']:
            entity.render(surface)
        self.mole.render(surface)
        
class GameEntity(pygame.sprite.Sprite):
    
    def __init__(self, world, name, image):
        '''Construtor for GameEntity'''
        pygame.sprite.Sprite.__init__(self)
        
        self.world = world
        self.name = name
        self.image = image
        self.rect = self.image.get_rect()
        self.destination = (0.,0.)
        self.visible = True
        self.speed = 0.
        self.type = 'regular'

    def scale_image(self, percent):
        w, h = self.image.get_size()
        self.image = pygame.transform.smoothscale(self.image, (int(percent * w), int(percent * h)))
        self.rect = self.image.get_rect()
           
    def render(self, surface):
        
        x, y = self.rect[0:2]
        w, h = self.image.get_size()
        surface.blit(self.image, (x, y))

class Hole(GameEntity):
    
    def __init__(self, world, hole_id):

        hole_image = pygame.image.load('images/hole.png').convert_alpha()
        GameEntity.__init__(self, world, 'hole', hole_image)

        self.scale_image(.6)
        self.world.hole_size = self.image.get_size()
        self.hole_id = hole_id
        self.set_position()

    def set_position(self):
        
        self.rect = Rect(self.world.hole_positions[self.hole_id], self.image.get_size())

class Mole(GameEntity):

    def __init__(self, world):
        """Initializing a mole.
        """        
        mole_image = pygame.image.load('images/mole.png').convert_alpha()
        GameEntity.__init__(self, world, 'mole', mole_image)
        self.type = 'mole'
        self.visible = False
        self.upspeed = 240
        self.downspeed = 290
        self.current_hole_id = -1
        self.status = 'STILL'
        self.moved = 0 # the number of times the mole has been moved
        self.locked = False
        self.locked_duration = 0
        self.max_locked_duration = 2000
        self.hit_locked_duration = 200
        self.bang_image = pygame.image.load('images/bang.png').convert_alpha()
        self.bang_image = scale_surface(self.bang_image, 0.5)
        self.bang_sound = pygame.mixer.Sound('sounds/whack.aif')
        self.whacked = False
        self.rel_whack_coordinates = (None, None)
        self.bang_pos = (0,0)
        self.begin_time = None
        self.end_time = None

    def move_to_hole(self, hole_id, verbose = False):
        if self.visible: return
        self.rect[0] = self.world.hole_positions[hole_id][0] + 50
        self.rect[1] = self.world.hole_positions[hole_id][1] + 25
        self.current_hole_id = hole_id
        self.whacked = False
        if verbose: print('mole moved to hole', self.current_hole_id)
        self.begin_time = time()
        return

    def move_weighted(self, verbose = False):
        """Move the mole to a hole according the appearance probabilities.
        """
        hole_id = sample(a = range(4), p = self.world.mole_dist)
        self.move_to_hole(hole_id, verbose)

    def show(self, time_passed):

        if self.current_hole_id == -1: return
        if self.status == 'MOVE_DOWN' or self.locked: return
        self.visible = True

        w, h = self.image.get_size()
        
        if self.rect[1] + h - 28 < self.world.hole_positions[self.current_hole_id][1]:
            self.status = 'STILL'
            self.locked = True
        else:
            self.status = 'MOVE_UP'
            seconds = time_passed / 1000.
            self.rect[1] = self.rect[1] - max(1, self.upspeed * seconds)

    def wait(self, time_passed):
        if self.current_hole_id == -1: return
        if self.locked is False: return
        
        if not self.whacked: max_duration = self.max_locked_duration
        else: max_duration = self.hit_locked_duration

        self.locked_duration += time_passed
        
        if self.locked_duration > max_duration:
            self.locked = False
            self.locked_duration = 0

    def hide(self, time_passed):
        if self.current_hole_id == -1: return
        if self.status == 'MOVE_UP' or self.locked: return
        w, h = self.image.get_size()

        if self.rect[1] - 25 >= self.world.hole_positions[self.current_hole_id][1]:
            self.status = 'STILL'
            self.visible = False
            #self.moved += 1
        else:
            self.status = 'MOVE_DOWN'
            seconds = time_passed / 1000.
            self.rect[1] = self.rect[1] + max(1, self.downspeed * seconds)

    def moveable(self):
        return not self.visible

    def get_whacked(self, mouse_x, mouse_y):
        """Detect if the mole is whacked when the method is called.
        """
        if self.whacked: return
        mole_x, mole_y, mole_w, mole_h = self.rect
        self.whacked = mouse_x > mole_x and mouse_x < mole_x + mole_w and mouse_y > mole_y and mouse_y < mole_y + mole_h
        
        if self.whacked:
            self.locked = self.whacked
            self.status = 'STILL'
            self.end_time = time()

            self.rel_whack_coordinates = (mouse_x - mole_x, mouse_y - mole_y)
            bang_center = (mouse_x, mouse_y)# (mole_x + mole_w / 2, mole_y + mole_h / 2)
            bang_size = self.bang_image.get_size()
            self.bang_pos = (bang_center[0] - bang_size[0] / 2, bang_center[1] - bang_size[1] / 2)

            self.bang_sound.play()
            self.world.score += int(5.0 * 1000.0 / float(self.get_alive_time()))

            return self.whacked

    def show_hammered_image(self, surface):
        if not self.whacked: return
        surface.blit(self.bang_image, self.bang_pos)

    def get_alive_time(self):
        """Return how long the mole was active before getting hammered.
        Return none if player missed.
        """
        if self.whacked: 
            try:
                td = self.end_time - self.begin_time
                alive_time = int(round(td * 1000))
            except:
                alive_time = None
            return alive_time
        else: 
            return

    def render(self, surface):
        if self.visible is False: return
        hole_w, hole_h = self.world.hole_size
        hole_x, hole_y = self.world.hole_positions[self.current_hole_id]
        mole_x, mole_y, mole_w, mole_h = self.rect
        drawable = Rect(0, 0, mole_w, max(hole_y + 25 - mole_y, 0))
        surface.blit(self.image, dest=(mole_x, mole_y), area=drawable)
    
class Animal(GameEntity):
    
    def __init__(self, world, name, image):
        GameEntity.__init__(self, world, name, image)
        self.type = 'animal'

    def auto_location(self):
        """Move the animal to a random new position in the world.
        """
        c = True
        while c:
            w, h = self.image.get_size()
            min_x, min_y, max_x, max_y = (0, 400, 1000-w-10, 734-h-10)
            x, y = (random.randint(min_x, max_x), random.randint(min_y,max_y))
        
            self.rect = Rect(x, y, w, h)
            c = pygame.sprite.spritecollide(self, self.world.entities, False)
            c.remove(self)

class Cat(Animal):
    
    def __init__(self, world):
        cat_image = pygame.image.load('images/cat.png').convert_alpha()
        Animal.__init__(self, world, 'cat', cat_image)

class Dinosaur(Animal):
    
    def __init__(self, world):
        dinosaur_image = pygame.image.load('images/dinosaur.png').convert_alpha()
        Animal.__init__(self, world, 'dinosaur', dinosaur_image)
        
class Hippo(Animal):
    
    def __init__(self, world):
        hippo_image = pygame.image.load('images/hippo.png').convert_alpha()
        Animal.__init__(self, world, 'hippo', hippo_image)

class Rabbit(Animal):
    
    def __init__(self, world):
        rabbit_image = pygame.image.load('images/rabbit.png').convert_alpha()
        Animal.__init__(self, world, 'rabbit', rabbit_image)

class Snail(Animal):

    def __init__(self, world):
        snail_image = pygame.image.load('images/snail.png').convert_alpha()
        Animal.__init__(self, world, 'snail', snail_image)

class ScoreBar(GameEntity):

    def __init__(self, world):
        
        self.color = (0,0,0)
        self.font = pygame.font.Font('data/intuitive.ttf', 32)
        scoreimage = self.font.render('Score: ' + str(world.score), True, self.color)
        GameEntity.__init__(self, world, 'scorebar', scoreimage)
        self.rect = Rect([750,60], self.image.get_size())

    def render(self, surface):

        self.image = self.font.render('Score: ' + str(self.world.score), True, self.color)
        x, y = self.rect[0:2]
        w, h = self.image.get_size()
        surface.blit(self.image, (x, y))

def scale_surface(surface, percent):

    w, h = surface.get_size()
    surface = pygame.transform.smoothscale(surface, 
                                           (int(percent * w), int(percent * h)))
    return surface

