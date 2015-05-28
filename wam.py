#!/usr/bin/env python
#-*- coding: utf-8 -*-

import pygame, sys
from pygame.locals import *
import numpy as np
import random, copy
from datetime import datetime

def weighted_sample(choices):
    total = sum(choices.itervalues())
    r = np.random.uniform(0, total)
    upto = 0
    for c, w in choices.iteritems():
        if upto + w > r: return c
        upto += w
    assert False, "Shouldn't get here"

class World(object):

    def __init__(self, alpha = 1, block = 1, correlated = True, previous_familiar=None,
                 previous_contexts=None, previous_hole_dist=None, previous_dist_history=None):
        '''Constructor for World'''

        self.entities = pygame.sprite.LayeredUpdates()
        self.distractors = pygame.sprite.LayeredUpdates()
        self.background = pygame.image.load('images/background-hi.png').convert()
        self.distractors_dist = {'cat': 0, 'rabbit': 0, 'snail': 0, 'hipo': 0, 'dinasor': 0}
        self.hole_positions = None
        self.hole_count = 4
        self.block = block
        self.score = 0
        self.mole = None
        self.correlated = correlated

        self.run_history = []
        if block == 1:
            self.context_choices = {'novel': alpha}
            self.hole_dist = None
            self.hole_dist_history = {}
            self.is_familiar_hole_dist = False
        elif block > 1:
            if previous_contexts is None: raise NameError('running as a subsequent block but no previous contexts found!')
            self.context_choices = previous_contexts
            self.hole_dist = previous_hole_dist
            self.hole_dist_history = previous_dist_history
            self.is_familiar_hole_dist = previous_familiar

        if not self.correlated:
            if block == 1:
                self.static_distractor_dist = self.generate_distractor_dist().copy()
            else:
                self.static_distractor_dist = self.hole_dist_history.values()[0]['distractors_dist'].copy()

        self.set_hole_dist()
        self.set_mole()
        pygame.mixer.music.load("sounds/background.mp3")

    def set_hole_dist(self):
        """Generate a random new distribution for the appearance
        probability of the mole.
        """
        available_choices = copy.deepcopy(self.context_choices)
        if self.hole_dist is not None: del available_choices[str(self.hole_dist)]
        new_context = weighted_sample(available_choices)
        
        if new_context != 'novel':
            self.is_familiar_hole_dist = True
            self.context_choices[new_context] += 1

            self.hole_dist = copy.deepcopy(self.hole_dist_history[new_context]['hole_dist'])
            self.distractors_dist = self.hole_dist_history[new_context]['distractors_dist'].copy()
            self.set_distractors()
        else:
            self.hole_dist = np.round(np.random.dirichlet((1,1,1,1)), 2)
            if self.correlated:
                new_distractor_dist = self.generate_distractor_dist()
            
                while self.duplicate_distractor_dist(new_distractor_dist):
                    #print 'duplicate detected', new_distractor_dist
                    new_distractor_dist = self.generate_distractor_dist()
                    #print 'Is the new visual context still a duplicate?', self.duplicate_distractor_dist(new_distractor_dist)
                           
                self.distractors_dist = new_distractor_dist.copy()
                self.set_distractors()
            else:
                self.distractors_dist = self.static_distractor_dist.copy()
                self.set_distractors()

            self.is_familiar_hole_dist = False
            self.context_choices[str(self.hole_dist)] = 1
            self.hole_dist_history[str(self.hole_dist)] = {'hole_dist': copy.deepcopy(self.hole_dist),
                                                           'distractors_dist': {'cat': 0,
                                                                                'rabbit': copy.deepcopy(self.distractors_dist['rabbit']),
                                                                                'snail': copy.deepcopy(self.distractors_dist['snail']),
                                                                                'hipo': copy.deepcopy(self.distractors_dist['hipo']),
                                                                                'dinasor': copy.deepcopy(self.distractors_dist['dinasor'])}}
        return

    def generate_distractor_dist(self):
        
        distractors_dist = {'cat':0}
        iter = 0
        total = 8
        for animal in self.distractors_dist.iterkeys():
            iter += 1
            if animal == 'cat': continue
            if iter == 4: 
                distractors_dist[animal] = total
                continue
            if total == 0:
                distractors_dist[animal] = 0
            
            count =  np.random.randint(0,5)
            while count > total:
                count = np.random.randint(0,5)
            distractors_dist[animal] = count
            total -= count
        return distractors_dist

    def duplicate_distractor_dist(self, dist):

        current_history = copy.deepcopy(self.hole_dist_history)
        for v in current_history.values():
            hist_d_dist = copy.deepcopy(v['distractors_dist'])
            if dist['cat'] == 0 and \
                    dist['rabbit'] == hist_d_dist['rabbit'] and \
                    dist['hipo'] == hist_d_dist['hipo'] and \
                    dist['snail'] == hist_d_dist['snail'] and \
                    dist['dinasor'] == hist_d_dist['dinasor']:
                return True
        return False

    def set_mole(self):
        """Add the mole to the world.
        """
        mole = Mole(self)
        mole.scale_image(.15)
        self.add_entity(mole)
        
    def set_distractors(self):
        """Add distractors to the world.
        """
        # add distractors
        distractor_classes = {'cat': Cat, 'dinasor': Dinasor,
                              'hipo': Hipo, 'rabbit': Rabbit,
                              'snail': Snail}


        # empty existing distractors
        self.entities.remove(self.distractors.sprites())
        self.distractors.empty()

        # add new distractors
        for distractor, count in self.distractors_dist.iteritems():
            for i in xrange(count):
                d = distractor_classes[distractor](self)
                d.scale_image(.115)
                self.add_entity(d)

    def record(self, rt, trial_no, run_length):
        
        self.run_history.append({
                'block': self.block,
                'trial': trial_no,
                'rt': rt,
                'familiar': self.is_familiar_hole_dist,
                'at_hole': self.mole.current_hole_id,
                'hole_dist': self.hole_dist,
                'distractors_dist': copy.deepcopy(self.distractors_dist),
                'score': self.score,
                'run_length': run_length,
                'whack_coordinates': self.mole.rel_whack_coordinates})
        
    def print_history(self, file_pointer = None):
        
        # string formatting
        keys = ['block', 'trial', 'rt', 'familiar', 'pos', 'p0', 'p1', 'p2', 'p3',
                'n.cat', 'n.hipo', 'n.rabbit', 'n.snail', 'n.dinasor', 'score', 'run.length', 'whack.x', 'whack.y']
        output = '{0},{1},{2},{3},{4},{5[0]},{5[1]},{5[2]},{5[3]},{6[cat]},{6[hipo]},{6[rabbit]},{6[snail]},{6[dinasor]},{7},{8},{9[0]},{9[1]}'

        # output header
        header = ','.join(keys)
        if file_pointer is None: print header
        else: file_pointer.write(header + '\n')

        # output each line
        for h in self.run_history:
            formatted_output = output.format(h['block'], h['trial'], h['rt'], h['familiar'], 
                                             h['at_hole'], h['hole_dist'], h['distractors_dist'], 
                                             h['score'], h['run_length'],h['whack_coordinates'])
            if file_pointer: file_pointer.write(formatted_output + '\n')
            else: print formatted_output
    
    def add_entity(self, entity):
        
        if entity.type == 'mole': self.mole = entity
        if entity.type == 'distractor': self.distractors.add(entity)
        self.entities.add(entity)

    def render(self, surface):
        '''Render the world on a given surface'''
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
        self.begin_datetime = None
        self.end_datetime = None

    def move_to_hole(self, hole_id, verbose = False):
        if self.visible: return
        self.rect[0] = self.world.hole_positions[hole_id][0] + 50
        self.rect[1] = self.world.hole_positions[hole_id][1] + 25
        self.current_hole_id = hole_id
        self.whacked = False
        self.begin_datetime = datetime.now()
        if verbose: print 'mole moved to hole', self.current_hole_id
        return

    def move_weighted(self, verbose = False):
        """Move the mole to a hole according the appearance probabilities.
        """
        # numpy shortcut: 4 is equivalent to np.arange(4)
        choices = dict(zip(xrange(4), self.world.hole_dist))
        hole_id = weighted_sample(choices)
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
            self.moved += 1
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
            self.end_datetime = datetime.now()

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
                td = self.end_datetime - self.begin_datetime
                alive_time = round(td.seconds * 1000.0 + td.microseconds / 1000.0)
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
    
