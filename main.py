"""Solitaire Multiplayer foundation: standalone local Hold'em, networking next."""
import os
from pathlib import Path
import pygame
from standalone_table import StandaloneTable
from standalone_view import TableView
import texas_holdem_ui as ui
from poker_recap import handle_recap_action

ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    pygame.init();screen=pygame.display.set_mode((1366,768),pygame.RESIZABLE)
    pygame.display.set_caption('Solitaire+ Poker Table — Local Starter')
    canvas=pygame.Surface((1366,768));clock=pygame.time.Clock();font=pygame.font.Font(None,36)
    view=TableView(canvas);name='';table=None;running=True;pygame.key.start_text_input()
    sounds={}
    if pygame.mixer.get_init():
        for folder in ('assets/sounds','assets/sfx'):
            for path in (ROOT/folder).glob('*.wav'):
                try:sounds[path.stem]=pygame.mixer.Sound(path)
                except pygame.error:continue
    def sound(key):
        if key in sounds:sounds[key].play()
    name_rect=pygame.Rect(423,300,520,60);start_rect=pygame.Rect(523,410,320,60)
    while running:
        sx,sy=screen.get_size();scale=min(sx/1366,sy/768);offset=((sx-1366*scale)/2,(sy-768*scale)/2)
        raw=pygame.mouse.get_pos();mouse=((raw[0]-offset[0])/scale,(raw[1]-offset[1])/scale)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False;continue
            if table is None:
                if event.type==pygame.TEXTINPUT:name=(name+event.text)[:32]
                if event.type==pygame.KEYDOWN and event.key==pygame.K_BACKSPACE:name=name[:-1]
                if (event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN) or (event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and start_rect.collidepoint(mouse)):
                    table=StandaloneTable(name);pygame.key.stop_text_input()
                continue
            g=table.game
            if event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:ui.holdem_options_open=not ui.holdem_options_open
                else:ui.handle_holdem_manual_bet_key(event,g)
            if event.type==pygame.MOUSEMOTION:ui.drag_holdem_bet_slider(mouse)
            if event.type==pygame.MOUSEBUTTONUP:ui.stop_holdem_bet_slider_drag()
            if event.type==pygame.MOUSEWHEEL:
                ui.holdem_log_scroll=max(0,ui.holdem_log_scroll-event.y)
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                if ui.handle_holdem_options_click(mouse) or ui.handle_holdem_panel_click(mouse):continue
                if ui.handle_holdem_manual_bet_click(mouse,g):continue
                if ui.update_holdem_bet_slider(mouse,g):continue
                action=ui.get_texas_holdem_action(mouse,g)
                if not action:continue
                if action=='options':ui.holdem_options_open=True
                elif action=='return' or (action=='next_hand' and table.finished):
                    table=None;pygame.key.start_text_input()
                elif action.startswith('recap_'):handle_recap_action(g,action)
                elif table.act(action):sound('card_move')
        if table is None:
            canvas.fill((20,56,42))
            for text,y in [('SOLITAIRE+ POKER TABLE',170),('Enter your name',250),('Local starter • You + 3 NPCs • $5,000 temporary chips',540)]:
                label=font.render(text,True,(245,233,201));canvas.blit(label,label.get_rect(center=(683,y)))
            pygame.draw.rect(canvas,(32,76,57),name_rect);pygame.draw.rect(canvas,(229,194,110),name_rect,2)
            canvas.blit(font.render(name+'|',True,(250,243,216)),(440,318))
            pygame.draw.rect(canvas,(54,107,76),start_rect,border_radius=10);label=font.render('Start Table',True,(250,243,216));canvas.blit(label,label.get_rect(center=start_rect.center))
        else:
            if not ui.holdem_options_open:
                key=table.update(pygame.time.get_ticks())
                if key:sound(key)
            # The old UI accepts a mouse argument; window scaling stays here.
            ui.draw_texas_holdem(canvas,mouse,table.game,view.cards,view.back,view.background,view.title,view.button,view.portrait,font,font,font,table.name,view.felt)
        screen.fill((0,0,0));screen.blit(pygame.transform.smoothscale(canvas,(round(1366*scale),round(768*scale))),offset);pygame.display.flip();clock.tick(60)
    pygame.key.stop_text_input();pygame.quit()

if __name__=='__main__':main()
