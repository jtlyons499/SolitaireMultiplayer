"""Exact pot awards with a player-controlled review screen."""
import pygame

OPEN = pygame.Rect(18, 82, 180, 40)
CLOSE = pygame.Rect(898, 652, 198, 48)
PREV = pygame.Rect(272, 652, 160, 48)
NEXT = pygame.Rect(444, 652, 160, 48)
ROWS = 9


def recap_lines(game):
    lines = []
    your_total = 0
    for index, pot in enumerate(game.last_pot_awards):
        label = 'Main pot' if index == 0 else f'Side pot {index}'
        lines.append(f"{label}: ${pot.get('amount', 0):,} — {pot.get('hand') or 'Everyone else folded'}")
        winners = pot.get('winners', [])
        for order, seat in enumerate(winners):
            amount = int(pot.get('share', 0)) + (order < int(pot.get('remainder', 0)))
            name = game.get_table_player_name(seat)
            if seat == 0:
                your_total += amount
            verb = "receive" if seat == 0 else "receives"
            lines.append(f"    {name} {verb} ${amount:,}" + (' (odd chip included)' if order < int(pot.get('remainder', 0)) else ''))
        eligible = [game.get_table_player_name(seat) for seat in pot.get('eligible', [])]
        lines.append('    Eligible: ' + ', '.join(eligible))
    if not lines:
        lines.append(game.result_text or 'No resolved pot.')
    contribution = int(getattr(game, 'player_hand_contribution', 0))
    net = your_total - contribution
    sign = '+' if net >= 0 else '−'
    lines.extend([f'You received: ${your_total:,}', f'Your hand contribution: ${contribution:,}',
                  f'Your net for this hand: {sign}${abs(net):,}'])
    return lines


def get_recap_action(mouse, game):
    if not game.hand_complete or mouse is None:
        return None
    if getattr(game, 'recap_open', False):
        for rect, name in ((CLOSE, 'recap_close'), (PREV, 'recap_prev'), (NEXT, 'recap_next')):
            if rect.collidepoint(mouse):
                return name
        return 'recap_block'
    if OPEN.collidepoint(mouse):
        return 'recap_open'
    return None


def handle_recap_action(game, action):
    if not action or not action.startswith('recap_'):
        return False
    if action == 'recap_open':
        game.recap_open, game.recap_page = True, 0
    elif action == 'recap_close':
        game.recap_open = False
    elif action in ('recap_prev', 'recap_next'):
        pages = max(1, (len(recap_lines(game)) + ROWS - 1) // ROWS)
        game.recap_page = max(0, min(pages - 1, getattr(game, 'recap_page', 0) + (1 if action == 'recap_next' else -1)))
    return True


def draw_recap(surface, mouse, game):
    if not game.hand_complete:
        return
    font = pygame.font.Font(None, 29)
    def button(rect, value, enabled=True):
        hover = enabled and mouse is not None and rect.collidepoint(mouse)
        pygame.draw.rect(surface, (52,100,78) if hover else (29,57,49), rect, border_radius=8)
        pygame.draw.rect(surface, (232,195,105) if enabled else (95,110,105), rect, 2, border_radius=8)
        text = font.render(value, True, (245,240,221) if enabled else (130,145,139))
        surface.blit(text, text.get_rect(center=rect.center))
    if not getattr(game, 'recap_open', False):
        button(OPEN, 'POT RECAP')
        return
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0,0,0,195));surface.blit(overlay,(0,0))
    panel = pygame.Rect(242, 58, 882, 658)
    pygame.draw.rect(surface, (22,40,38), panel, border_radius=18)
    pygame.draw.rect(surface, (230,191,98), panel, 3, border_radius=18)
    title = pygame.font.Font(None, 42).render('HAND / POT RECAP', True, (240,202,119))
    surface.blit(title, (272,82))
    surface.blit(font.render('Auto-deal and cash-out pause while you review.', True, (188,207,195)), (272,133))
    lines = recap_lines(game)
    pages = max(1, (len(lines)+ROWS-1)//ROWS)
    page = max(0,min(pages-1,getattr(game,'recap_page',0)))
    for i, value in enumerate(lines[page*ROWS:(page+1)*ROWS]):
        fitted = font
        size = 29
        while fitted.size(value)[0] > 820 and size > 23:
            size -= 1; fitted = pygame.font.Font(None,size)
        image = fitted.render(value, True, (243,236,216))
        clip = surface.get_clip();surface.set_clip((272,180+i*46,820,44))
        surface.blit(image,(272,184+i*46));surface.set_clip(clip)
    surface.blit(font.render(f'Page {page+1} / {pages}',True,(207,219,210)),(652,665))
    button(PREV,'Previous',page>0);button(NEXT,'Next',page+1<pages);button(CLOSE,'Back to table')
