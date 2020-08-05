import js
jq = js.jQuery
q = js.query
window = js.window
import collections
import random

colors = 'kwrgb'

Noble = collections.namedtuple('Noble', ['points',
                                       'k', 'w', 'r', 'b', 'g'])
Card = collections.namedtuple('Card', ['level', 'bonus', 'points',
                                       'k', 'w', 'r', 'b', 'g'])
template_nobles = [[3,3,3,0,0, 3],
                   [4,4,0,0,0, 3],
                  ]
def generate_nobles():
    nobles = []
    for i, color in enumerate(['w', 'k', 'r', 'g', 'b']):
        for data in template_nobles:
            n = Noble(points=data[5],
                      w=data[(0+i)%5],
                      k=data[(1+i)%5],
                      r=data[(2+i)%5],
                      g=data[(3+i)%5],
                      b=data[(4+i)%5])
            nobles.append(n)
    return nobles


template_cards = {
    1: [[0,1,0,2,2, 0],
        [0,1,2,0,0, 0],
        [0,1,1,1,1, 0],
        [0,0,0,0,3, 0],
        [0,0,0,2,2, 0],
        [0,1,1,2,1, 0],
        [3,1,0,0,1, 0],
        [0,0,0,4,0, 1],
        ],
    2: [[0,2,2,3,0, 1],
        [2,0,3,0,3, 1],
        [0,2,4,1,0, 2],
        [0,0,5,0,0, 2],
        [0,3,5,0,0, 2],
        [6,0,0,0,0, 3],
        ],
    3: [[0,3,5,3,3, 3],
        [0,7,0,0,0, 4],
        [3,6,3,0,0, 4],
        [3,7,0,0,0, 5],
        ],
    }

def generate_cards():
    cards = []
    for i, color in enumerate(['w', 'k', 'r', 'g', 'b']):
        for level, templ in template_cards.items():
            for data in templ:
                c = Card(level=level, bonus=color, points=data[5],
                         w=data[(0+i)%5],
                         k=data[(1+i)%5],
                         r=data[(2+i)%5],
                         g=data[(3+i)%5],
                         b=data[(4+i)%5])
                cards.append(c)
    return cards



