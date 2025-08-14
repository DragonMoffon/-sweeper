from uuid import uuid4
from enum import IntEnum
import random

import arcade
import pyglet

CHUNK_SIZE = 32
SQUARE_SIZE = 32
CHUNK_TOTAL_SIZE = CHUNK_SIZE * SQUARE_SIZE

class SpritePool:

    def __init__(self, count: int, default: arcade.Texture):
        self._count: int = count
        self._used: int = 0
        self._sprites: arcade.SpriteList = arcade.SpriteList(capacity=count)
        self._sprites.extend((arcade.BasicSprite(default, visible=False) for sprite in range(count)))
        
    @property
    def is_full(self):
        return self._used == self._count

    @property
    def is_empty(self):
        return self._used == 0

    def get(self):
        if self.is_full:
            raise IndexError("No more sprites available to free")

        sprite = self._sprites[self._used]
        sprite.visible = True
        self._used += 1
        return sprite

    def free(self, sprite: arcade.BasicSprite):
        if self.is_empty:
            raise IndexError("There are no sprites in use")

        idx = self._sprites.index(sprite)
        if idx >= self._used:
            raise IndexError("attempting to free already free sprite")
        self._used -= 1
        self._sprites.swap(idx, self._used)
        sprite.visible = False

    def draw(self):
        self._sprites.draw(pixelated=True)


class Tile(IntEnum):
    empty = 0
    bomb = 1
    shown = 2
    shown_bomb = 3
    flag = 4 
    flag_bomb = 5

class Chunk:

    def __init__(self, pos: tuple[int, int], size: int, square: int, mine_density: float, seed: str):
        self.x: int = pos[0]
        self.y: int = pos[1]
        self.size: int = size
        self.density: float = mine_density
        self.square_size: int = square
        self.total_px_size: int = size * square
        self.seed: str = seed
        
        self._tiles: list[list[Tile]] = None

    @property
    def is_generated(self) -> bool:
        return self.tiles is not Nonei
        
    @property
    def bomb_count(self) -> int:
        return int(self.size * self.size * self.density)
                    
    def get_tiles(self) -> list[list[Tile]]:
        if self._tiles is not None:
            return self._tiles

        self._tiles = [[Tile.empty] * self.size for _ in range(self.size)]
        free_indices = [(x, y) for x in range(self.size) for y in range(self.size)]
        random.seed(hash(self.seed))
        for bomb_location in random.sample(free_indices, self.bomb_count):
            self._tiles[bomb_location[0]][bomb_location[1]] = Tile.bomb

        return self._tiles

    def to_local_coord(self, pos):
        x_ = int(pos[0] - self.size * self.x)
        y_ = int(pos[1] - self.size * self.y)
        return (x_, y_)

    def to_global_coord(self, pos):
        x_ = int(pos[0] + self.size * self.x)
        y_ = int(pos[1] + self.size * self.y)
        return (x_, y_)

