import os
import json
import random
import pygame

pygame.init()

# =========================
# 기본 설정
# =========================
WIDTH = 20
HEIGHT = 15
SIZE = 50
NUM_OF_BOMBS = 40
FPS = 60

EXPLOSION_WAVE_DELAY = 70       # 바깥으로 1칸 번질 때마다 지연(ms)
EXPLOSION_STAGE1_DURATION = 180 # 1차 폭발 이미지 표시 시간(ms)
EXPLOSION_POPUP_EXTRA_DELAY = 180

TOP_UI_HEIGHT = 70
SCREEN_WIDTH = WIDTH * SIZE
SCREEN_HEIGHT = HEIGHT * SIZE + TOP_UI_HEIGHT

EMPTY = 0
BOMB = 1

CLOSED = 0
OPENED = 1
FLAGGED = 2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORD_FILE = os.path.join(BASE_DIR, "mine_records.json")

# =========================
# 화면 설정
# =========================
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("지뢰찾기")
clock = pygame.time.Clock()

# =========================
# 폰트
# =========================
font = pygame.font.SysFont("malgungothic", 28)
small_font = pygame.font.SysFont("malgungothic", 20)
tiny_font = pygame.font.SysFont("malgungothic", 16)
big_font = pygame.font.SysFont("malgungothic", 40)

# =========================
# 이미지 불러오기
# 코드와 같은 폴더 기준
# =========================
def load_image(filename, size):
    path = os.path.join(BASE_DIR, filename)
    image = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(image, size)


img_closed = load_image("기본블럭.png", (SIZE, SIZE))
img_opened = load_image("눌림블럭.png", (SIZE, SIZE))
img_flag = load_image("우측클릭.png", (SIZE, SIZE))

img_bomb_stage1 = load_image("폭탄터짐1차.png", (SIZE, SIZE))
img_bomb_stage2 = load_image("폭탄터짐2차.png", (SIZE, SIZE))

number_imgs = {}
for i in range(1, 9):
    number_imgs[i] = load_image(f"{i}.png", (SIZE, SIZE))

# =========================
# 버튼 클래스
# =========================
class Button:
    def __init__(self, x, y, w, h, text, bg=(230, 230, 230), fg=(0, 0, 0)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.bg = bg
        self.fg = fg

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg, self.rect, border_radius=8)
        pygame.draw.rect(surface, (30, 30, 30), self.rect, 2, border_radius=8)
        txt = small_font.render(self.text, True, self.fg)
        txt_rect = txt.get_rect(center=self.rect.center)
        surface.blit(txt, txt_rect)

    def collidepoint(self, pos):
        return self.rect.collidepoint(pos)

