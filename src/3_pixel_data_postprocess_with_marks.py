import os
import itertools
import numpy as np
import pickle
from copy import deepcopy
from PIL import Image



# VARIABLE

folder = os.path.abspath("/Users/duch/Documents/PhD/knit/2024_prototypes/callibration/flat_no_shortrows")
filename = "flat_no_shortrows_prestrain"

pixel_data_file_path = os.path.join(folder, filename + "_pixel_data_dict.pkl")
pixel_data_file_path_o = os.path.join(folder, filename + "_pixel_data_dict_o.pkl")
bitmap_file_path =  os.path.join(folder, filename + "export_w_optim.bmp")

with open(pixel_data_file_path, 'rb') as file:
    pixel_data = pickle.load(file)
print(f"Dictionary has been pickled and saved to {pixel_data_file_path}")




# double the size of the image
# - 0 - 0       
# 0 - 0 -       
# 0 - 0 -
# - 0 - 0 


new_data = {}
for (x, y), color in pixel_data.items():
    if pixel_data[(x, y)] != (0, 150, 255):
        new_data[(x, y*2)] = (0, 128, 0) # back stitch
    else:
        new_data[(x, y*2)] = (0, 150, 255)
    new_data[(x, y*2+1)] = color
    
    if y % 2 == 0:
        if x % 2 == 0: # only recolor the front stitch
            new_data[(x, y*2)] = (200, 100, 100)  # grey red, front stitch
        # else:
            new_data[(x, y*2+1)] = (100, 100, 100)  # grey, float 
    else:
        if x % 2 != 0: 
            new_data[(x, y*2+1)] = (100, 100, 100)
        # else:
            new_data[(x, y*2)] = (200, 100, 100)
            
pixel_data = new_data


# # bit map pattern
# # BT F- F0 B-
# # B0 F- F0 B-
# # F0 B- BT F-    
# # F0 B- B0 F-    


# new_data = {}
# for (x, y), color in pixel_data.items(): # one x pixel is 4 pixels
#     new_data[(x*4, y)] = color
#     new_data[(x*4+1, y)] = color
#     new_data[(x*4+2, y)] = color
#     new_data[(x*4+3, y)] = color
    
#     if y % 4 == 0:
#         new_data[(x*4+1, y)] = (200, 100, 100) # B-
#         new_data[(x*4+2, y)] = (100, 100, 200) # B0
#         new_data[(x*4+3, y)] = (100, 200, 100) # F-
#     elif y % 4 == 1:
#         new_data[(x*4+1, y)] = (200, 100, 100) # B-
#         new_data[(x*4+2, y)] = (100, 100, 100) # BT
#         new_data[(x*4+3, y)] = (100, 200, 100) # F-
#     elif y % 4 == 2:
#         new_data[(x*4, y)] = (100, 100, 200)  # B0
#         new_data[(x*4+1, y)] = (100, 200, 100) # F-
#         new_data[(x*4+3, y)] = (200, 100, 100) # B-
#     else:
#         new_data[(x*4, y)] = (100, 100, 100) # BT
#         new_data[(x*4+1, y)] = (100, 200, 100) # F-
#         new_data[(x*4+3, y)] = (200, 100, 100) # B-
    
pixel_data = new_data



# print(pixel_data)
x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1




# Calculate the new keys with flipped x values
flip = True
if flip:
    new_data = {}
    for (x, y), value in pixel_data.items():
        # Flip y value across the middle of the min and max range
        flipped_x = max_x + min_x - x
        new_data[(flipped_x, y)] = value
    pixel_data = new_data



pixel_data_y = {}
for (x, y), value in pixel_data.items():
    if y not in pixel_data_y.keys():
        pixel_data_y[y] = {}
    pixel_data_y[y][x] = value

assert min_y == 0


for i in range(min_y+1, max_y+1):  # start from 1
    if i % 2 != 0:
        # red line, even
        # save the biggest x value 
        prev_max_x = max(list(pixel_data_y[i].keys()))
      
    else:
        # black line, odd 
        xs = list(pixel_data_y[i].keys())
        line_max_x = max(xs)  # max x 
        # if > max x, there is a red line
        if prev_max_x > line_max_x: # only modify is there's a very big gap
            missing_num = prev_max_x - line_max_x
            if missing_num > 3:
                current_x = line_max_x + 1
                current_y = i+2
                
                # current_x<i+50 limit the searching not to be too far
                while missing_num > 2 and current_y < i+50 and current_y < max_y and current_x < max_x: 
                    # print(i, prev_max_x, line_max_x, max_x, max_y, current_x, current_y)
                    while current_x in pixel_data_y[current_y].keys():
                        # print(current_x, current_y)
                        # pixel_data_y[i][current_x] = pixel_data_y[current_y][current_x]
                        # pixel_data_y[i][current_x] = (100, 100, 0)  # FOR DEBUGGING
                        pixel_data_y[i][current_x] = pixel_data_y[current_y][current_x]
                        del pixel_data_y[current_y][current_x]
                        
                        # pixel_data[(current_x, i)] = (100, 100, 0)  # FOR DEBUGGING
                        pixel_data[(current_x, i)] = pixel_data[(current_x, current_y)]
                        del pixel_data[(current_x, current_y)]
                        current_x += 1
                    missing_num = prev_max_x - current_x
                    current_y += 2
                        



