import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY, TRAP = 0, 1, 2, 3, 4
SPEED = 3
GUARD_SPEED = 2

def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []

    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)

        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)

        if not overlap:
            rooms.append(room)

            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery

        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            cx += 1 if bx > cx else -1

        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            cy += 1 if by > cy else -1

    guard_points = None

    if len(rooms) >= 2:
        cr, ck = rooms[-1], rooms[-2]

        chest_pos = (cr.centerx, cr.centery)
        key_pos = (ck.centerx, ck.centery)

        grid[chest_pos[1]][chest_pos[0]] = CHEST
        grid[key_pos[1]][key_pos[0]] = KEY

        # Add traps to random floor cells.
        trap_candidates = []

        for r in range(ROWS):
            for c in range(COLS):
                if grid[r][c] == FLOOR:
                    if rooms[0].collidepoint(c, r):
                        continue

                    if (c, r) == key_pos or (c, r) == chest_pos:
                        continue

                    trap_candidates.append((c, r))

        trap_count = min(6, len(trap_candidates))

        for c, r in random.sample(trap_candidates, trap_count):
            grid[r][c] = TRAP

        # Find two safe floor positions near the chest for the guard.
        guard_candidates = []

        for r in range(
            max(0, cr.top),
            min(ROWS, cr.bottom)
        ):
            for c in range(
                max(0, cr.left),
                min(COLS, cr.right)
            ):
                if grid[r][c] == FLOOR:
                    guard_candidates.append((c, r))

        # Prefer two positions on the same row.
        rows_with_positions = {}

        for c, r in guard_candidates:
            rows_with_positions.setdefault(r, []).append(c)

        for r, positions in rows_with_positions.items():
            positions.sort()

            if len(positions) >= 2:
                guard_points = (
                    (positions[0], r),
                    (positions[-1], r)
                )
                break

        # Fallback: use two safe floor positions if needed.
        if guard_points is None and len(guard_candidates) >= 2:
            guard_points = (
                guard_candidates[0],
                guard_candidates[-1]
            )

    start = rooms[0] if rooms else None

    return grid, start, guard_points


COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    TRAP: (180,60,60),
}


class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx = dy = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -SPEED

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = SPEED

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy = -SPEED

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy = SPEED

        self._try_move(dx, 0, grid, rows, cols)
        self._try_move(0, dy, grid, rows, cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx, dy)

        for px, py in [
            (new.left, new.top),
            (new.right-1, new.top),
            (new.left, new.bottom-1),
            (new.right-1, new.bottom-1)
        ]:
            c, r = px//TILE, py//TILE

            if not(0 <= r < rows and 0 <= c < cols) or grid[r][c] == WALL:
                return

        self.rect = new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)

        if self.has_key:
            pygame.draw.circle(
                screen,
                (220,220,60),
                (self.rect.right-6, self.rect.top+6),
                5
            )


class Guard:
    def __init__(self, point_a, point_b):
        self.point_a = pygame.Vector2(
            point_a[0] * TILE + 6,
            point_a[1] * TILE + 6
        )

        self.point_b = pygame.Vector2(
            point_b[0] * TILE + 6,
            point_b[1] * TILE + 6
        )

        self.position = self.point_a.copy()
        self.rect = pygame.Rect(
            int(self.position.x),
            int(self.position.y),
            28,
            28
        )

        self.direction = 1
        self.speed = GUARD_SPEED
        self.color = (190, 50, 50)

    def update(self):
        target = self.point_b if self.direction == 1 else self.point_a

        direction = target - self.position

        if direction.length() <= self.speed:
            self.position = target.copy()
            self.direction *= -1
        else:
            self.position += direction.normalize() * self.speed

        self.rect.topleft = (
            round(self.position.x),
            round(self.position.y)
        )

    def draw(self, screen):
        pygame.draw.rect(
            screen,
            self.color,
            self.rect,
            border_radius=6
        )

        # Draw simple eyes to distinguish the guard.
        pygame.draw.circle(
            screen,
            (255,255,255),
            (self.rect.left + 8, self.rect.top + 9),
            3
        )

        pygame.draw.circle(
            screen,
            (255,255,255),
            (self.rect.left + 20, self.rect.top + 9),
            3
        )


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60


