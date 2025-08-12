from uuid import uuid4
import random

import arcade
import pyglet

import cProfile
from time import time_ns

CHUNK_SIZE = 32
SQUARE_SIZE = 32
CHUNK_TOTAL_SIZE = CHUNK_SIZE * SQUARE_SIZE

class _Context:

    def __init__(self):
        self._seed: str | None = None
        self._seed_hash: int | None = None
        self._tile_textures: dict[str, arcade.Texture] = {}
        self._chunk_renderer: arcade.SpriteList = arcade.SpriteList(capacity = 9 * CHUNK_SIZE * CHUNK_SIZE)

    def get_seed_source(self) -> str:
        if self._seed is None:
            raise ValueError('Seed has not been set.')
        return self._seed

    def get_seed(self) -> int:
        if self._seed is None:
            raise ValueError('Seed has not been set.')
        return self._seed_hash

    def set_seed(self, seed: str) -> None:
        self._seed = seed
        self._seed_hash = hash(seed)

    def load_spritesheet(self, path: str):
        sheet = arcade.SpriteSheet(path)
        self._tile_textures['grass'] = sheet.get_texture(arcade.LBWH(SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['flag'] = sheet.get_texture(arcade.LBWH(2*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['0'] = sheet.get_texture(arcade.LBWH(0, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['1'] = sheet.get_texture(arcade.LBWH(3*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['2'] = sheet.get_texture(arcade.LBWH(4*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['3'] = sheet.get_texture(arcade.LBWH(5*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['4'] = sheet.get_texture(arcade.LBWH(6*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['5'] = sheet.get_texture(arcade.LBWH(7*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['6'] = sheet.get_texture(arcade.LBWH(8*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['7'] = sheet.get_texture(arcade.LBWH(9*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))
        self._tile_textures['8'] = sheet.get_texture(arcade.LBWH(10*SQUARE_SIZE, 0, SQUARE_SIZE, SQUARE_SIZE))

    def get_texture(self, name: str):
        return self._tile_textures[name]

    def show_sprites(self, sprites: list[arcade.Sprite]):
        self._chunk_renderer.extend(sprites)

    def hide_sprites(self):
        self._chunk_renderer.clear()

    def draw_sprites(self):
        self._chunk_renderer.draw(pixelated=True)

ctx = _Context()


class Chunk:

    def __init__(self, x: int, y: int, size: int, square: int, mine_density: float):
        self.x: int = x
        self.y: int = y
        self.size: int = size
        self.density: float = mine_density
        self.square_size: int = square
        self.total_px_size: int = size * square
        
        self._has_generated: bool = False
        self._has_counted: bool = False
        self._is_shown: bool = False

        self._bombs: list[list[bool]] = []
        self._flags: list[list[bool]] = []
        self._shown: list[list[bool]] = []
        self._count: list[list[int]] = []
        self._sprites: list[arcade.Sprite] = []

    def get_sprites(self):
        if not self._sprites:
            chunk_x = self.x * self.total_px_size
            chunk_y = self.y * self.total_px_size
            sq_sz = self.square_size
            self._sprites = [None] * (self.size*self.size)
            for x in range(self.size):
                for y in range(self.size):
                    idx = x * self.size + y
                    self._sprites[idx] = arcade.Sprite(ctx.get_texture("grass"), chunk_x + (x + 0.5) * sq_sz, chunk_y + (y + 0.5) * sq_sz)
        return self._sprites

    def place_bombs(self):
        self._bombs: list[list[bool]] = [[False] * size for _ in range(size)]
        self._flags: list[list[bool]] = [[False] * size for _ in range(size)]
        self._shown: list[list[bool]] = [[False] * size for _ in range(size)]
        self._count: list[list[int]] = [[0] * size for _ in range(size)]
        
        random.seed(ctx.get_seed())
        safe_squares = [(x, y) for x in range(size) for y in range(size)]
        for _ in range(self.count):
            bomb_idx = random.randrange(0, len(safe_squares))
            bomb = safe_squares.pop(bomb_idx)
            self._bombs[bomb[0]][bomb[1]] = True

        self._has_generated: bool = True

    def count_bombs(self):
        pass

    @property
    def count(self) -> int:
        return int(self.size * self.size * self.density)
                    


class Application(arcade.Window):

    def __init__(self):
        arcade.Window.__init__(self, 800, 800, "∞-Sweeper", vsync=False)
        ctx.load_spritesheet('./sweep/tiles.png')
        self.frame_camera = arcade.Camera2D()
        self.game_camera = arcade.Camera2D(arcade.LBWH(30, 30, 740, 740))
        self.chunks: dict[tuple[int, int], Chunk] = {}
        self.shown_chunks: tuple[tuple[int, int], ...] = ()

    def get_chunk(self, x: int, y: int):
        if (x, y) not in self.chunks:
            self.chunks[x, y] = Chunk(x, y, CHUNK_SIZE, SQUARE_SIZE, 0.2)

        return self.chunks[x, y]

    def _dispatch_frame(self, delta_time: float):
        s = time_ns()
        super()._dispatch_frame(delta_time)
        e = time_ns()
        print(f'frame_time: {s*1e-9}s -> {e*1e-9}s; {(e-s)*1e-6}ms')

    def _dispatch_updates(self, delta_time: float):
        s = time_ns()
        super()._dispatch_updates(delta_time)
        e = time_ns()
        print(f'update time: {s*1e-9}s -> {e*1e-9}s; {(e-s)*1e-6}ms')


    def on_update(self, delta_time: float):
        print(1/delta_time)

    def on_draw(self):
        s = time_ns()
        self.clear()
        with self.frame_camera.activate():
            arcade.draw_text(
                f"chunks created: {len(self.chunks)}", 5, 5, font_name="monofur"
            )
            arcade.draw_text(
                f"seed: {ctx.get_seed_source()}", self.width - 5, 5, font_name="monofur", anchor_x="right"
            )

        with self.game_camera.activate():
            l, b = self.game_camera.bottom_left
            r, t = self.game_camera.top_right

            l, r = int(l // CHUNK_TOTAL_SIZE), int(r // CHUNK_TOTAL_SIZE)
            b, t = int(b // CHUNK_TOTAL_SIZE), int(t // CHUNK_TOTAL_SIZE)
            chunks = tuple((x, y) for x in range(l, r+1) for y in range(b, t+1))
            if chunks != self.shown_chunks:
                print('renew')
                self.shown_chunks = chunks
                ctx.hide_sprites()
                for coord in chunks:
                    chunk = self.get_chunk(coord[0], coord[1])
                    ctx.show_sprites(chunk.get_sprites())
            s2 = time_ns()
            ctx.draw_sprites()
            e2 = time_ns()
            print(f'chunk time: {s2*1e-9}s -> {e2*1e-9}s; {(e2-s2) * 1e-6}ms')
        e = time_ns()
        print(f'draw_time: {s*1e-9}s -> {e*1e-9}s; {(e - s) * 1e-6}ms')

    def on_mouse_drag(self, x, y, dx, dy, symbol, modifier):
        pos = self.game_camera.position
        zoom = self.game_camera.zoom
        self.game_camera.position = pos[0] - dx / zoom, pos[1] - dy / zoom

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.game_camera.zoom = min(
            4.0, max(0.5, self.game_camera.zoom - scroll_y * 0.1)
        )


def main():
    seed = input("enter game seed (leave blank for random): ")
    if not seed:
        seed = uuid4().hex
    ctx.set_seed(hash(seed))

    win = Application()
    win.run()


if __name__ == "__main__":
    with cProfile.Profile() as pr:
        main()

        # pr.print_stats('cumulative')