# add the rows in the beginning and end of the program, that are missing 
x_control = -10000
for i in range(min_y+1, max_y): # start from 1
    if i % 2 == 0:
        xs = sorted(list(pixel_data_y[i].keys()), reverse=True)
        for i_x, x in enumerate(xs):
            if x in pixel_data_y[i-1].keys():
                tem_i = i_x
                tem_x = x
                # print(i, tem_x, tem_i, xs[0:tem_i])
                break
        if tem_i >= 2 and tem_x > x_control:
            x_control = tem_x
            for x in xs[0:tem_i]:
                pixel_data[(x, i-1)] = (0, 0, 200)
                
                
x_control = -10000
for i in range(min_y+1, max_y)[::-1]:
    if i % 2 != 0:
        xs = sorted(list(pixel_data_y[i].keys()), reverse=True)
        for i_x, x in enumerate(xs):
            if x in pixel_data_y[i+1].keys():
                tem_i = i_x
                tem_x = x
                break
        if tem_i >= 3 and tem_x > x_control:
            x_control = tem_x
            for x in xs[0:tem_i]:
                pixel_data[(x, i+1)] = (0, 0, 200)
                    
            

# decrease: left side (one: pink 255, 96, 208; two: purple: 160, 32, 255)
x_control = 10000
for i in range(min_y+1, max_y)[::-1]:
    if i % 2 != 0:
        xs = sorted(list(pixel_data_y[i].keys()), reverse=False)
        for i_x, x in enumerate(xs):
            if x in pixel_data_y[i+1].keys():
                tem_i = i_x
                tem_x = x
                break
        if tem_i < 3 and tem_x <= x_control:
            x_control = tem_x
            if tem_i == 1: color = (255, 96, 208)
            else: color = (160, 32, 255)
            for x in xs[0:tem_i]:
                pixel_data[(x, i)] = color
        

# decrease: right side (one:yellow 255, 224, 32; two: orange 255, 160, 16)
x_control = -10000
for i in range(min_y+1, max_y)[::-1]:
    if i % 2 != 0:
        xs = sorted(list(pixel_data_y[i].keys()), reverse=True)
        for i_x, x in enumerate(xs):
            if x in pixel_data_y[i+1].keys():
                tem_i = i_x
                tem_x = x
                break
        if tem_i < 3 and tem_x >= x_control:
            x_control = tem_x
            if tem_i == 1: color = (255, 224, 32) # yellow
            else: color = (255, 160, 16) # orange
            for x in xs[0:tem_i]:
                pixel_data[(x, i)] = color
        

# modify the marks 
new_data = {}
pixel_data_y = {}
for (x, y), value in pixel_data.items():
    if y not in pixel_data_y.keys():
        pixel_data_y[y] = {}
    pixel_data_y[y][x] = value
x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1


add_y = 0
for y in range(min_y, max_y+1): 
    xs = sorted(list(pixel_data_y[y].keys()), reverse=True)
    if y % 2 == 0:
        for i_x, x in enumerate(xs):
            # feature color: (0, 150, 255)
            if pixel_data[(x,y)] == (0, 150, 255):
                if ((x-2,y) in pixel_data.keys() and pixel_data[(x-2,y)] == (0, 150, 255)) or ((x+2,y) in pixel_data.keys() and pixel_data[(x+2,y)] == (0, 150, 255)):
                    new_data[(x, y+add_y)] = pixel_data_y[y][x]
                else:
                # if pixel_data[(x-2,y)] == (0, 150, 255) or pixel_data[(x+2,y)] == (0, 150, 255):
                    new_data[(x, y+add_y)] = ( 255, 87, 51)
                    new_data[(x, y+add_y+1)] = ( 255, 87, 51) # orange, float
                    new_data[(x, y+add_y+2)] = (255, 192, 203) # pink
                    new_data[(x-1, y+add_y+2)] = (255, 192, 203)
                    new_data[(x, y+add_y+3)] = (255, 192, 203) # pink
                    new_data[(x-1, y+add_y+3)] = (255, 192, 203)
                    new_data[(x, y+add_y+4)] = ( 255, 87, 51)
                    add_y += 4
            else:
                new_data[(x, y+add_y)] = pixel_data_y[y][x]
    else:
        for i_x, x in enumerate(xs):
            new_data[(x, y+add_y)] = pixel_data_y[y][x]