class GameEngine:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")

        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)

        self.reset()

    def reset(self):
        self.grid, start, guard_points = generate_world()

        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6

        self.player_start = (sx, sy)

        self.player = Player(sx, sy)

        self.guard = None

        if guard_points:
            self.guard = Guard(
                guard_points[0],
                guard_points[1]
            )

        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.reset()

        return True

    def update(self):
        if self.won:
            return

        keys = pygame.key.get_pressed()

        self.player.move(
            keys,
            self.grid,
            ROWS,
            COLS
        )

        # Move the guard every frame.
        if self.guard:
            self.guard.update()

            # Check whether the player touched the guard.
            if self.player.rect.colliderect(self.guard.rect):
                self.player.rect.topleft = self.player_start
                self.status = "Guard caught you! Back to start!"

        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE

        if 0 <= pr < ROWS and 0 <= pc < COLS:
            cell = self.grid[pr][pc]

            if cell == TRAP:
                self.player.rect.topleft = self.player_start
                self.status = "Trap! Back to start!"

            elif cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"

            elif cell == CHEST and self.player.has_key:
                self.won = True
                self.status = "Treasure found!"

    def draw(self):
        self.screen.fill((30,25,40))

        for r in range(ROWS):
            for c in range(COLS):

                cell = self.grid[r][c]

                rect = pygame.Rect(
                    c*TILE,
                    r*TILE,
                    TILE,
                    TILE
                )

                pygame.draw.rect(
                    self.screen,
                    COLORS[cell],
                    rect
                )

                if cell == KEY:
                    pygame.draw.circle(
                        self.screen,
                        (255,240,60),
                        (
                            c*TILE+TILE//2,
                            r*TILE+TILE//2
                        ),
                        10
                    )

                elif cell == CHEST:
                    pygame.draw.rect(
                        self.screen,
                        (180,120,20),
                        rect.inflate(-12,-12),
                        border_radius=4
                    )

                elif cell == TRAP:
                    pygame.draw.line(
                        self.screen,
                        (255,220,220),
                        (c*TILE+10, r*TILE+10),
                        (c*TILE+30, r*TILE+30),
                        4
                    )

                    pygame.draw.line(
                        self.screen,
                        (255,220,220),
                        (c*TILE+30, r*TILE+10),
                        (c*TILE+10, r*TILE+30),
                        4
                    )

        if self.guard:
            self.guard.draw(self.screen)

        self.player.draw(self.screen)

        hud = pygame.Rect(
            0,
            ROWS*TILE,
            WIDTH,
            50
        )

        pygame.draw.rect(
            self.screen,
            (20,20,35),
            hud
        )

        st = self.font.render(
            self.status + "  |  R=Restart",
            True,
            (200,200,200)
        )

        self.screen.blit(
            st,
            (8,ROWS*TILE+13)
        )

        if self.won:
            ov = pygame.Surface(
                (WIDTH,ROWS*TILE),
                pygame.SRCALPHA
            )

            ov.fill((0,0,0,140))

            self.screen.blit(
                ov,
                (0,0)
            )

            msg = self.big_font.render(
                "TREASURE FOUND!",
                True,
                (220,180,30)
            )

            sub = self.font.render(
                "Press R to Play Again",
                True,
                (180,180,180)
            )

            self.screen.blit(
                msg,
                (
                    WIDTH//2-msg.get_width()//2,
                    ROWS*TILE//2-30
                )
            )

            self.screen.blit(
                sub,
                (
                    WIDTH//2-sub.get_width()//2,
                    ROWS*TILE//2+20
                )
            )

        pygame.display.flip()

    def run(self):
        running = True

        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()


if __name__ == "__main__":
    engine = GameEngine()
    engine.run()