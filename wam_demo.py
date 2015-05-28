#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
from wam import *
from menu import *
import sys, argparse
from datetime import datetime


class Game(object):
    
    # game presentation parameters
    S_MENU, S_PAUSED, S_WARM_UP, S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5 = (-2, -1, 0, 1, 2, 3, 4, 5)
    M_WARM_UP, M_START_GAME, M_EXIT = (0, 1, 2)
    SCREEN_SIZE = (1000, 734)
    HOLE_POSITIONS = [(320,450), (300, 600), (700, 500), (680, 650)]
    HOLE_DIST = None
    DIST_SEQ = [1, 2, 3, 2, 3, 1]
    BUNDLE_LENGTH_SEQ = [4, 4, 4, 4, 4, 4]
    ALL_MOLE_DISTS = [[0.1, 0.1, 0.2, 0.6],
                      [0.2, 0.6, 0.1, 0.1],
                      [0.6, 0.2, 0.1, 0.1]]
    ALL_ANIMAL_DISTS = [[0.25, 0.25, 0.25, 0.25],
                        [0.25, 0.25, 0.25, 0.25],
                        [0.25, 0.25, 0.25, 0.25]]
    
    WARMUP_TRIAL_NO, REAL_TRIAL_NO = 20, 200

    def __init__(self):
        """Initialize a game with a given world.
        """
        # set up screen 
        self.screen = pygame.display.set_mode(Game.SCREEN_SIZE, 0, 32)
        self.state = Game.S_MENU
        self.fullscreen = False

        # set up menu
        self.menu = Menu()
        self.menu.set_fontsize(44)
        self.menu.init(['Warm up', 'Start Game', 'Exit'], self.screen)

        # set up the world 
        world = World(dist_seq = Game.DIST_SEQ,
                      bundle_length_seq = Game.BUNDLE_LENGTH_SEQ,
                      all_mole_dists = Game.ALL_MOLE_DISTS,
                      all_animal_dists = Game.ALL_ANIMAL_DISTS,
                      correlated = args.correlated_cue == 'yes')
        world.add_tree()
        world.add_scorebar()
        
        world.hole_positions = Game.HOLE_POSITIONS
        for hole_id in xrange(len(Game.HOLE_POSITIONS)):
            hole = Hole(world, hole_id)
            world.add_entity(hole)
        
            # hole covers are set up to prevent distractors from being positioned above holes
            hole_cover = GameEntity(world, 'hole_cover', pygame.Surface(hole.image.get_size(), SRCALPHA, 32))
            x, y, w, h = hole.rect
            hole_cover.rect = Rect(x, y - h, w, h)
            world.add_entity(hole_cover)

        self.world = world
        
    def start(self):
        """Start the game.
        """
        while True:

            if self.state == Game.S_MENU:
                self.screen.fill((51,51,51))
                self.menu.draw()
                pygame.mixer.music.stop()

            # React to user choices at the menu screen
            e = pygame.event.wait()
            if e.type == KEYDOWN:
                if e.key == K_f:
                    self.fullscreen = not self.fullscreen
                    if self.fullscreen:
                        self.screen = pygame.display.set_mode(SCREEN_SIZE, FULLSCREEN, 32)
                    else:
                        self.screen = pygame.display.set_mode(SCREEN_SIZE, 0, 32)
                elif e.key == K_UP:
                    self.menu.draw(-1)
                elif e.key == K_DOWN:
                    self.menu.draw(1)
                elif e.key == K_RETURN:
                    choice = self.menu.get_position()
                    if choice == Game.M_START_GAME:
                        for block in ([0,1]):
                            self.state = block
                            whack_session(bundle_indices = block)
                            pause_game(self.screen)
                            self.state = Game.S_MENU
                    elif choice == Game.M_WARM_UP:
                        self.state = Game.S_WARM_UP
                        whack_session(warm_up=True)
                        self.state = Game.S_MENU
                    elif choice == Game.M_EXIT:
                        return

            if e.type == QUIT:
                return

            pygame.display.update()
        
    def rearrange_animals(self):
        """Randomly rearrange the positions of animals on the screen.
        """    
        for entity in self.world.entities:
            if entity.type == 'animal':
                entity.auto_location()
                
    def whack_session(self, bundle_indices = None, warm_up = False):
        """Start the game. 
        """
        # show a "GET Ready"
        message = "Get Ready!"
        countdown = 3
        self.screen.fill((255,255,255))
        font = pygame.font.Font("data/fof.ttf", 80);
        text_surface = font.render(message, True, (0, 0, 0))
        for i in xrange(3):
            self.screen.fill((245,245,245))
            self.screen.blit(text_surface, (350,280))
            countdown_surface = font.render(str(countdown-i), True, (0,0,0))
            self.screen.blit(countdown_surface, (500,430))
            pygame.mixer.Sound('sounds/ticking.wav').play()
            pygame.display.update()
            pygame.time.wait(1000)
            
        pygame.mouse.set_visible(True)
        pygame.mixer.music.play()

        # set up clock
        clock = pygame.time.Clock()
        
        # restrict the activity of the mole
        move_count = 0

        # take care of mode differences
        # If mode is set to WARM_UP, use a uniform distribution for mole position. 
        if self.state == S_WARM_UP:
            bundle_length = 20,
            mole_dist = [0.25, 0.25, 0.25, 0.25]
            animal_dist = [0.25, 0.25, 0.25, 0.25]
        
        # start the trials
        for bundle_idx in bundle_indices:
            bundle_length, mole_dist, animal_dist = self.world.get_bundle_info(self.bundle_idx)

            # here and below needs work
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
                        self.world.mole.get_whacked(mouse_x, mouse_y)

                time_passed = clock.tick(60)
                
                if self.world.mole.moveable():
                    rearrange_distractors(self.world)
                    self.world.mole.move_weighted(verbose = False)
        
                self.world.mole.show(time_passed)
                self.world.mole.wait(time_passed)
                self.world.mole.hide(time_passed)

                if self.world.mole.moved > move_count:
                    move_count += 1
                    break

                self.world.render(self.screen)
                self.world.mole.show_hammered_image(self.screen)

                pygame.display.update()

            # make a record of this trial
            if self.state in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5): 
                self.world.record(rt = self.world.mole.get_alive_time(),
                             trial_no = trial_no, 
                             run_length = current_max_run)

            # print 'trial: ', trial_no , self.world.mole.get_alive_time()

            if current_run >= current_max_run:
                print("Reached the end of the bundle.", file=sys.stderr)
                if trial_no >= trial_total: break
                current_max_run = 25
                current_run = 0
                self.world.set_hole_dist()

            
        if self.state in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4, S_BLOCK5):
            self.world.print_history(open(str(datetime.now()) + '.txt', 'w'))

def pause_game(screen, world):

    if self.state in (S_BLOCK1, S_BLOCK2, S_BLOCK3, S_BLOCK4):
        score_msg = "Good job! Your score is %s" % (world.score)
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

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the Whack-The-Mole experiment.')
    parser.add_argument('--correlated_cue', choices=['yes', 'no'], default = 'no',
                        help='specify whether the background animals are correlated with contexts')
    args = parser.parse_args()

    pygame.init()
        
    g = Game()
    g.start()
   
