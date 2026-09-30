import os
import itertools
import numpy as np
import pickle
from copy import deepcopy
from PIL import Image



# VARIABLE

folder = os.path.abspath("/Users/duch/Documents/PhD/knit/2024_prototypes/2part/8_15")
filename = "2part"

pixel_data_file_path = os.path.join(folder, filename + "_pixel_data_dict_o.pkl")
bitmap_file_path =  os.path.join(folder, filename + "export_w_optim_with_channel.bmp")

with open(pixel_data_file_path, 'rb') as file:
    pixel_data = pickle.load(file)
print(f"Dictionary has been loaded from {pixel_data_file_path}")


# print(pixel_data)
x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1
print("Bitmap size is", x_size, y_size)


pixel_data_y = {}
for (x, y), value in pixel_data.items():
    if y not in pixel_data_y.keys():
        pixel_data_y[y] = {}
    pixel_data_y[y][x] = value

assert min_y == 0


count = 0 
for y in range(min_y, max_y+1): 
    if y % 2 == 0 :
        if (max_x, y) in pixel_data.keys():
            pixel_data[(max_x+1, y)] = (0, 128,0) # back stitch
            # pixel_data[(max_x+2, y)] = (200, 100, 100) # front stitch
            pixel_data[(max_x+4, y)] = (0, 128,0) # back stitch
            
            # if count % 15 < 6:
            pixel_data[(max_x+3, y)] = (200, 100, 100) # front stitch
            pixel_data[(max_x+2, y)] = ( 255, 87, 51) # float
            # else:
            #     pixel_data[(max_x+2, y)] =(100, 100, 100) # float 
            
            # count += 1
            
            
    else:
        if (max_x, y) in pixel_data.keys():
            pixel_data[(max_x+1, y)] =  (200, 100, 100) 
            # pixel_data[(max_x+2, y)] =(0, 128,0)
            pixel_data[(max_x+4, y)] = (200, 100, 100) 
            
            # if count % 15 < 6:
            pixel_data[(max_x+3, y)] = (0, 128, 0)
            pixel_data[(max_x+2, y)] = ( 255, 87, 51) # float
            # else:
            #     pixel_data[(max_x+2, y)] =(100, 100, 100) # float 
                
            # count += 1 
        
        

# channel: 
# front back  front
# back  front back


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

for (x, y), color in pixel_data.items():
    # print((x-min_x, y-min_y))
    image.putpixel((x-min_x, y-min_y), color)
    

flipped_image = image.transpose(Image.FLIP_TOP_BOTTOM)
flipped_image = flipped_image.transpose(Image.FLIP_LEFT_RIGHT)
flipped_image.save(bitmap_file_path)
# image.save(filepath)


print("Bitmap image created successfully to:", bitmap_file_path, "the size is", x_size, y_size)

