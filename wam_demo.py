#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
from wam import *
from menu import *
import sys, argparse
from datetime import datetime

# game presentation parameters
S_MENU, S_PAUSED, S_WARM_UP, S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5 = (-2, -1, 0, 1, 2, 3, 4, 5)
M_WARM_UP, M_START_GAME, M_EXIT = (0, 1, 2)
SCREEN_SIZE = (1000, 734)
Fullscreen = False
GAME_STATE = None
HOLE_POSITIONS = [(320,450), (300, 600), (700, 500), (680, 650)]
HOLE_DIST = None
SCORE = 0
DIST_SEQ = [1, 2, 3, 2, 3, 1]
BUNDLE_LENGTH_SEQ = [4, 4, 4, 4, 4, 4]
ALL_MOLE_DISTS = [[0.1, 0.1, 0.2, 0.6],
                  [0.2, 0.6, 0.1, 0.1],
                  [0.6, 0.2, 0.1, 0.1]]
ALL_ANIMAL_DISTS = [[0.25, 0.25, 0.25, 0.25]]

WARMUP_TRIAL_NO, REAL_TRIAL_NO = 20, 200

# world parameters
ALPHA = 1
CORRELATED = True

def init_world():
    """Set up the world (i.e. background), the tree, and the holes.
    All static objects.
    """
    # set up the world (including set initial hole dist)
    world = World(dist_seq = DIST_SEQ,
                  bundle_length_seq = BUNDLE_LENGTH_SEQ,
                  all_most_dists = ALL_MOLE_DISTS,
                  all_animal_dists = ALL_ANIMAL_DISTS,
                  correlated = False)
    
    # simulate and add the tree
    world.add_tree()

    # add a score bar
    world.add_scorebar()
    
    # add the holes
    world.hole_positions = HOLE_POSITIONS
    for hole_id in xrange(len(HOLE_POSITIONS)):
        hole = Hole(world, hole_id)
        world.add_entity(hole)
        
        # hole covers are set up to prevent distractors from being
        # positioned above holes
        hole_cover = GameEntity(world, 'hole_cover', pygame.Surface(hole.image.get_size(), SRCALPHA, 32))
        x, y, w, h = hole.rect
        hole_cover.rect = Rect(x, y - h, w, h)
        world.add_entity(hole_cover)

    return world
    
def rearrange_distractors(world):
    """Randomly rearrange the positions of distractors on the screen.
    """    
    for entity in world.entities:
        if entity.type == 'animal':
            entity.auto_location()

def start_game(screen, trial_total):
    """Start the game. 
    """
    global P_FAMILIAR, P_HOLE_DIST, P_DIST_HISTORY, P_CONTEXTS, SCORE

    # set up world
    world = init_world()

    # show a "GET Ready"
    message = "Get Ready!"
    countdown = 3
    screen.fill((255,255,255))
    font = pygame.font.Font("data/fof.ttf", 80);
    text_surface = font.render(message, True, (0, 0, 0))
    for i in xrange(3):
        screen.fill((245,245,245))
        screen.blit(text_surface, (350,280))
        countdown_surface = font.render(str(countdown-i), True, (0,0,0))
        screen.blit(countdown_surface, (500,430))
        pygame.display.update()
        pygame.mixer.Sound('sounds/ticking.wav').play()
        pygame.time.wait(1000)

    pygame.mouse.set_visible(True)
    pygame.mixer.music.play()

    # set up clock
    clock = pygame.time.Clock()

    # restrict the activity of the mole
    move_count = 0

    # current run
    current_run = 0
    current_max_run = 25
    
    # take care of mode differences
    # If mode is set to WARM_UP, use a uniform
    # distribution for mole position. 
    if GAME_STATE == S_WARM_UP:
        world.hole_dist = (0.25, 0.25, 0.25, 0.25)
        current_max_run = 20

    trial_no = 0
    # start the trials
    while True:
        trial_no += 1
        current_run += 1

        while True:
           
            for event in pygame.event.get():
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        return
                    if event.key == K_s:
                        if pygame.mixer.music.get_busy():
                            pygame.mixer.music.fadeout(2000)
                        else:
                            pygame.mixer.music.play()
                if event.type == MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    world.mole.get_whacked(mouse_x, mouse_y)

            time_passed = clock.tick(60)

            if world.mole.moveable():
                rearrange_distractors(world)
                world.mole.move_weighted(verbose = False)
        
            world.mole.show(time_passed)
            world.mole.wait(time_passed)
            world.mole.hide(time_passed)

            if world.mole.moved > move_count:
                move_count += 1
                break

            world.render(screen)
            world.mole.show_hammered_image(screen)

            pygame.display.update()

        # make a record of this trial
        if GAME_STATE in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5): 
            world.record(rt = world.mole.get_alive_time(),
                         trial_no = trial_no, 
                         run_length = current_max_run)

        print 'trial: ', trial_no , world.mole.get_alive_time()

        if current_run >= current_max_run:
            print trial_no, trial_total
            if trial_no >= trial_total: break
            current_max_run = 25
            current_run = 0
            world.set_hole_dist()

            
    if GAME_STATE in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5):
        world.print_history(open(str(datetime.now()) + '.txt', 'w'))
        P_FAMILIAR, P_HOLE_DIST, P_DIST_HISTORY, P_CONTEXTS = (world.is_familiar_hole_dist,
                                                               world.hole_dist,
                                                               world.hole_dist_history,
                                                               world.context_choices)
    SCORE = world.score