# =========================
# 기록 저장/불러오기
# =========================
def load_records():
    if not os.path.exists(RECORD_FILE):
        return []

    try:
        with open(RECORD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_records(records):
    with open(RECORD_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def add_record(name, play_time, result_text):
    records = load_records()
    records.append({
        "name": name.strip() if name.strip() else "이름없음",
        "time": round(play_time, 2),
        "result": result_text
    })
    save_records(records)


def get_sorted_records():
    records = load_records()

    def sort_key(item):
        result_priority = 0 if item.get("result") == "클리어" else 1
        time_value = item.get("time", 999999.0)
        name_value = item.get("name", "")
        return (result_priority, time_value, name_value)

    return sorted(records, key=sort_key)

# =========================
# 게임 데이터
# =========================
field = []
state = []

game_over = False
game_clear = False
paused = False

show_help = False
show_end_popup = False
show_record_input = False
show_rank_popup = False

first_click = True
opened_safe_count = 0

exploded_pos = None
explosion_start_time = None
max_explosion_distance = 0

start_ticks = None
paused_total_ms = 0
pause_started_ms = 0
final_time = 0.0

input_name = ""
record_saved = False
help_opened_pause = False
rank_opened_pause = False

# =========================
# 상단 버튼
# =========================
btn_restart = Button(20, 15, 70, 40, "RE")
btn_pause = Button(100, 15, 90, 40, "ESC")
btn_help = Button(200, 15, 100, 40, "도움말")
btn_rank = Button(310, 15, 100, 40, "랭킹")

# =========================
# 함수들
# =========================
def reset_game():
    global field, state
    global game_over, game_clear, paused
    global show_help, show_end_popup, show_record_input, show_rank_popup
    global first_click, opened_safe_count
    global exploded_pos, explosion_start_time, max_explosion_distance
    global start_ticks, paused_total_ms, pause_started_ms
    global final_time, input_name, record_saved
    global help_opened_pause, rank_opened_pause

    field = [[EMPTY for _ in range(WIDTH)] for _ in range(HEIGHT)]
    state = [[CLOSED for _ in range(WIDTH)] for _ in range(HEIGHT)]

    game_over = False
    game_clear = False
    paused = False

    show_help = False
    show_end_popup = False
    show_record_input = False
    show_rank_popup = False

    first_click = True
    opened_safe_count = 0

    exploded_pos = None
    explosion_start_time = None
    max_explosion_distance = 0

    start_ticks = None
    paused_total_ms = 0
    pause_started_ms = 0
    final_time = 0.0

    input_name = ""
    record_saved = False
    help_opened_pause = False
    rank_opened_pause = False


def toggle_pause():
    global paused, pause_started_ms, paused_total_ms

    if game_over or game_clear:
        return

    if not paused:
        paused = True
        pause_started_ms = pygame.time.get_ticks()
    else:
        paused = False
        paused_total_ms += pygame.time.get_ticks() - pause_started_ms


def open_help_popup():
    global show_help, help_opened_pause

    if show_help:
        return

    show_help = True
    help_opened_pause = False

    if not paused and not game_over and not game_clear:
        toggle_pause()
        help_opened_pause = True


def close_help_popup():
    global show_help, help_opened_pause

    show_help = False

    if help_opened_pause and paused:
        toggle_pause()

    help_opened_pause = False


def open_rank_popup():
    global show_rank_popup, rank_opened_pause

    if show_rank_popup:
        return

    show_rank_popup = True
    rank_opened_pause = False

    if not paused and not game_over and not game_clear:
        toggle_pause()
        rank_opened_pause = True


def close_rank_popup():
    global show_rank_popup, rank_opened_pause

    show_rank_popup = False

    if rank_opened_pause and paused:
        toggle_pause()

    rank_opened_pause = False


def get_elapsed_time():
    if first_click or start_ticks is None:
        return 0.0

    now = pygame.time.get_ticks()

    if paused:
        elapsed_ms = pause_started_ms - start_ticks - paused_total_ms
    else:
        elapsed_ms = now - start_ticks - paused_total_ms

    return max(0.0, elapsed_ms / 1000.0)


def in_range(x, y):
    return 0 <= x < WIDTH and 0 <= y < HEIGHT


def place_bombs(exclude_x, exclude_y):
    """
    첫 클릭 칸 + 주변 8칸은 안전 구역으로 처리
    """
    safe_zone = set()

    for yoff in range(-1, 2):
        for xoff in range(-1, 2):
            nx = exclude_x + xoff
            ny = exclude_y + yoff
            if in_range(nx, ny):
                safe_zone.add((nx, ny))

    count = 0
    while count < NUM_OF_BOMBS:
        x = random.randint(0, WIDTH - 1)
        y = random.randint(0, HEIGHT - 1)

        if (x, y) in safe_zone:
            continue

        if field[y][x] != BOMB:
            field[y][x] = BOMB
            count += 1


def num_of_bomb(x_pos, y_pos):
    count = 0
    for yoff in range(-1, 2):
        for xoff in range(-1, 2):
            if xoff == 0 and yoff == 0:
                continue

            nx = x_pos + xoff
            ny = y_pos + yoff

            if in_range(nx, ny) and field[ny][nx] == BOMB:
                count += 1

    return count


def open_tile(x, y):
    """
    0칸이면 주변을 계속 열고,
    숫자칸이 나오면 거기까지 자동으로 열림
    """
    global opened_safe_count

    if not in_range(x, y):
        return
    if state[y][x] == OPENED:
        return
    if state[y][x] == FLAGGED:
        return
    if field[y][x] == BOMB:
        return

    state[y][x] = OPENED
    opened_safe_count += 1

    bomb_count = num_of_bomb(x, y)

    if bomb_count == 0:
        for yoff in range(-1, 2):
            for xoff in range(-1, 2):
                if xoff == 0 and yoff == 0:
                    continue
                nx = x + xoff
                ny = y + yoff
                if in_range(nx, ny):
                    open_tile(nx, ny)


def reveal_all_bombs():
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if field[y][x] == BOMB:
                state[y][x] = OPENED


def check_clear():
    safe_total = WIDTH * HEIGHT - NUM_OF_BOMBS
    return opened_safe_count == safe_total


def get_bomb_distance_from_explosion(x, y):
    if exploded_pos is None:
        return 0

    ex, ey = exploded_pos
    return max(abs(x - ex), abs(y - ey))


def get_bomb_explosion_phase(x, y, now_ms):
    """
    반환값:
    0 = 아직 폭발이 번지지 않음(닫힌 칸처럼 표시)
    1 = 1차 폭발 이미지
    2 = 2차 폭발 이미지
    """
    if explosion_start_time is None or exploded_pos is None:
        return 2

    distance = get_bomb_distance_from_explosion(x, y)
    start_ms = explosion_start_time + distance * EXPLOSION_WAVE_DELAY

    if now_ms < start_ms:
        return 0
    if now_ms < start_ms + EXPLOSION_STAGE1_DURATION:
        return 1
    return 2


def get_total_explosion_duration():
    return max_explosion_distance * EXPLOSION_WAVE_DELAY + EXPLOSION_STAGE1_DURATION + EXPLOSION_POPUP_EXTRA_DELAY

# =========================
# 팝업 버튼 생성 함수
# =========================
def get_help_close_button():
    popup = pygame.Rect(170, 100, 660, 470)
    return Button(popup.centerx - 60, popup.bottom - 50, 120, 40, "닫기")


def get_end_popup_buttons():
    popup = pygame.Rect(220, 150, 560, 300)
    restart_btn = Button(popup.x + 40, popup.y + 190, 140, 48, "다시하기")
    record_btn = Button(popup.x + 210, popup.y + 190, 140, 48, "기록")
    rank_btn = Button(popup.x + 380, popup.y + 190, 140, 48, "랭킹")
    return restart_btn, record_btn, rank_btn


def get_record_popup_buttons():
    popup = pygame.Rect(250, 150, 500, 300)
    input_rect = pygame.Rect(popup.x + 160, popup.y + 122, 260, 40)
    save_btn = Button(popup.x + 110, popup.y + 220, 120, 42, "저장")
    cancel_btn = Button(popup.x + 270, popup.y + 220, 120, 42, "닫기")
    return input_rect, save_btn, cancel_btn


def get_rank_popup_buttons():
    popup = pygame.Rect(180, 80, 640, 560)
    close_btn = Button(popup.centerx - 60, popup.bottom - 55, 120, 40, "닫기")
    return close_btn

# =========================
# 그리기 함수들
# =========================
def draw_top_ui():
    pygame.draw.rect(screen, (40, 40, 40), (0, 0, SCREEN_WIDTH, TOP_UI_HEIGHT))

    btn_restart.draw(screen)
    btn_pause.draw(screen)
    btn_help.draw(screen)
    btn_rank.draw(screen)

    current_time = final_time if (game_over or game_clear) and final_time > 0 else get_elapsed_time()
    timer_text = font.render(f"시간: {current_time:.2f}초", True, (255, 255, 255))
    timer_rect = timer_text.get_rect(topright=(SCREEN_WIDTH - 20, 18))
    screen.blit(timer_text, timer_rect)


def draw_board():
    now = pygame.time.get_ticks()

    for y in range(HEIGHT):
        for x in range(WIDTH):
            px = x * SIZE
            py = y * SIZE + TOP_UI_HEIGHT

            if state[y][x] == CLOSED:
                screen.blit(img_closed, (px, py))

            elif state[y][x] == FLAGGED:
                screen.blit(img_closed, (px, py))
                screen.blit(img_flag, (px, py))

            elif state[y][x] == OPENED:
                if field[y][x] == BOMB:
                    phase = get_bomb_explosion_phase(x, y, now)

                    if phase == 0:
                        screen.blit(img_closed, (px, py))
                    elif phase == 1:
                        screen.blit(img_bomb_stage1, (px, py))
                    else:
                        screen.blit(img_bomb_stage2, (px, py))
                else:
                    bomb_count = num_of_bomb(x, y)
                    screen.blit(img_opened, (px, py))
                    if bomb_count > 0:
                        screen.blit(number_imgs[bomb_count], (px, py))


def draw_pause_overlay():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    screen.blit(overlay, (0, 0))

    txt = big_font.render("일시정지", True, (255, 255, 255))
    txt_rect = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
    screen.blit(txt, txt_rect)

    sub = small_font.render("ESC를 다시 누르면 계속 진행됩니다.", True, (255, 255, 255))
    sub_rect = sub.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 25))
    screen.blit(sub, sub_rect)