class Player(object):
    def __init__(self, game):
        self.game = game
        self.chips = {c:0 for c in colors+'x'}
        self.bonus = {c:0 for c in colors}
        self.cards = []
        self.reserve = []
        self.nobles = []
        self.points = 0
        self.drawn_this_turn = []
        self.reserving = False
        self.must_discard = False

    def can_reserve_card(self, card):
        if self.game.players[self.game.current_player] is not self:
            return False
        if self.game.must_select_noble:
            return False
        if len(self.reserve) >= 3:
            return False
        if not self.game.is_in_tableau(card):
            return False
        return True

    def reserve_card(self, card):        
        assert self.can_reserve_card(card)
        self.reserve.append(card)
        self.game.remove_card(card)
        self.reserving = False
        self.game.end_turn()

    def can_play(self, card):
        if self.game.players[self.game.current_player] is not self:
            return False
        if self.game.must_select_noble:
            return False
        if not self.game.is_in_tableau(card) and card not in self.reserve:
            return False
        extra_needed = 0
        for c in colors:
            cost = getattr(card, c)
            if self.chips[c] + self.bonus[c] < cost:
                extra_needed += cost - (self.chips[c] + self.bonus[c])
        if extra_needed > self.chips['x']:
            return False
        return True

    def play(self, card):
        assert self.can_play(card)
        self.cards.append(card)
        if card in self.reserve:
            self.reserve.remove(card)
        else:
            self.game.remove_card(card)
        for c in colors:
            cost = getattr(card, c)
            self.chips[c] -= max(cost - self.bonus[c], 0)
            self.game.chips[c] += max(cost - self.bonus[c], 0)
            if self.chips[c] < 0:
                self.chips['x'] += self.chips[c]
                self.game.chips[c] += self.chips[c]
                self.game.chips['x'] -= self.chips[c]
                self.chips[c] = 0
        self.bonus[card.bonus] += 1
        self.points += card.points
        self.check_nobles()
        if self.points >= 1:
            self.game.end_game = True
        self.game.end_turn()

    def check_nobles(self):
        my_nobles = []
        for n in self.game.nobles:
            for c in colors:
                if getattr(n, c) > self.bonus[c]:
                    break
            else:
                my_nobles.append(n)
        if len(my_nobles) == 1:
            n = my_nobles[0]
            self.nobles.append(n)
            self.game.nobles.remove(n)
            self.points += n.points
        elif len(my_nobles) > 1:
            self.game.must_select_noble = True
            self.game.selectable_nobles = my_nobles

    def can_select_noble(self, noble):
        if self.game.players[self.game.current_player] is not self:
            return False
        if not self.game.must_select_noble:
            return False
        if noble not in self.game.selectable_nobles:
            return False
        return True

    def select_noble(self, noble):
        assert self.can_select_noble(noble)
        self.nobles.append(noble)
        self.points += noble.points
        self.game.nobles.remove(noble)
        self.game.must_select_noble = False
        self.game.selectable_nobles = None

    def valid_actions(self):
        actions = []
        
        if self.must_discard:
            for c in colors + 'x':
                if self.chips[c] > 0:
                    actions.append((self.return_chip, dict(color=c)))
        elif self.reserving:
            for level in [3, 2, 1]:
                for card in self.game.tableau[level]:
                    if card is not None:
                        actions.append((self.reserve_card, dict(card=card)))
        elif len(self.drawn_this_turn) == 0:
            if self.game.must_select_noble:
                for n in self.game.selectable_nobles:
                    actions.append((self.select_noble, dict(noble=n)))
                return actions

            for level in [1, 2, 3]:
                for card in self.game.tableau[level]:
                    if card is not None:
                        if self.can_play(card):
                            actions.append((self.play, dict(card=card)))
            for card in self.reserve:
                if self.can_play(card):
                    actions.append((self.play, dict(card=card)))
            for i, c in enumerate(colors):
                if self.game.chips[c] > 0:
                    actions.append((self.draw, dict(color=c)))
            if self.game.chips['x'] > 0 and len(self.reserve)<3:
                actions.append((self.draw, dict(color='x')))
        else:
            for i, c in enumerate(colors):
                if self.can_draw(c):
                    actions.append((self.draw, dict(color=c)))
        return actions
        
    def can_draw(self, color):
        if color == 'x':
            if len(self.drawn_this_turn) == 0 and len(self.reserved) < 3:
                return True
        elif game.chips[color] > 0:
            if color not in self.drawn_this_turn:
                return True
            elif self.game.chips[color] >= 3 and len(self.drawn_this_turn) == 1:
                return True
        return False
    
        
    def draw(self, color):
        if color == 'x' and self.game.chips[color] == 0:
            pass
        else:
            self.game.chips[color] -= 1
            self.chips[color] += 1
        self.drawn_this_turn.append(color)
        if color == 'x':
            if len(self.reserve) < 3:
                self.reserving = True
            return
        if len(self.drawn_this_turn) >= 3:
            self.game.end_turn()
        if len(self.drawn_this_turn) >= 2 and color in self.drawn_this_turn[:-1]:
            self.game.end_turn()
        if sum([self.can_draw(c) for c in colors]) == 0:
            self.game.end_turn()
            
    def has_too_many(self):
        return sum(self.chips.values()) > 10
        
    def return_chip(self, color):
        if self.chips[color] > 0:
            self.chips[color] -= 1
            self.game.chips[color] +=1
        self.game.end_turn()
            