def pause_game(screen):

    if GAME_STATE in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4):
        score_msg = "Good job! Your score is %s" % (SCORE)
        break_msg = "Take a break. A new wave of moles are coming in 2 minutes!"
        continue_msg = "Touch anywhere to continue"
        font = pygame.font.Font("data/intuitive.ttf", 30);
        score_surface = font.render(score_msg, True, (0, 0, 0))
        break_surface = font.render(break_msg, True, (0, 0, 0))        
        continue_surface = font.render(continue_msg, True, (255, 0, 0))
        screen.fill((245,245,245))

        clock = pygame.time.Clock()
        clock.tick(10)
        timer = 0
        screen.blit(score_surface, (340,240))
        screen.blit(break_surface, (140,320))

        pygame.mixer.music.stop()
        pygame.mouse.set_visible(True)

        while timer < 1000 * 60 * 2:
            pygame.display.update()
            timer += clock.tick(5)
            
        screen.blit(continue_surface, (350,420))
        pygame.display.update()
        pygame.event.clear()
        while True:
            event = pygame.event.wait()
            if event.type == MOUSEBUTTONUP: return
    else:
        message = "Game Over. You did an excellent job!"
        font = pygame.font.Font("data/intuitive.ttf", 36);
        text_surface = font.render(message, True, (255, 0, 0))
        screen.fill((245,245,245))
        screen.blit(text_surface, (200,280))
        pygame.display.update()
        pygame.time.wait(1000 * 3)
        return

def run():

    global GAME_STATE, Fullscreen
    pygame.init()

    # set up screen 
    w, h = SCREEN_SIZE
    screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)

    # set up menu
    menu = Menu()
    menu.set_fontsize(44)
    menu.init(['Warm up', 'Start Game', 'Exit'], screen)
    
    # set the initial state of the game "S_MENU"
    GAME_STATE = S_MENU
    
    while True:

        if GAME_STATE == S_MENU:
            screen.fill((51,51,51))
            menu.draw()
            pygame.mixer.music.stop()

            # Get the next event                                                                                
            e = pygame.event.wait()
      
            if e.type == KEYDOWN:
                if e.key == K_f:
                    Fullscreen = not Fullscreen
                    if Fullscreen:
                        screen = pygame.display.set_mode(SCREEN_SIZE, FULLSCREEN, 32)
                    else:
                        screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)
                elif e.key == K_UP:
                    menu.draw(-1)
                elif e.key == K_DOWN:
                    menu.draw(1)
                elif e.key == K_RETURN:
                    choice = menu.get_position()
                    if choice == M_START_GAME:
                        for block in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5):
                            GAME_STATE = block
                            start_game(screen, trial_total=REAL_TRIAL_NO)
                            pause_game(screen)
                        GAME_STATE = S_MENU
                    elif choice == M_WARM_UP:
                        GAME_STATE = S_WARM_UP
                        start_game(screen, trial_total=WARMUP_TRIAL_NO)
                        GAME_STATE = S_MENU
                    elif choice == M_EXIT:
                        return

        if e.type == QUIT:
            return

        pygame.display.update()

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the Whack-The-Mole experiment.')
    parser.add_argument('--correlated_cue', required=True, choices=['yes', 'no'], 
                        help='specify whether the background animals are correlated with contexts')
    parser.add_argument('--alpha', type=int, default=1, help='larger alpha value creates more novel contexts')
    args = parser.parse_args()

    # set the correct variables
    if args.correlated_cue == 'yes': 
        CORRELATED = True
    else:
        CORRELATED = False
    
    ALPHA = args.alpha

    run()