def draw_help_popup():
    popup = pygame.Rect(170, 100, 660, 470)
    pygame.draw.rect(screen, (250, 250, 250), popup, border_radius=12)
    pygame.draw.rect(screen, (20, 20, 20), popup, 2, border_radius=12)

    title = font.render("게임 방법", True, (0, 0, 0))
    screen.blit(title, (popup.x + 20, popup.y + 20))

    lines = [
        "1. 왼쪽 클릭: 칸을 엽니다.",
        "2. 오른쪽 클릭: 폭탄이 있을 것 같은 곳을 표시합니다.",
        "3. 숫자 1~8: 주변 8칸에 있는 폭탄 개수입니다.",
        "4. 빈칸(0칸)을 열면 주변 칸이 자동으로 열립니다.",
        "5. 처음 클릭한 칸과 주변은 안전하게 시작됩니다.",
        "6. 폭탄을 누르면 게임 오버입니다.",
        "7. 모든 안전한 칸을 열면 클리어입니다.",
        "8. R 키 또는 RE 버튼으로 다시 시작할 수 있습니다.",
        "9. ESC 키 또는 ESC 버튼으로 일시정지할 수 있습니다.",
        "10. 도움말/랭킹 팝업이 열리면 게임 시간도 멈춥니다."
    ]

    for i, line in enumerate(lines):
        txt = small_font.render(line, True, (20, 20, 20))
        screen.blit(txt, (popup.x + 20, popup.y + 80 + i * 33))

    close_btn = get_help_close_button()
    close_btn.draw(screen)
    return close_btn