class Splendor(object):
    def __init__(self, seed):
        self.started = False
        self.n_players = 1
        self.current_player = None
        self.seed = seed
        all_cards = generate_cards()
        rng = random.Random()
        rng.seed(self.seed)
        rng.shuffle(all_cards)
        self.levels = {}
        self.tableau = {}
        for level in [1, 2, 3]:
            self.levels[level] = [x for x in all_cards if x.level==level]
            self.tableau[level] = [None] * 4
            
        all_nobles = generate_nobles()
        rng.shuffle(all_nobles)
        self.nobles = all_nobles
        self.must_select_noble = False
        self.end_game = False
        self.winners = None
        self.pass_count = 0
        self.rng = rng
        self.chips = {}

            
    
    def start(self):
        self.started = True
        n_players = self.n_players
        self.nobles = self.nobles[:n_players+1]
        self.players = [Player(self) for i in range(n_players)]
        for level in [1, 2, 3]:
            self.tableau[level] = [self.draw(level) for j in range(4)]

        self.first_player = self.rng.randrange(n_players)
        self.current_player = self.first_player

        n_chips = 7 if n_players > 2 else 4
        self.chips = dict(k=n_chips, w=n_chips, r=n_chips,
                          g=n_chips, b=n_chips, x=5)

    def draw(self, level):
        if len(self.levels[level]) == 0:
            return None
        return self.levels[level].pop()

    def is_in_tableau(self, card):
        for level in [1, 2, 3]:
            if card in self.tableau[level]:
                return True
        return False

    def remove_card(self, card):
        for level in [1, 2, 3]:
            if card in self.tableau[level]:
                index = self.tableau[level].index(card)
                self.tableau[level][index] = self.draw(level)
                return
        raise Exception('removed unknown card')

    def pass_turn(self):
        self.pass_count += 1
        if self.pass_count == len(self.players):
            self.winners = []
            self.current_player = None
        else:
            self.end_turn(reset_pass=False)

    def end_turn(self, reset_pass=True):
        if self.players[self.current_player].has_too_many():
            self.players[self.current_player].must_discard = True
            return
        self.players[self.current_player].must_discard = False
        
        if reset_pass:
            self.pass_count = 0
        del self.players[self.current_player].drawn_this_turn[:]            
        self.current_player = ((self.current_player + 1) % len(self.players))
        if self.end_game and self.current_player == self.first_player:
            max_points = max([p.points for p in self.players])
            self.winners = [p for p in self.players if p.points == max_points]
            self.current_player = None
    
    def add_player(self):
        self.n_players += 1
        
    def remove_player(self):
        self.n_players -= 1
        
    def valid_actions(self):
        if not self.started:
            actions = []
            actions.append((self.add_player, {}))
            if self.n_players > 1:
                actions.append((self.remove_player, {}))
            actions.append((self.start, {}))
        elif self.current_player is not None:
            p = game.players[game.current_player]
            actions = p.valid_actions()        
        else:
            actions = []
        return actions



def text_game_state(game):
    if not game.started:
        return 'Ready to play with %d players' % game.n_players
    rows = []
    n = ''.join('%14s' % text_noble(n) for n in game.nobles)
    rows.append(n)
    '''
    rows.append('-'*76)
    for level in [3, 2, 1]:
        lev = ''.join('%19s' % text_card(c) for c in game.tableau[level])
        rows.append(lev)
    rows.append('-'*76)
    '''
    #chips = []
    #for c in colors+'x':
    #    chips.append('%d%s' % (game.chips[c], c))
    #rows.append('  '.join(chips))
    #rows.append('='*76)


    '''
    for i, p in enumerate(game.players):
        current = '*' if game.current_player == i else ' '
        chip_info = []
        for c in colors:
            bonus = p.bonus[c]
            chips = p.chips[c]
            if bonus > 0:
                if chips > 0:
                    chip_info.append('%d[+%d]%s' % (chips, bonus, c))
                else:
                    chip_info.append('[+%d]%s' % (bonus, c))
            else:
                chip_info.append('%d%s' % (chips, c))
        if p.chips['x'] > 0:
            chip_info.append('%dx' % (p.chips['x']))
        if len(p.reserve) > 0:
            reserve = ' '.join(text_card(c) for c in p.reserve)
        else:
            reserve = ''
        if len(p.nobles) > 0:
            nobles = ' '.join(text_noble(n) for n in p.nobles)
        else:
            nobles = ''

        rows.append('%sP%d [%d] %s %s %s' % (current, i, p.points, 
                                            ':'.join(chip_info), nobles, reserve))
    '''
    return '\n'.join(rows)

def text_noble(noble):
    cost = []
    for c in colors:
        v = getattr(noble, c)
        if v > 0:
            cost.append('%d%s' % (v, c))
    return '[%d](%s)' % (noble.points, ':'.join(cost))


def text_card(card):
    if card is None:
        return '----'
    points = '+%d' % card.points if card.points > 0 else ''

    cost = []
    for c in 'kwrgb':
        v = getattr(card, c)
        if v > 0:
            cost.append('%d%s' % (v, c))

    return '[%s%s](%s)' % (card.bonus, points, ':'.join(cost))
    
def code_noble(noble):
    code = 'n-'
    for c in 'kwrgb':
        v = getattr(noble, c)
        if v > 0:
            code += c * v
    return code

def code_card(card):
    code = '%s%d-' % (card.bonus, card.points)
    for c in 'kwrgb':
        v = getattr(card, c)
        if v > 0:
            code += c * v
    return code
    

def text_action(func, args):
    name = func.__name__
    if name == 'draw_three':
        return 'Draw Three: %s %s %s' % tuple(args.keys())
    elif name == 'draw_two':
        return 'Draw Two: %s' % args['color']
    elif name == 'draw':
        return 'Draw: %s' % args['color']        
    elif name == 'reserve_card':
        return 'Reserve: %s' % text_card(args['card'])
    elif name == 'play':
        return 'Play: %s' % text_card(args['card'])
    elif name == 'add_player':
        return 'Add a player'
    elif name == 'remove_player':
        return 'Remove a player'
    elif name == 'start':
        return 'Start game'
    else:
        return name, args
