#!/usr/bin/env python
#-*- coding: utf-8 -*-

from __future__ import print_function
from wam import *
from slidemenu.slidemenu import *
import sys, argparse, gzip, random
from datetime import datetime
from time import time

class Game(object):
    
    SCREEN_SIZE = (1000, 734)
    WARM_UP_TRIAL_NO = 20

    def __init__(self,
                 subj_id,
                 dist_seq, # the sequence of distributions implemented by each bundle; N = # of bundles
                 bundle_length_seq, # the length of each bundle; N = # of bundles
                 all_mole_dists, # the probability distribution of mole positions; N = # of unique distributions
                 all_animal_dists, # the probability distribution of background animals; N = # of unique animal distributions
                 exact_proportion,
                 hole_positions = [(320,450), (300, 600), (700, 500), (680, 650)],
                 mumble = False, compress = False):
        """Initialize a game with a given world.
        """
        self.subj_id = subj_id
        assert len(dist_seq) == len(bundle_length_seq)
        assert len(all_mole_dists) == len(all_animal_dists)
        self.dist_seq, self.bundle_length_seq = dist_seq, bundle_length_seq
        self.all_mole_dists, self.all_animal_dists = all_mole_dists, all_animal_dists
        self.exact_proportion = exact_proportion
        self.num_of_blocks = len(self.dist_seq)
        self.session_trial = 0

        self.dist_history = {}
        self.animal_dist_history = {}

        # set up output file
        if compress:
            self.dest = gzip.open('_'.join([subj_id, datetime.today().strftime('%Y-%m-%d-%H-%M')]) + '.csv.gz', 'w')
        else:
            self.dest = open('_'.join([subj_id, datetime.today().strftime('%Y-%m-%d-%H-%M')]) + '.csv', 'w')
        self.mumble = mumble
            
        # set up screen 
        self.screen = pygame.display.set_mode(Game.SCREEN_SIZE, 0, 32)
        self.fullscreen = False

        # set up the world
        world = World()
        world.add_tree()
        world.add_scorebar()
        
        world.hole_positions = hole_positions
        for hole_id in xrange(len(hole_positions)):
            hole = Hole(world, hole_id)
            world.add_entity(hole)
        
            # hole covers are set up to prevent distractors from being positioned above holes
            hole_cover = GameEntity(world, 'hole_cover', pygame.Surface(hole.image.get_size(), SRCALPHA, 32))
            x, y, w, h = hole.rect
            hole_cover.rect = Rect(x, y - h, w, h)
            world.add_entity(hole_cover)

        self.world = world

    def get_bundle_info(self, block, bundle_idx=None):
        """Given a bundle index, retrieve its length, the associated distribution of mole positions,
        and its distribution of background animals.
        """
        if block == 'WARM_UP':
            bundle_length = Game.WARM_UP_TRIAL_NO
            mole_dist = [0.25] * 4
            animal_dist = {'rabbit': 2, 'snail': 2, 'hippo': 2, 'dinosaur': 2}
            mole_dist_idx, animal_dist_idx = 0, 0
        else:
            assert type(block) is int and type(bundle_idx) is int
            mole_dist_idx, animal_dist_idx = self.dist_seq[block][bundle_idx]
            bundle_length = self.bundle_length_seq[block][bundle_idx]
            mole_dist = self.all_mole_dists[mole_dist_idx]
            animal_dist = self.all_animal_dists[animal_dist_idx]
            
        return bundle_length, mole_dist, animal_dist, mole_dist_idx, animal_dist_idx
        
    def start(self):
        """Start the game.
        """
        while True:
            self.screen.fill((0,0,0))
            pygame.display.update()
            pygame.mixer.music.stop()
            resp = menu(['Warm up', 'Start Game', 'Toggle fullscreen', 'Exit'],
                        color1     = (255,80,40),
                        light      = 9,
                        tooltiptime= 1000,
                        #cursor_img = image.load('mouse.png'),
                        hotspot    = (38,15))
                    
            # React to user choices at the menu screen
            if resp[0] == 'Toggle fullscreen':
                self.fullscreen = not self.fullscreen
                if self.fullscreen:
                    self.screen = pygame.display.set_mode(Game.SCREEN_SIZE, FULLSCREEN, 32)
                else:
                    self.screen = pygame.display.set_mode(Game.SCREEN_SIZE, 0, 32)
            elif resp[0] == 'Start Game':
                for block in xrange(self.num_of_blocks):
                    self.whack_session(block = block)
                    self.pause_game(block = block)
            elif resp[0] == 'Warm up':
                self.whack_session(block = 'WARM_UP')
            elif resp[0] == 'Exit':
                return

            pygame.display.update()
        
    def rearrange_animals(self):
        """Randomly rearrange the positions of animals on the screen.
        """    
        for entity in self.world.entities:
            if entity.type == 'animal':
                entity.auto_location()
                
    def whack_session(self, block):
        """Start the game. 
        """
        # set up a few variables for recording data
        block_trial = 0
        dist_history_block = {}
        animal_dist_history_block = {}
        
        # session prompt
        message, countdown = "Get Ready!", 3
        self.screen.fill((255,255,255))
        font = pygame.font.Font("data/fof.ttf", 80);
        text_surface = font.render(message, True, (0, 0, 0))

        # set up clock
        clock = pygame.time.Clock()
        
        for i in xrange(3):
            self.screen.fill((245,245,245))
            self.screen.blit(text_surface, (350,280))
            countdown_surface = font.render(str(countdown-i), True, (0,0,0))
            self.screen.blit(countdown_surface, (500,430))
            pygame.mixer.Sound('sounds/ticking.wav').play()
            pygame.display.update()
            timer = 0
            while timer < 1000:
                pygame.event.pump()
                timer += clock.tick(60)

        # begin session
        pygame.mouse.set_visible(True)
        pygame.mixer.music.play()

        # The difference between a warm up session and a regular session
        # is taken care of by the start() method
        if block == 'WARM_UP':
            bundle_range = [None]
        else: bundle_range = range(len(self.dist_seq[block]))
        
        # start the trials
        for bundle_idx in bundle_range:
            bundle_length, mole_dist, animal_dist, mole_dist_idx, animal_dist_idx = self.get_bundle_info(block, bundle_idx)
            # add statistics
            try: self.dist_history[mole_dist_idx] += 1
            except KeyError: self.dist_history[mole_dist_idx] = 0
            try: dist_history_block[mole_dist_idx] += 1
            except KeyError: dist_history_block[mole_dist_idx] = 0
            try: self.animal_dist_history[animal_dist_idx] += 1
            except KeyError: self.animal_dist_history[animal_dist_idx] = 0
            try: animal_dist_history_block[animal_dist_idx] += 1
            except KeyError: animal_dist_history_block[animal_dist_idx] = 0
            
            # add the mole and the animals to the world
            self.world.add_mole(mole_dist)
            self.world.add_animals(animal_dist)

            # generate the exact proportion list
            location_list = []
            for loc_idx in xrange(4):
                location_list.extend([loc_idx] * int(bundle_length * mole_dist[loc_idx]))
            random.shuffle(location_list)
            
            # reset clock
            clock.tick()
            # loop over all bundle trials
            for bundle_trial in range(bundle_length):
                while True:
                    for event in pygame.event.get():
                        if event.type == KEYDOWN:
                            if event.key == K_ESCAPE:
                                try: self.dest.flush()
                                except: pass
                                return
                            if event.key == K_s:
                                if pygame.mixer.music.get_busy():
                                    pygame.mixer.music.fadeout(2000)
                                else:
                                    pygame.mixer.music.play()
                        if event.type == MOUSEBUTTONDOWN:
                            mouse_x, mouse_y = pygame.mouse.get_pos()
                            self.world.mole.get_whacked(mouse_x, mouse_y)

                
                    if self.world.mole.moveable():
                        self.rearrange_animals()
                        if self.exact_proportion:
                            self.world.mole.move_to_hole(location_list[bundle_trial])
                        else:
                            self.world.mole.move_weighted(verbose = False)

                    time_passed = clock.tick(60)
                    self.world.mole.show(time_passed)
                    self.world.mole.wait(time_passed)
                    self.world.mole.hide(time_passed)

                    # detect the end of a trial
                    if self.world.mole.visible is False and self.world.mole.status == 'STILL':
                        break

                    self.world.render(self.screen)
                    self.world.mole.show_hammered_image(self.screen)

                    pygame.display.update()

                # make a record of this trial
                self.record(
                    dest = self.dest,
                    subject = self.subj_id, block = block, bundle = bundle_idx, 
                    session_trial = self.session_trial, block_trial = block_trial, bundle_trial = bundle_trial,
                    reaction_time = self.world.mole.get_alive_time(), score = self.world.score,
                    which_hole = self.world.mole.current_hole_id,
                    hole0_design_prob = mole_dist[0], hole1_design_prob = mole_dist[1],
                    hole2_design_prob = mole_dist[2], hole3_design_prob = mole_dist[3],
                    bundle_length = bundle_length,
                    rabbit_count = animal_dist['rabbit'], snail_count = animal_dist['snail'],
                    dinosaur_count = animal_dist['dinosaur'], hippo_count = animal_dist['hippo'],
                    mole_dist_freq = self.dist_history[mole_dist_idx], mole_dist_freq_block = dist_history_block[mole_dist_idx],
                    animal_dist_freq = self.animal_dist_history[animal_dist_idx], animal_dist_freq_block = animal_dist_history_block[animal_dist_idx]
                )
                block_trial += 1
                self.session_trial += 1

            # flush out the result at the end of a bundle
            try: self.dest.flush()
            except: pass

                
                
    def pause_game(self, block):
        """Pause or end the game. If all blocks are presented the game will end.
        Otherwise, display a score and force a break.
        """
        try: self.dest.flush()
        except: pass
        if block < self.num_of_blocks:
            score_msg = "Good job! Your score is %s" % (self.world.score)
            break_msg = "Take a break. A new wave of moles are coming in 2 minutes!"
            continue_msg = "Touch anywhere to continue"
            font = pygame.font.Font("data/intuitive.ttf", 30);
            score_surface = font.render(score_msg, True, (0, 0, 0))
            break_surface = font.render(break_msg, True, (0, 0, 0))        
            continue_surface = font.render(continue_msg, True, (255, 0, 0))
            self.screen.fill((245,245,245))

            clock = pygame.time.Clock()
            clock.tick(10)
            timer = 0
            self.screen.blit(score_surface, (340,240))
            self.screen.blit(break_surface, (140,320))

            pygame.mixer.music.stop()
            pygame.mouse.set_visible(True)

            pygame.display.update()
            # mandatory break of 2 minutes
            while timer < 1000 * 60 * 2:
                pygame.event.pump()
                timer += clock.tick(5)

            # after the break, prompt user to continue the game
            self.screen.blit(continue_surface, (350,420))
            pygame.display.update()
            pygame.event.clear()

            while True:
                event = pygame.event.wait()
                if event.type == MOUSEBUTTONUP: return

        else: # if all blocks have been presented, end game
            message = "Game Over. You did an excellent job!"
            font = pygame.font.Font("data/intuitive.ttf", 36);
            text_surface = font.render(message, True, (255, 0, 0))
            self.screen.fill((245,245,245))
            self.screen.blit(text_surface, (200,280))
            pygame.display.update()
            pygame.time.wait(1000 * 3)
            return

    def record(self, dest=sys.stdout, **kwargs):
        """Record all information of the current trial.
        """
        if kwargs['session_trial'] == 0:
            print(*[_.replace('_', '.') for _ in kwargs.keys()], file=dest, sep=',')
        if self.mumble:
            print(*[_.replace('_', '.') for _ in kwargs.keys()], file=sys.stderr, sep=',')
            
        print(*kwargs.values(), file=dest, sep=',')
        if self.mumble:
            print(*kwargs.values(), file=sys.stderr, sep=',')
            
        #self.run_history.append({
        #        'whack_coordinates': self.mole.rel_whack_coordinates})
        

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the Whack-The-Mole experiment.')
    parser.add_argument('--subj', default = 'unknown', type=str, help='Specify a Subject ID for traceable output data')
    parser.add_argument('--mumble', action='store_true', help='Also prints out results to the screen. Note that this information is sent to standard error so it cannot be captured by redirecting using >')
    args = parser.parse_args()

    pygame.init()

    ALL_MOLE_DISTS = [[0.6, 0.2, 0.1, 0.1],
                      [0.2, 0.6, 0.1, 0.1],
                      [0.1, 0.2, 0.6, 0.1],
                      [0.1, 0.1, 0.2, 0.6]]
    ALL_ANIMAL_DISTS = [{'rabbit': 2, 'snail': 2, 'hippo': 2, 'dinosaur': 2}] * 4
    
    # the (mole dist, animal dist) pair sequence used in each block
    # instead of *3, which says 3 three blocks of the same sequence,
    # you can also list all blocks manually, if variation between blocks is needed
    # e.g., DIST_SEQ = [[(0,0), (1,0), (2,0)], [(1,0), (2,0), (0,0)]] - everything counts from 0
    # PAY SPECIAL ATTENTION TO THE DOUBLE BRACKETS - we want a nested list, each child list represents a block
    DIST_SEQ = [[(0,0), (1,0), (2,0), (0,0), (3,0), (1,0), (3,0), (2,0), (1,0), (0,0), (2,0), (3,0)]] * 3

    # the same applies to the bundle length sequence
    BUNDLE_LENGTH_SEQ = [[20, 25, 30, 25, 20, 20, 30, 20, 30, 30, 25, 25]] * 3

    # set a flag that determines if mole locations are sampled on the fly
    # or selected (randomly) from an exact-proportion list
    EXACT_PROPORTION = True
    
    g = Game(
        mumble = args.mumble,
        subj_id = args.subj,
        dist_seq = DIST_SEQ, # the sequence of distributions implemented by each bundle; N = # of bundles
        bundle_length_seq = BUNDLE_LENGTH_SEQ, # the length of each bundle; N = # of bundles
        all_mole_dists = ALL_MOLE_DISTS, # the probability distribution of mole positions; N = # of unique distributions
        all_animal_dists = ALL_ANIMAL_DISTS,
        exact_proportion = EXACT_PROPORTION) # the probability distribution of background animals; N = # of unique animal distributions

    g.start()
   