def draw_end_popup():
    popup = pygame.Rect(220, 150, 560, 300)
    pygame.draw.rect(screen, (255, 255, 255), popup, border_radius=12)
    pygame.draw.rect(screen, (20, 20, 20), popup, 2, border_radius=12)

    if game_clear:
        title = font.render("게임 클리어!", True, (0, 140, 0))
        msg = small_font.render(f"기록 시간: {final_time:.2f}초", True, (0, 0, 0))
    else:
        title = font.render("게임 오버!", True, (200, 0, 0))
        msg = small_font.render(f"플레이 시간: {final_time:.2f}초", True, (0, 0, 0))

    title_rect = title.get_rect(center=(popup.centerx, popup.y + 45))
    msg_rect = msg.get_rect(center=(popup.centerx, popup.y + 95))
    screen.blit(title, title_rect)
    screen.blit(msg, msg_rect)

    msg2 = tiny_font.render("R 키로도 다시 시작할 수 있습니다.", True, (60, 60, 60))
    msg2_rect = msg2.get_rect(center=(popup.centerx, popup.y + 130))
    screen.blit(msg2, msg2_rect)

    restart_btn, record_btn, rank_btn = get_end_popup_buttons()
    restart_btn.draw(screen)
    record_btn.draw(screen)
    rank_btn.draw(screen)

    return restart_btn, record_btn, rank_btn