pixel_data = new_data



# modify the tiles - color:  (160, 32, 255)

# - 0 - 0 
# 0 - 0 - 
# - 0 - 0
# 0 - 0 -

new_data = {}
pixel_data_y = {}
for (x, y), value in pixel_data.items():
    if y not in pixel_data_y.keys():
        pixel_data_y[y] = {}
    pixel_data_y[y][x] = value
x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1


add_y = 0
for y in range(min_y, max_y+1): 
    xs = sorted(list(pixel_data_y[y].keys()), reverse=False)
    for i_x, x in enumerate(xs):
        # feature color: (160, 32, 255)
        if pixel_data[(x,y)] == (160, 32, 255):
            print("tile color", x, y)
            # new_data[(x, y+add_y)] = ( 255, 87, 51)# orange, float
            new_data[(x, y+add_y+1)] = ( 255, 87, 51)
            new_data[(x-1, y+add_y+1)] = ( 255, 87, 51)
            
            
            new_data[(x-1, y+add_y+2)] = (160, 32, 255)
            new_data[(x, y+add_y+2)] = ( 255, 87, 51)
            new_data[(x+1, y+add_y+2)] = (160, 32, 255)
            new_data[(x+2, y+add_y+2)] = ( 255, 87, 51)
            
            
            new_data[(x-1, y+add_y+3)] =  ( 255, 87, 51)
            new_data[(x, y+add_y+3)] =(160, 32, 255)
            new_data[(x+1, y+add_y+3)] = ( 255, 87, 51)
            new_data[(x+2, y+add_y+3)] = (160, 32, 255)
            
            new_data[(x-1, y+add_y+4)] = (160, 32, 255)
            new_data[(x, y+add_y+4)] = ( 255, 87, 51)
            new_data[(x+1, y+add_y+4)] = (160, 32, 255)
            new_data[(x+2, y+add_y+4)] = ( 255, 87, 51)
            
            new_data[(x-1, y+add_y+5)] =  ( 255, 87, 51)
            new_data[(x, y+add_y+5)] =(160, 32, 255)
            new_data[(x+1, y+add_y+5)] = ( 255, 87, 51)
            new_data[(x+2, y+add_y+5)] = (160, 32, 255)
            
            new_data[(x-1, y+add_y+6)] =  ( 255, 87, 51)
            new_data[(x, y+add_y+6)] =  ( 255, 87, 51)

            add_y += 6
        else:
            new_data[(x, y+add_y)] = pixel_data_y[y][x]



pixel_data = new_data



# # OPTIONAL:  --------------------------------------------
# # color every 10th row
# for i in range(min_y+1, max_y+1):
#     if i % 10 == 0 or i % 10 == 1:
#         for x in pixel_data_y[i].keys():
#             pixel_data_y[i][x] = (0, 0, 200)
#             pixel_data[(x, i)] = (0, 0, 200)
# # OPTIONAL:  --------------------------------------------

x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1

image = Image.new('RGB', (x_size, y_size), "white")
print(max_x, min_x, x_size, min_y, max_y, y_size)
        
# Calculate the new keys with flipped x values
new_data = {}
for (x, y), value in pixel_data.items():
    # Flip y value across the middle of the min and max range
    flipped_x = max_x + min_x - x
    new_data[(flipped_x, y)] = value
pixel_data = new_data


with open(pixel_data_file_path_o, 'wb') as file:
    pickle.dump(pixel_data, file)

print(f"Dictionary has been pickled and saved to {pixel_data_file_path_o}")


for (x, y), color in pixel_data.items():
    # print((x-min_x, y-min_y))
    image.putpixel((x-min_x, y-min_y), color)


# Save the image, need to flip for the machine software


flipped_image = image.transpose(Image.FLIP_TOP_BOTTOM)
flipped_image = flipped_image.transpose(Image.FLIP_LEFT_RIGHT)
flipped_image.save(bitmap_file_path)
# image.save(filepath)


print("Bitmap image created successfully to:", bitmap_file_path, "the size is", x_size, y_size)
