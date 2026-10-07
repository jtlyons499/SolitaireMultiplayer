"""Solitaire Multiplayer foundation: standalone local Hold'em, LAN and room-code relay."""
import os
from pathlib import Path
import pygame
from standalone_table import StandaloneTable
from lan_session import OnlineTable
from standalone_view import TableView
import texas_holdem_ui as ui
from poker_recap import handle_recap_action

ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    pygame.init();screen=pygame.display.set_mode((1366,768),pygame.RESIZABLE)
    pygame.display.set_caption('Solitaire+ Poker Table — Multiplayer')
    canvas=pygame.Surface((1366,768));clock=pygame.time.Clock();font=pygame.font.Font(None,36)
    view=TableView(canvas);name='';address='127.0.0.1';room_code='';relay_address='127.0.0.1:50008';focus='name';table=None;running=True;pygame.key.start_text_input()
    sounds={}
    if pygame.mixer.get_init():
        for folder in ('assets/sounds','assets/sfx'):
            for path in (ROOT/folder).glob('*.wav'):
                try:sounds[path.stem]=pygame.mixer.Sound(path)
                except pygame.error:continue
    def sound(key):
        if key in sounds:sounds[key].play()
    name_rect=pygame.Rect(423,290,520,52);start_rect=pygame.Rect(183,460,300,60)
    host_rect=pygame.Rect(533,460,300,60);join_rect=pygame.Rect(883,460,300,60)
    address_rect=pygame.Rect(423,380,520,52);leave_rect=pygame.Rect(550,20,220,40);ready_rect=pygame.Rect(800,20,280,40)
    relay_rect=pygame.Rect(183,590,520,48);code_rect=pygame.Rect(723,590,460,48)
    create_rect=pygame.Rect(363,660,300,55);room_join_rect=pygame.Rect(703,660,300,55)
    while running:
        sx,sy=screen.get_size();scale=min(sx/1366,sy/768);offset=((sx-1366*scale)/2,(sy-768*scale)/2)
        raw=pygame.mouse.get_pos();mouse=((raw[0]-offset[0])/scale,(raw[1]-offset[1])/scale)
        for event in pygame.event.get():
            if event.type==pygame.QUIT:running=False;continue
            if table is None:
                if event.type==pygame.TEXTINPUT:
                    if focus=='name':name=(name+event.text)[:32]
                    elif focus=='address':address=(address+event.text)[:128]
                    elif focus=='relay':relay_address=(relay_address+event.text)[:128]
                    else:room_code=(room_code+event.text.upper())[:8]
                if event.type==pygame.KEYDOWN and event.key==pygame.K_BACKSPACE:
                    if focus=='name':name=name[:-1]
                    elif focus=='address':address=address[:-1]
                    elif focus=='relay':relay_address=relay_address[:-1]
                    else:room_code=room_code[:-1]
                if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                    if name_rect.collidepoint(mouse):focus='name'
                    elif address_rect.collidepoint(mouse):focus='address'
                    elif relay_rect.collidepoint(mouse):focus='relay'
                    elif code_rect.collidepoint(mouse):focus='code'
                    elif create_rect.collidepoint(mouse):table=OnlineTable(name,True,relay_address,relay=True)
                    elif room_join_rect.collidepoint(mouse):table=OnlineTable(name,False,relay_address,relay=True,code=room_code)
                    elif host_rect.collidepoint(mouse):table=OnlineTable(name,True)
                    elif join_rect.collidepoint(mouse):table=OnlineTable(name,False,address.strip() or '127.0.0.1')
                    elif start_rect.collidepoint(mouse):table=StandaloneTable(name)
                if event.type==pygame.KEYDOWN and event.key==pygame.K_RETURN:table=StandaloneTable(name)
                if table is not None:pygame.key.stop_text_input()
                continue
            online=isinstance(table,OnlineTable)
            if event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and leave_rect.collidepoint(mouse):
                if online:table.close()
                table=None;pygame.key.start_text_input();continue
            if online and not table.playable:
                if event.type==pygame.KEYDOWN and event.key==pygame.K_ESCAPE:
                    table.close();table=None;pygame.key.start_text_input()
                continue
            g=table.game
            if online and g.hand_complete and event.type==pygame.MOUSEBUTTONDOWN and event.button==1 and ready_rect.collidepoint(mouse):
                if not g.you_ready:table.act('next_hand')
                continue
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
                    
                    if isinstance(table,OnlineTable):table.close()
                    table=None;pygame.key.start_text_input()
                elif action.startswith('recap_'):handle_recap_action(g,action)
                elif table.act(action):sound('card_move')
        if table is None:
            canvas.fill((20,56,42))
            for text,y in [('SOLITAIRE+ POKER TABLE',150),('Your name',265),('Join address: localhost or the host’s LAN IP',355),('Relay address',560)]:
                label=font.render(text,True,(245,233,201));canvas.blit(label,label.get_rect(center=(443 if y==560 else 683,y)))
            label=font.render('Room code (joining only)',True,(245,233,201));canvas.blit(label,label.get_rect(center=(953,560)))
            for rect,value,field in ((name_rect,name,'name'),(address_rect,address,'address'),(relay_rect,relay_address,'relay'),(code_rect,room_code,'code')):
                pygame.draw.rect(canvas,(32,76,57),rect);pygame.draw.rect(canvas,(229,194,110) if focus==field else (130,166,145),rect,2)
                clip=canvas.get_clip();canvas.set_clip(rect.inflate(-12,-6))
                canvas.blit(font.render(value+('|' if focus==field else ''),True,(250,243,216)),(rect.x+15,rect.y+15));canvas.set_clip(clip)
            for rect,label in ((start_rect,'Local Practice'),(host_rect,'Host Table'),(join_rect,'Join LAN'),(create_rect,'Create Room'),(room_join_rect,'Join Room')):
                pygame.draw.rect(canvas,(54,107,76),rect,border_radius=10);image=font.render(label,True,(250,243,216));canvas.blit(image,image.get_rect(center=rect.center))
        else:
            online=isinstance(table,OnlineTable)
            if online or not ui.holdem_options_open:
                key=table.update(pygame.time.get_ticks())
                if key:sound(key)
            if not online or table.playable:
                ui.draw_texas_holdem(canvas,mouse,table.game,view.cards,view.back,view.background,view.title,view.button,view.portrait,font,font,font,table.name,view.felt)
            else:
                canvas.fill((20,56,42));label=font.render(table.status,True,(245,233,201));canvas.blit(label,label.get_rect(center=(683,320)))
                label=font.render('Share the room code and relay address with your friend.',True,(245,233,201));canvas.blit(label,label.get_rect(center=(683,385)))
            pygame.draw.rect(canvas,(65,96,77),leave_rect,border_radius=8);label=font.render('Leave table',True,(245,233,201));canvas.blit(label,label.get_rect(center=leave_rect.center))
            if online and table.playable and table.game.hand_complete:
                alive=sum(stack>0 for stack in [table.game.player_stack,*table.game.npc_stacks])
                text='Table finished' if alive<2 else f'Ready ({table.game.ready_count}/2)' if table.game.you_ready else 'Ready for next hand'
                pygame.draw.rect(canvas,(65,96,77),ready_rect,border_radius=8);image=pygame.font.Font(None,26).render(text,True,(245,233,201));canvas.blit(image,image.get_rect(center=ready_rect.center))
            if online:
                label=pygame.font.Font(None,22).render(table.status,True,(245,233,201));canvas.blit(label,(450,72))
        screen.fill((0,0,0));screen.blit(pygame.transform.smoothscale(canvas,(round(1366*scale),round(768*scale))),offset);pygame.display.flip();clock.tick(60)
    if isinstance(table,OnlineTable):table.close()
    pygame.key.stop_text_input();pygame.quit()

if __name__=='__main__':main()