def draw_record_input_popup():
    popup = pygame.Rect(250, 150, 500, 300)
    pygame.draw.rect(screen, (255, 255, 255), popup, border_radius=12)
    pygame.draw.rect(screen, (20, 20, 20), popup, 2, border_radius=12)

    title = font.render("기록 저장", True, (0, 0, 0))
    screen.blit(title, (popup.x + 185, popup.y + 20))

    info = small_font.render(f"시간: {final_time:.2f}초", True, (0, 0, 0))
    screen.blit(info, (popup.x + 185, popup.y + 70))

    label = small_font.render("이름 입력:", True, (0, 0, 0))
    screen.blit(label, (popup.x + 60, popup.y + 130))

    input_rect, save_btn, cancel_btn = get_record_popup_buttons()

    pygame.draw.rect(screen, (245, 245, 245), input_rect, border_radius=6)
    pygame.draw.rect(screen, (50, 50, 50), input_rect, 2, border_radius=6)

    display_name = input_name if input_name else ""
    name_txt = small_font.render(display_name, True, (0, 0, 0))
    screen.blit(name_txt, (input_rect.x + 10, input_rect.y + 8))

    hint = tiny_font.render("Enter: 저장 / ESC: 닫기", True, (90, 90, 90))
    screen.blit(hint, (popup.x + 160, popup.y + 168))

    save_btn.draw(screen)
    cancel_btn.draw(screen)

    if record_saved:
        done_txt = tiny_font.render("기록이 저장되었습니다.", True, (0, 120, 0))
        screen.blit(done_txt, (popup.x + 180, popup.y + 195))

    return input_rect, save_btn, cancel_btn


def draw_rank_popup():
    popup = pygame.Rect(180, 80, 640, 560)
    pygame.draw.rect(screen, (255, 255, 255), popup, border_radius=12)
    pygame.draw.rect(screen, (20, 20, 20), popup, 2, border_radius=12)

    title = font.render("랭킹 기록", True, (0, 0, 0))
    screen.blit(title, (popup.x + 245, popup.y + 18))

    records = get_sorted_records()

    header_y = popup.y + 70
    headers = [(popup.x + 25, "순위"), (popup.x + 90, "이름"), (popup.x + 290, "결과"), (popup.x + 420, "시간")]
    for hx, label in headers:
        header_txt = small_font.render(label, True, (30, 30, 30))
        screen.blit(header_txt, (hx, header_y))

    pygame.draw.line(screen, (120, 120, 120), (popup.x + 20, header_y + 32), (popup.right - 20, header_y + 32), 2)

    if not records:
        empty_txt = small_font.render("저장된 기록이 없습니다.", True, (80, 80, 80))
        empty_rect = empty_txt.get_rect(center=(popup.centerx, popup.centery - 10))
        screen.blit(empty_txt, empty_rect)
    else:
        max_rows = 12
        start_y = header_y + 50
        row_h = 34

        for idx, item in enumerate(records[:max_rows], start=1):
            row_y = start_y + (idx - 1) * row_h
            if idx % 2 == 1:
                pygame.draw.rect(
                    screen,
                    (248, 248, 248),
                    (popup.x + 18, row_y - 2, popup.width - 36, row_h - 2),
                    border_radius=4
                )

            rank_txt = tiny_font.render(str(idx), True, (0, 0, 0))
            name_txt = tiny_font.render(str(item.get("name", "이름없음")), True, (0, 0, 0))
            result_txt = tiny_font.render(str(item.get("result", "-")), True, (0, 0, 0))
            time_txt = tiny_font.render(f"{float(item.get('time', 0.0)):.2f}초", True, (0, 0, 0))

            screen.blit(rank_txt, (popup.x + 35, row_y + 6))
            screen.blit(name_txt, (popup.x + 90, row_y + 6))
            screen.blit(result_txt, (popup.x + 300, row_y + 6))
            screen.blit(time_txt, (popup.x + 420, row_y + 6))

        guide = tiny_font.render("클리어 기록이 먼저, 같은 결과에서는 빠른 시간순으로 정렬됩니다.", True, (90, 90, 90))
        screen.blit(guide, (popup.x + 22, popup.bottom - 95))

    close_btn = get_rank_popup_buttons()
    close_btn.draw(screen)
    return close_btn

# =========================
# 시작
# =========================
reset_game()