class Distractor(GameEntity):
    
    def __init__(self, world, name, image):
        GameEntity.__init__(self, world, name, image)
        self.type = 'distractor'

    def auto_location(self):
        """Move the distractor to a random new position in the world.
        """
        c = True
        while c:
            w, h = self.image.get_size()
            min_x, min_y, max_x, max_y = (0, 400, 1000-w-10, 734-h-10)
            x, y = (np.random.randint(min_x, max_x+1), np.random.randint(min_y,max_y+1))
        
            self.rect = Rect(x, y, w, h)
            c = pygame.sprite.spritecollide(self, self.world.entities, False)
            c.remove(self)

class Cat(Distractor):
    
    def __init__(self, world):
        cat_image = pygame.image.load('images/cat.png').convert_alpha()
        Distractor.__init__(self, world, 'cat', cat_image)

class Dinasor(Distractor):
    
    def __init__(self, world):
        dinasor_image = pygame.image.load('images/dinasor.png').convert_alpha()
        Distractor.__init__(self, world, 'dinasor', dinasor_image)
        
class Hipo(Distractor):
    
    def __init__(self, world):
        hipo_image = pygame.image.load('images/hipo.png').convert_alpha()
        Distractor.__init__(self, world, 'hipo', hipo_image)

class Rabbit(Distractor):
    
    def __init__(self, world):
        rabbit_image = pygame.image.load('images/rabbit.png').convert_alpha()
        Distractor.__init__(self, world, 'rabbit', rabbit_image)

class Snail(Distractor):

    def __init__(self, world):
        snail_image = pygame.image.load('images/snail.png').convert_alpha()
        Distractor.__init__(self, world, 'snail', snail_image)

class ScoreBar(GameEntity):

    def __init__(self, world):
        
        self.color = (0,0,0)#(254,254,151)
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