def code_action(func, args):
    name = func.__name__
    if name == 'draw':
        return 'd:%s' % args['color']
    elif name == 'reserve_card':
        return 'r:%s' % text_card(args['card'])
    elif name == 'play':
        return 'p:%s' % text_card(args['card'])
    elif name == 'add_player':
        return 'add'
    elif name == 'remove_player':
        return 'remove'
    elif name == 'start':
        return 'start'
    elif name == 'return_chip':
        return 'return:%s' % args['color']
    else:
        return 'unknown:%r %r' % (name, args)
        
def ui_action(func, args):
    name = func.__name__
    cmd = "peerstack.add('%s')" % code_action(func, args)
    if name == 'draw':
        obj = q('#chip-%s' % args['color'])
    elif name == 'play':
        obj = q('#%s' % code_card(args['card']))
    elif name == 'reserve_card':
        obj = q('#%s' % code_card(args['card']))
    elif name == 'return_chip':
        obj = q('#chip-%d-%s' % (player_index, args['color']))
    else:
        return False
    obj.attr('onclick', cmd)
    obj.addClass("action")
    return True
        
def html_action(func, args):
    code = "peerstack.add('%s')" % code_action(func, args)
    return '<button onclick="%s">%s</li>' % (code, text_action(func, args))

def act(code):
    actions = game.valid_actions()
    for f, a in actions:
        code2 = code_action(f, a)
        if code == code2:
            f(**a)
    
def update(animate=True):
    for c in generate_cards():
        id = code_card(c)
        card = q('#%s' % id)
        z = 0
        
        reserve = False
        if c in game.levels[c.level]:
            pos_top = {1:50,2:35,3:20}[c.level]
            pos_left = -10
            facedown = True
        elif c in game.tableau[c.level]:
            index = game.tableau[c.level].index(c)
            pos_top = {1:50,2:35,3:20}[c.level]
            pos_left = 22.5 + 16*index
            facedown = False
        elif game.started:
            for i, player in enumerate(game.players):
                if c in player.cards:
                    pos_top, pos_left = calc_item_position(player=i, color=c.bonus)
                    offset = [cc for cc in player.cards if c.bonus==cc.bonus].index(c)
                    pos_top += offset*2
                    pos_left += offset*1
                    z = offset
                    facedown = False
                    break
                elif c in player.reserve:
                    pos_top, pos_left = calc_item_position(player=i, color='x')
                    offset = player.reserve.index(c)
                    pos_top += offset*4
                    pos_left += offset*2
                    z = offset
                    facedown = False
                    reserve = True
                    break
                
            else:
                continue
        else:
            continue
            
        if animate:
            now_top = card.prop('style')['top']
            now_left = card.prop('style')['left']
            pos_top = '%g%%'%pos_top
            pos_left = '%g%%'%pos_left
            if pos_top != now_top or pos_left != now_left:
                card.animate({'top':pos_top, 'left':pos_left, 'z-index':z}, 500)
        else:
            card.prop('style', 'top:%g%%; left:%g%%; z-index:%d;' % (pos_top, pos_left, z))
        if facedown:
            card.addClass('facedown')
        else:
            card.removeClass('facedown')
        if reserve:
            card.addClass('reserve')
        else:
            card.removeClass('reserve')
    
    
    for n in generate_nobles():
        id = code_noble(n)
        noble = q('#%s' % id)
        left = -10
        top = 50
        z = 10000
        if game.started:
            if n in game.nobles:
                index = game.nobles.index(n)
                spacing = 50 / (game.n_players + 1)
                top = 20 + spacing*index
                left = 2.5
            else:
                for i, player in enumerate(game.players):
                    if n in player.nobles:
                        top, left = calc_item_position(player=i, color='*')
                        index = player.nobles.index(n)
                        top += index*6
                        z += index
                    
        if animate:
            now_top = noble.prop('style')['top']
            now_left = noble.prop('style')['left']
            pos_top = '%g%%'%top
            pos_left = '%g%%'%left
            if pos_top != now_top or pos_left != now_left:
                noble.animate({'top':pos_top, 'left':pos_left, 'z-index':z}, 500)
        else:
            noble.prop('style', 'top:%g%%; left:%g%%; z-index:%d;' % (top, left, z))
        
            
    for k, v in game.chips.items():
        chip = q('#chip-%s' % k)
        chip.text('%d' % v)
        if v == 0:
            chip.addClass("empty")
        else:
            chip.removeClass("empty")
            
    if game.started:
        for i in range(game.n_players):
            for k, v in game.players[i].chips.items():
                chip = q('#chip-%d-%s' % (i,k))
                chip.text('%d' % v)
                if v == 0:
                    chip.addClass("empty")
                else:
                    chip.removeClass("empty")
                  

    q('.chip').removeClass("action")
    q('.chip').attr("onclick", "")
    q('.card').removeClass("action")
    q('.card').attr("onclick", "")
    
    if game.started:
        scores = ' '.join(['%d'%p.points for p in game.players])
        scores = 'Scores: %s' % scores
    else: 
        scores = ''
    
    if game.started and game.current_player == None:
        q('#actions').html('%s<br></br>Game over! <button onclick="restart();">Restart</button>'%scores)
        return
    
    actions = game.valid_actions()
    html = []
    if game.current_player == player_index or not game.started:
        for a in actions:
            handled = ui_action(*a)
            if not handled:
                html.append(html_action(*a))
    if len(html) > 0:
        q('#actions').html('%s<ul>%s</ul>'%(scores, ''.join(html)))
    else:
        q('#actions').html(scores)
    
    
