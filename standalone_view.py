"""Existing poker presentation with standalone assets, portraits and sound adapters."""
from pathlib import Path
import pygame
import texas_holdem_ui as ui
from npc_portraits import draw_layered_portrait
ROOT=Path(__file__).resolve().parent

class TableView:
    def __init__(self,surface):
        self.surface=surface;self.portraits={};self.font=pygame.font.Font(None,28);self.cards={}
        for suit,letter in [('Clubs','C'),('Diamonds','D'),('Hearts','H'),('Spades','S')]:
            for rank in ['A','2','3','4','5','6','7','8','9','10','J','Q','K']:
                key=rank+letter;path=ROOT/'assets/cards/fronts'/f'{key}.png'
                if path.exists():self.cards[key]=pygame.image.load(path).convert_alpha()
                else:
                    # Fully functional native card faces when running without optional artwork.
                    card=pygame.Surface((150,210));card.fill((248,245,231));pygame.draw.rect(card,(40,40,40),card.get_rect(),3)
                    color=(188,37,38) if letter in 'DH' else (25,30,30)
                    card.blit(self.font.render(rank+' '+letter,True,color),(12,12));self.cards[key]=card
        path=ROOT/'assets/cards/backs/back_default.png'
        self.back=pygame.image.load(path).convert_alpha() if path.exists() else pygame.Surface((150,210))
        if not path.exists():self.back.fill((38,73,125));pygame.draw.rect(self.back,(236,221,167),self.back.get_rect().inflate(-16,-16),3)
        self.felt=pygame.Surface((1366,768));self.felt.fill((25,88,59))
    def background(self,overlay_alpha=0):self.surface.fill((20,42,35))
    def title(self,*args,**kwargs):pass  # The poker UI draws its own table heading.
    def button(self,rect,text,*args,**kwargs):
        pygame.draw.rect(self.surface,(42,85,64),rect);label=self.font.render(text,True,(246,240,218));self.surface.blit(label,label.get_rect(center=rect.center))
    def portrait(self,npc,rect,game=None):
        key=(npc.get('id'),rect.size)
        if key not in self.portraits:
            path=ROOT/str(npc.get('portrait',''))
            self.portraits[key]=pygame.image.load(path).convert_alpha() if path.is_file() else draw_layered_portrait(npc,rect.w)
        image=self.portraits[key]
        if image is not None:self.surface.blit(pygame.transform.smoothscale(image,rect.size),rect)
        else:
            pygame.draw.rect(self.surface,(43,74,68),rect,border_radius=8)
            initial=self.font.render(npc.get('name','?')[0],True,(242,229,192));self.surface.blit(initial,initial.get_rect(center=rect.center))
    def draw(self,table):
        ui.draw_texas_holdem(self.surface,pygame.mouse.get_pos(),table.game,self.cards,self.back,self.background,self.title,self.button,self.portrait,self.font,self.font,self.font,table.name,self.felt)
