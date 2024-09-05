from multiprocessing import Process
from threading import Thread
import random as r
import time as t
import pygame
import json
from copy import deepcopy
import os

pygame.init()

clock = pygame.time.Clock()
tickClock = pygame.time.Clock()
font = pygame.font.SysFont('Arial', 30, True)

size = 600, 500
pixel_size = 15
place_delay = 1

def shuffle_order():
    global order_x, order_y
    r.shuffle(order_x)
    r.shuffle(order_y)

def generate_grid():
    global grid, g, order_x, order_y
    
    order_x = list(range(size[0]//pixel_size))
    order_y = list(range(size[1]//pixel_size))

    grid = [[('-',-1) for y in range(size[1]//pixel_size)] for x in range(size[0]//pixel_size-2)]
    grid.append([('barrier',-1) for _ in range(size[1]//pixel_size)])
    grid.insert(0,[('barrier',-1) for _ in range(size[1]//pixel_size)])
    for i in grid:
        i[-1] = 'barrier',-1
    
    g = deepcopy(grid)

def load_collection(path, multi=False):
    collection = []

    for file in os.listdir(path):
        if not file.endswith('.json'): continue
        if multi: collection.extend(json.load(open(f'{path}/{file}')))
        else: collection.append(json.load(open(f'{path}/{file}')))

    return collection

def update_grid():
    global grid, g, order_x, order_y
    r.shuffle(patterns)
    g = deepcopy(grid)
    shuffle_order()

    # Update
    for y in order_y:
        for x in order_x:
            try: pixel,data,*_ = g[x][y]
            except:
                try: g[x][y] = pixel,-1
                except: ...
                continue

            if isinstance(pixel,tuple):
                pixel,data = pixel

            if data == -1:
                if len(colors.get(pixel,[])) == 0: data = 0
                else:
                    data = r.randrange(len(colors[pixel]))
                    g[x][y] = pixel,data

            if 'no_sim' in tags.get(pixel,[]): continue
            cellUpdateShader(x,y,pixel,g)
    
    grid = g

def shapeless(pattern,cell,grid,debug,cx,cy):
    cpixel_from, npixel_from = pattern['from']
    cpixel_to, npixel_to = pattern['to']

    if cpixel_from.startswith('#'):
        if cpixel_from.removeprefix('#') not in tags.get(cell,[]):
            return
        
        cpixel_from = cell

    elif cell != cpixel_from:
        return

    
    cpixel_from, npixel_from = pattern['from']
    cpixel_to, npixel_to = pattern['to']

    for y in range(-1,3):
        for x in range(-1,3):
            if x == 1 and y == 1: continue

            try:
                neighbour,data,*_ = grid[cx+x-1][cy+y-1]
            except Exception:
                continue

            if 'no_sim' in tags.get(neighbour,[]): continue

            match = False
            matched = [cell,'']

            # Handle tags
            if npixel_from.startswith('#'):
                if npixel_from.removeprefix('#') in tags.get(neighbour,[]):
                    npixel_from = neighbour
                    matched[1] = neighbour
                    match = True
            
            elif npixel_from == '!':
                if neighbour != '-':
                        matched[1] = neighbour
                        match = True
            
            elif npixel_from.startswith('!'):
                if npixel_from.removeprefix('!').startswith('#'):
                    if npixel_from.removeprefix('!').removeprefix('#') not in tags.get(neighbour,[]):
                        matched[1] = neighbour
                        match = True
                else:
                    if neighbour != npixel_from.removeprefix('!'):
                        matched[1] = neighbour
                        match = True
            
            elif npixel_from == '*':
                matched[1] = neighbour
                match = True
            
            else:
                if npixel_from == neighbour:
                    match = True
                    matched[1] = neighbour
                
            if match:

                # Handle @ notation
                if cpixel_to.startswith('@'):
                    i = cpixel_to.removeprefix('@')
                    cpixel_to = matched[int(i)]

                if npixel_to.startswith('@'):
                    i = npixel_to.removeprefix('@')
                    npixel_to = matched[int(i)]

                if debug: print(f'From: {cpixel_from} [{matched[0]}] {npixel_from} [{matched[1]}] -> To: {cpixel_to} {npixel_to}')
                
                if cpixel_to != '*':
                    # Set the center pixel to the new value too
                    grid[cx][cy] = cpixel_to,-1

                if npixel_to != '*':
                    # If the new pixel is *, we don't need to do anything
                    
                    # Set the neighbouring pixel to the new value
                    try: grid[cx+x][cy+y] = npixel_to,-1
                    except: ...

def shaped(pattern,cell,grid,debug,cx,cy):
    cpixel = pattern['from'][1][1]

    if cpixel == '*': raise ValueError('Center pixel cannot be "*"')

    elif cpixel.startswith('#'):
        cpixel = cpixel.removeprefix('#')
        if cpixel not in tags.get(cell,[]):
            if debug: print(f'Tag does not match: {cpixel}: {tags[cell]}')
            return
        if debug: print(f'Tag does match: {cpixel}: {tags[cell]}')

    elif cpixel != cell: return

    matched = [['-' for _ in range(3)] for _ in range(3)]

    for y in range(3):
        for x in range(3):
            try: neighbour,data = grid[cx+x-1][cy+y-1]
            except: continue
            ppixel = pattern['from'][y][x]

            if ppixel == '*': continue
            if ppixel == '!':
                if neighbour == '-':
                    return
            
            elif ppixel.startswith('!'):
                ppixel = ppixel.removeprefix('!')
                if ppixel.startswith('#'):
                    if ppixel.removeprefix('#') not in tags.get(neighbour,[]):
                        matched[x][y] == neighbour
                        ppixel = neighbour
                    else:
                        return
            

                elif ppixel == neighbour:
                    return
                

            elif ppixel.startswith('#'):
                if ppixel.removeprefix('#') in tags.get(neighbour,[]):
                    matched[x][y] = neighbour
                    ppixel = neighbour
                else:
                    return

            elif ppixel != neighbour:
                if debug: print(f'Pixel does not match: {ppixel} != {neighbour} [{cx+x-1}, {cy+y-1}]')
                return

    for y in range(3):
        for x in range(3):
            gx = cx + x - 1
            gy = cy + y - 1
            ppixel = pattern['to'][y][x]
            if ppixel == '*': continue
            if ppixel.startswith('@'):
                a,b = ppixel.removeprefix('@').split(',')
                a,b = int(a.strip()), int(b.strip())
                ppixel = matched[a][b]
            if (x,y) == (1,1):
                print(ppixel)

            try: grid[gx][gy] = ppixel,-1
            except: continue

def cellUpdateShader(cx:int,cy:int,cell:str,grid:list[list[str]],debug=False):
    for pattern in patterns:
        if 'chance' in pattern.keys():
            if r.randrange(0,pattern['chance']) != 0:
                continue
        
        # Shapeless
        if pattern.get('shapeless',False):
            shapeless(pattern,cell,grid,debug,cx,cy)
        
        # Shaped
        else:
            shaped(pattern,cell,grid,debug,cx,cy)

def fill(x,y,width,height,cell):
    for y in range(y,y+height):
        for x in range(x,x+width):
            try: grid[x][y] = cell
            except: ...

def printGrid(size=(5,5),offset=(0,0)):
    for y in range(offset[1],size[1]):
        for x in range(offset[0],size[0]):
            pixel,data = grid[x][y]
            if pixel == '-': pixel = '-'
            print(f'{pixel:<10}',end=' ')
        print()

def updateThread():
    while True:
        update_grid()
        tickClock.tick(60)

if __name__ != '__main__': exit()

generate_grid()

disp = pygame.display.set_mode(size, pygame.RESIZABLE)

patterns = load_collection('patterns',multi=True)
materials = load_collection('materials')
material_names = [material['name'] for material in materials]

tags = {material['name']: material['tags'] for material in materials}
colors = {material['name']: material['colors'] for material in materials}

total_pixels = len(grid)*len(grid[0])

a = []

for mat in material_names:
    a.extend(colors[mat])

print('--- Statistics ---')
print(f'Patterns: {len(patterns)}')
print(f'Materials: {len(materials)}')
print(f'Tags: {len(tags)}')
print(f'Colors: {len(a)}')
print(f'Grid Size: {len(grid)} x {len(grid[0])}')
print(f'Total Pixels: {total_pixels}')
print(f'Loops per tick: ~{total_pixels * len(patterns) * 9 * 4}')

for _ in range(2):
    Thread(target=updateThread,daemon=True).start()

selected = 0

dt = 1
run = True
while run:
    if not __name__ == '__main__': exit()

    # Events
    for event in pygame.event.get():
        if event.type == pygame.MOUSEWHEEL:
            y = event.dict['y']
            selected += y
            selected %= len(materials)

        elif event.type == pygame.VIDEORESIZE:
            size = event.dict['size']
            generate_grid()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                generate_grid()


        elif event.type == pygame.QUIT:
            run = False
            break


    # Reset display
    disp.fill((0,0,0))


    # Place
    if pygame.mouse.get_pressed()[0]:
        x,y = pygame.mouse.get_pos()
        x,y = x//pixel_size, y//pixel_size
        p = material_names[selected]
        try:
            g[x][y] = p,-1
            grid[x][y] = p,-1
        except Exception as e: print(e)

    # Pick
    elif pygame.mouse.get_pressed()[1]:
        x,y = pygame.mouse.get_pos()
        x,y = x//pixel_size, y//pixel_size
        try: selected = material_names.index(grid[x][y][0])
        except Exception as e: print(e)

    # Delete
    elif pygame.mouse.get_pressed()[2]:
        x,y = pygame.mouse.get_pos()
        x,y = x//pixel_size, y//pixel_size
        try:
            g[x][y] = '-',0
            grid[x][y] = '-',0
        except Exception as e: print(e)

    # Rendering
    for y in range(size[1]//pixel_size):
        for x in range(size[0]//pixel_size):
            try: pixel,data,*_ = g[x][y]
            except:
                g[x][y] = pixel,-1
            if isinstance(pixel,tuple):
                g[x][y] = pixel
                pixel,data,*_ = pixel
            if data == -1:
                if len(colors.get(pixel,[])) == 0: data = 0
                else: data = r.randrange(len(colors[pixel]))
                g[x][y] = pixel, data
                grid[x][y] = pixel, data
            
            if not str(data).isnumeric():
                data = 0

            if 'no_render' in tags.get(pixel,[]): continue

            if len(colors.get(pixel,[])) == 0:
                print(f'Found glitched pixel at {x}:{y}! [{g[x][y]}]')

            pygame.draw.rect(disp, colors.get(pixel,[(255,0,255)])[int(data)], (x*pixel_size,y*pixel_size,pixel_size,pixel_size))

    ### UI
    # Selected material icon
    m = material_names[selected]
    if not len(colors.get(m)) == 0:
        c = int(t.time()*10 % len(colors.get(m)))
        pygame.draw.rect(disp, colors.get(m,[(255,0,255)])[c], (30,10,25,25))
        pygame.draw.rect(disp,(0,0,0),(28,8,29,29),width=2)

    # Selected material name
    if m == '-': m = 'NONE'
    disp.blit(font.render(m.upper(),1,(255,255,255)),(65,5))
    # Update
    pygame.display.update()
    pygame.display.set_caption(f'SAND | FPS: {round(clock.get_fps(),2)} TPS: {round(tickClock.get_fps(),2)}')

    dt = clock.tick()
