import os
import itertools
import numpy as np
import pickle
from copy import deepcopy
from PIL import Image



# VARIABLE

folder = os.path.abspath("/Users/duch/Documents/PhD/knit/2024_prototypes/2part/7_18week")
filename = "2part"

pixel_data_file_path = os.path.join(folder, filename + "_pixel_data_dict_o.pkl")


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

split_num = 3

for split_i in range(split_num):
    bitmap_file_path =  os.path.join(folder, filename + "export_w_optim_split_{}.bmp".format(split_i))
    
    new_data = {}
    
    x_lower = min_x + int(split_i * (x_size / split_num))
    x_upper = min_x + int((split_i+1) * (x_size / split_num))
    print(min_x, max_x, x_lower, x_upper)
    
    
    for (x, y), color in pixel_data.items():
        if x >= x_lower and x < x_upper:
            new_data[(x, y)] = color

    image = Image.new('RGB', (x_upper-x_lower, y_size), "white")
    
    
    
    # print(x-min_x+x_upper, y-min_y)
    for (x, y), color in new_data.items():
        x_loc = x-min_x-int(split_i * (x_size / split_num))
        image.putpixel((x_loc, y-min_y), color)
    
    
    flipped_image = image.transpose(Image.FLIP_TOP_BOTTOM)
    flipped_image = flipped_image.transpose(Image.FLIP_LEFT_RIGHT)
    flipped_image.save(bitmap_file_path)
    # image.save(filepath)


    print("Bitmap image created successfully to:", bitmap_file_path, "the size is", x_upper-x_lower, y_size)