initialized_players = None     
player_index = 0
    
    
def on_changed(items, metadata):
    global game
    global player_index
    print('on_changed')
    print(player_index, window.peerstack.index)
    force = False
    if player_index == 0 and not window.peerstack.is_host:
        player_index = window.peerstack.index
        force = True
    game = Splendor(seed=metadata['seed'])
    for item in items:
        act(item)
    init_game_ui(force=force)
    update(animate=game.started)
    
def change_player_index(index):
    global player_index
    player_index = index
    init_game_ui(force=True)
    update(animate=True)

def get_player_index():
    return player_index
    
    
    
def initialize_ui():
    board = q('#board')
    board.html('')
    for c in generate_cards():
        id = code_card(c)
        
        card = q('<div></div>')
        card.prop('id',id)
        card.prop('class','card %c facedown level%d'%(c.bonus, c.level))
        if c.points > 0:
            card.append('<div class="points">%d</div>' % c.points)
        cost = q('<div class="cost"></div>')
        for cc in colors:
            v = getattr(c, cc)
            if v > 0:
                cost.append('<div class="cost_%s">%d</div>' % (cc, v))
        card.append(cost)
        
        board.append(card)
    for i, c in enumerate(colors+'x'):
        top = 20 + i*7
        coin = q('<div id="chip-%s" class="chip %s empty" style="top:%g%%; left:85%%">0</div>' % (c, c, top))
        board.append(coin)
    
    for n in generate_nobles():
        id = code_noble(n)
        noble = q('<div></div>')
        noble.prop('id', id)
        noble.prop('class', 'noble x')
        noble.prop('style', 'top:50%; left:-10%; z-index:0;')
        for cc in colors:
            v = getattr(n, cc)
            if v > 0:
                noble.append('<div class="cost_%s">%d</div>' % (cc, v))
        
        board.append(noble)
     
     

def init_game_ui(force=False):

    global initialized_players
    if initialized_players == game.n_players and game.started and not force:
        return
    
    board = q('#board')
    
    if initialized_players is not None:
        for i in range(initialized_players):
            for c in colors+'x':
                q('#chip-%d-%s' % (i, c)).remove()
    
    for i in range(game.n_players):
        for c in colors+'x':
            top, left = calc_item_position(i, c)
            top += 10
            left -=1
            coin = q('<div id="chip-%d-%s" class="chip %s empty" style="top:%g%%; left:%g%%">0</div>' % (i, c, c, top, left))
            board.append(coin)
    initialized_players = game.n_players
        
        
def calc_item_position(player, color):
    if player == player_index:
        top = 65
        index = ('*'+colors+'x').index(color)
        left = 2 + index*12
    else:
        n_others = game.n_players
        if player_index < game.n_players:
            n_others -= 1
        if n_others == 0:
            n_others = 1   # this should not happen
            console.log('calc_item_position called for n_others=0')
        width = 100 / (n_others)
        top_index = player
        if player_index < player:
            top_index -= 1
        top = 0
        index = ('*'+colors+'x').index(color)
        left = (2 + index*12) * width / 100 + top_index * width
    return top, left
initialize_ui()