running = True
while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if show_record_input:
                if event.key == pygame.K_ESCAPE:
                    show_record_input = False
                elif event.key == pygame.K_BACKSPACE:
                    input_name = input_name[:-1]
                elif event.key == pygame.K_RETURN:
                    if not record_saved:
                        result_text = "클리어" if game_clear else "실패"
                        add_record(input_name, final_time, result_text)
                        record_saved = True
                else:
                    if len(input_name) < 12 and event.unicode and event.unicode.isprintable():
                        input_name += event.unicode
                continue

            if event.key == pygame.K_r:
                reset_game()

            elif event.key == pygame.K_ESCAPE:
                if show_help:
                    close_help_popup()
                elif show_rank_popup:
                    close_rank_popup()
                else:
                    toggle_pause()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos

            # 기록 저장 팝업이 가장 우선
            if show_record_input:
                _, save_btn, cancel_btn = get_record_popup_buttons()

                if save_btn.collidepoint((mx, my)):
                    if not record_saved:
                        result_text = "클리어" if game_clear else "실패"
                        add_record(input_name, final_time, result_text)
                        record_saved = True

                elif cancel_btn.collidepoint((mx, my)):
                    show_record_input = False

                continue

            # 도움말 팝업
            if show_help:
                close_btn = get_help_close_button()
                if close_btn.collidepoint((mx, my)):
                    close_help_popup()
                continue

            # 랭킹 팝업
            if show_rank_popup:
                close_btn = get_rank_popup_buttons()
                if close_btn.collidepoint((mx, my)):
                    close_rank_popup()
                continue

            # 종료 팝업
            if show_end_popup:
                restart_btn, record_btn, rank_btn = get_end_popup_buttons()

                if restart_btn.collidepoint((mx, my)):
                    reset_game()

                elif record_btn.collidepoint((mx, my)):
                    show_record_input = True
                    input_name = ""
                    record_saved = False

                elif rank_btn.collidepoint((mx, my)):
                    open_rank_popup()

                continue

            # 상단 버튼
            if btn_restart.collidepoint((mx, my)):
                reset_game()
                continue

            if btn_pause.collidepoint((mx, my)):
                toggle_pause()
                continue

            if btn_help.collidepoint((mx, my)):
                open_help_popup()
                continue

            if btn_rank.collidepoint((mx, my)):
                open_rank_popup()
                continue

            # 일시정지 상태면 보드 클릭 무시
            if paused:
                continue

            # 게임 끝난 뒤 보드 클릭 무시
            if game_over or game_clear:
                continue

            # 상단 UI 영역 제외
            if my < TOP_UI_HEIGHT:
                continue

            gx = mx // SIZE
            gy = (my - TOP_UI_HEIGHT) // SIZE

            if not in_range(gx, gy):
                continue

            # 좌클릭
            if event.button == 1:
                if state[gy][gx] == FLAGGED:
                    continue

                if first_click:
                    place_bombs(gx, gy)
                    first_click = False
                    start_ticks = pygame.time.get_ticks()

                if field[gy][gx] == BOMB:
                    game_over = True
                    final_time = get_elapsed_time()
                    exploded_pos = (gx, gy)
                    explosion_start_time = pygame.time.get_ticks()
                    max_explosion_distance = 0

                    for by in range(HEIGHT):
                        for bx in range(WIDTH):
                            if field[by][bx] == BOMB:
                                max_explosion_distance = max(
                                    max_explosion_distance,
                                    get_bomb_distance_from_explosion(bx, by)
                                )

                    reveal_all_bombs()
                else:
                    open_tile(gx, gy)

                    if check_clear():
                        game_clear = True
                        final_time = get_elapsed_time()
                        show_end_popup = True

            # 우클릭
            elif event.button == 3:
                if state[gy][gx] == CLOSED:
                    state[gy][gx] = FLAGGED
                elif state[gy][gx] == FLAGGED:
                    state[gy][gx] = CLOSED

    # =========================
    # 화면 그리기
    # =========================
    if game_over and not show_end_popup and explosion_start_time is not None:
        if pygame.time.get_ticks() - explosion_start_time >= get_total_explosion_duration():
            show_end_popup = True

    screen.fill((0, 0, 0))
    draw_top_ui()
    draw_board()

    if paused and not show_help and not show_rank_popup:
        draw_pause_overlay()

    if show_help:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_help_popup()

    if show_end_popup:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_end_popup()

    if show_rank_popup:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_rank_popup()

    if show_record_input:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))
        draw_record_input_popup()

    pygame.display.flip()

pygame.quit()