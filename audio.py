import random
import pygame


class AudioManager:
    def __init__(self):
        pygame.mixer.init()

        # ----------------------------
        # Volume
        # ----------------------------

        self.instrumental_gain = 0.10
        self.ambient_gain = 0.4

        self.music_volume = 0.5
        self.sfx_volume = 1

        # ----------------------------
        # Sound effects
        # ----------------------------

        self.sounds = {}

        # ----------------------------
        # Music playlists
        # ----------------------------

        self.playlists = {}

        self.music_mode = "instrumental"

        self.current_track = None
        self.current_playlist = []

        # Used so every song plays before
        # reshuffling the playlist
        self.music_queue = []

        # Custom pygame event fired
        # when a song finishes
        self.MUSIC_END_EVENT = pygame.USEREVENT + 1

        pygame.mixer.music.set_endevent(
            self.MUSIC_END_EVENT
        )

    # ==================================================
    # SOUND EFFECTS
    # ==================================================

    def load_sound(self, name, path):
        sound = pygame.mixer.Sound(path)

        sound.set_volume(
            self.sfx_volume
        )

        self.sounds[name] = sound

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].play()

    # ==================================================
    # MUSIC PLAYLISTS
    # ==================================================

    def add_playlist(
        self,
        name,
        tracks,
        startup_track=None
    ):
        self.playlists[name] = {
            "tracks": tracks,
            "startup_track": startup_track
        }

    def set_music_mode(self, mode):

        if (
                mode == self.music_mode
                and pygame.mixer.music.get_busy()
        ):
            return
        # Stop current music first
        pygame.mixer.music.stop()

        self.music_mode = mode
        self.current_track = None
        self.music_queue = []

        # No music
        if mode == "off":
            return

        if mode not in self.playlists:
            return

        playlist_data = self.playlists[mode]

        self.current_playlist = (
            playlist_data["tracks"]
        )

        startup_track = (
            playlist_data["startup_track"]
        )

        # Play designated starting song
        if startup_track:
            self.play_music_track(
                startup_track
            )

            self.build_music_queue(
                exclude=startup_track
            )

        # Otherwise start with shuffled music
        else:
            self.build_music_queue()
            self.play_next_track()

    def build_music_queue(
        self,
        exclude=None
    ):
        self.music_queue = [
            track
            for track in self.current_playlist
            if track != exclude
        ]

        random.shuffle(
            self.music_queue
        )

    def play_music_track(self, path):
        pygame.mixer.music.load(path)

        volume = self.music_volume

        if self.music_mode == "instrumental":
            volume *= self.instrumental_gain

        elif self.music_mode == "ambient":
            volume *= self.ambient_gain

        pygame.mixer.music.set_volume(volume)

        pygame.mixer.music.play()

        self.current_track = path

    def play_next_track(self):
        if self.music_mode == "off":
            return

        if not self.current_playlist:
            return

        # Once every track has played,
        # create another shuffled rotation
        if not self.music_queue:
            self.build_music_queue(
                exclude=self.current_track
            )

        if not self.music_queue:
            return

        next_track = self.music_queue.pop(0)

        self.play_music_track(
            next_track
        )

    # ==================================================
    # EVENTS
    # ==================================================

    def handle_event(self, event):
        if event.type == self.MUSIC_END_EVENT:
            self.play_next_track()

    def update(self):
        if self.music_mode == "off":
            return

        if not self.current_playlist:
            return

        if not pygame.mixer.music.get_busy():
            self.play_next_track()

    # ==================================================
    # VOLUME
    # ==================================================

    def set_music_volume(self, volume):
        self.music_volume = max(
            0.0,
            min(volume, 1.0)
        )

        adjusted_volume = self.music_volume

        if self.music_mode == "instrumental":
            adjusted_volume *= self.instrumental_gain

        elif self.music_mode == "ambient":
            adjusted_volume *= self.ambient_gain

        pygame.mixer.music.set_volume(
            adjusted_volume
        )

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(
            0.0,
            min(volume, 1.0)
        )

        for sound in self.sounds.values():
            sound.set_volume(
                self.sfx_volume
            )