class Application(arcade.Window):

    def __init__(self, seed: str):
        arcade.Window.__init__(self, 800, 800, "∞-Sweeper", vsync=False)
        self.seed = seed
        self.frame_camera = arcade.Camera2D()
        self.game_camera = arcade.Camera2D(arcade.LBWH(30, 30, 740, 740))
        
        textures = arcade.load_spritesheet("sweep/tiles.png").get_texture_grid((SQUARE_SIZE, SQUARE_SIZE), 12, 12)
        self.textures: dict[str, arcade.Texture] = {name: tex for name, tex in zip("efb012345678", textures)}

        self.chunks: dict[tuple[int, int], Chunk] = {}
        self.shown_chunks: dict[tuple[int, int], tuple(arcade.Sprite)] = {}
        self.last_chunks: tuple[tuple[int, int], ...] = ((0, 0),)
        self.sprites: SpritePool = SpritePool(9 * CHUNK_SIZE * CHUNK_SIZE, self.textures['e'])

        self.dragged: bool = False

        self.show_chunk((0, 0))

    def tile_texture(self, tile, coord):
        if tile == Tile.empty: # Empty
            return self.textures['e']
        elif tile == Tile.bomb: # Bomb
            return self.textures['b']
        elif tile == Tile.shown: # Shown
            count = self.get_tile_count(coord)
            return self.textures[str(count)]
        elif tile & 0b100: # flag
            return self.textures['f']

    def get_chunk(self, pos):
        if pos not in self.chunks:
            self.chunks[pos] = Chunk(pos, CHUNK_SIZE, SQUARE_SIZE, 0.25, self.seed)

        return self.chunks[pos]
    
    def hide_chunk(self, chunk: tuple[int, int]):
        if chunk not in self.shown_chunks:
            return

        sprites = self.shown_chunks.pop(chunk)
        for sprite in sprites:
            self.sprites.free(sprite)

    def show_chunk(self, chunk: tuple[int, int]):
        if chunk in self.shown_chunks or len(self.shown_chunks) >= 9:
            return

        chunk_data = self.get_chunk(chunk)
        tiles = chunk_data.get_tiles()
        sprites = []
        for x, column in enumerate(tiles):
            for y, tile in enumerate(column):
                coord = chunk_data.to_global_coord((x, y))
                sprite = self.sprites.get()
                sprite.position = (coord[0] + 0.5) * SQUARE_SIZE, (coord[1] + 0.5) * SQUARE_SIZE
                sprite.texture = self.tile_texture(tile, coord)
                sprites.append(sprite)
        self.shown_chunks[chunk] = tuple(sprites)

    def change_chunk(self, old: tuple[int, int], new: tuple[int, int]):
        if new in self.shown_chunks:
            return
        if old not in self.shown_chunks:
            self.show_chunk(new)
            return
        
        sprites = self.shown_chunks.pop(old)
        chunk = self.get_chunk(new)
        tiles = chunk.get_tiles()
        for x, column in enumerate(tiles):
            for y, tile in enumerate(column):
                idx = x * chunk.size + y
                coord = chunk.to_global_coord((x, y))
                sprite = sprites[idx]
                sprite.position = (coord[0] + 0.5) * SQUARE_SIZE, (coord[1] + 0.5) * SQUARE_SIZE
                sprite.texture = self.tile_texture(tile, coord)

    def get_tile(self, pos):
        cx = pos[0] // CHUNK_SIZE
        cy = pos[1] // CHUNK_SIZE
        chunk = self.get_chunk((cx, cy))
        pos = chunk.to_local_coord(pos)
        return chunk.get_tiles()[pos[0]][pos[1]]

    def get_tile_count(self, pos):
        count = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                tile = self.get_tile((pos[0]+dx, pos[1]+dy))
                if tile & 0b001:
                    count += 1
        return count

    def toggle_flag(self, pos):
        cx = pos[0] // CHUNK_SIZE
        cy = pos[1] // CHUNK_SIZE
        chunk = self.get_chunk((cx, cy))
        tiles = chunk.get_tiles()
        pos_ = chunk.to_local_coord(pos)
        tile = Tile(tiles[pos_[0]][pos_[1]] ^ 0b100)
        tiles[pos_[0]][pos_[1]] = tile
        if (cx, cy) not in self.shown_chunks:
            return
        idx = pos_[0] * chunk.size + pos_[1]
        sprite = self.shown_chunks[cx, cy][idx].texture = self.tile_texture(tile, pos)

    def show_tile(self, pos):
        cx = pos[0] // CHUNK_SIZE
        cy = pos[1] // CHUNK_SIZE
        chunk = self.get_chunk((cx, cy))
        tiles = chunk.get_tiles()
        tile = chunk
        
    def find_shown_chunks(self):
        l, b = self.game_camera.bottom_left
        r, t = self.game_camera.top_right
        cl, cr, cb, ct = l // CHUNK_TOTAL_SIZE, r // CHUNK_TOTAL_SIZE, b // CHUNK_TOTAL_SIZE, t // CHUNK_TOTAL_SIZE
        return tuple((x, y) for x in range(int(cl), int(cr) + 1) for y in range(int(cb), int(ct) + 1))

    def show_chunks(self, chunks: tuple[tuple[int, int], ...]):
        previous = self.shown_chunks
        old = [chunk for chunk in previous if chunk not in chunks]
        new = [chunk for chunk in chunks if chunk not in previous]
       
        if not old and not new:
            return
        
        for chunk in old:
            if not new:
                self.hide_chunk(chunk)
            else:
                self.change_chunk(chunk, new.pop(-1))
        
        for chunk in new:
            self.show_chunk(chunk)


    def on_draw(self):
        self.clear()
        with self.frame_camera.activate():
            arcade.draw_text(
                f"chunks created: {len(self.chunks)}", 5, 5, font_name="monofur"
            )
            arcade.draw_text(
                f"fps: {1/self.delta_time:.3f}", self.width/2, 5, font_name="monofur", anchor_x="center"
            )
            arcade.draw_text(
                f"seed: {self.seed}", self.width - 5, 5, font_name="monofur", anchor_x="right"
            )

        with self.game_camera.activate():
            chunks = self.find_shown_chunks()
            if chunks != self.last_chunks:
                self.last_chunks = chunks
                self.show_chunks(chunks)
            self.sprites.draw()

    def on_mouse_drag(self, x, y, dx, dy, symbol, modifier):
        self.dragged = True
        pos = self.game_camera.position
        zoom = self.game_camera.zoom
        self.game_camera.position = pos[0] - dx / zoom, pos[1] - dy / zoom

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        self.game_camera.zoom = min(
            4.0, max(0.5, self.game_camera.zoom - scroll_y * 0.1)
        )

    def on_mouse_release(self, x, y, symbol, modifier):
        if not self.dragged:
            pos = self.game_camera.unproject((x, y)) // SQUARE_SIZE
            self.toggle_flag((int(pos.x), int(pos.y)))
        self.dragged = False

def main():
    seed = input("enter game seed (leave blank for random): ")
    if not seed:
        seed = uuid4().hex

    win = Application(seed)
    win.run()


if __name__ == "__main__":
    main()

