import os
import itertools
import numpy as np
from compas_view2.app import App
from compas.datastructures import Network
import pickle
from copy import deepcopy
from PIL import Image
from compas.utilities import geometric_key

# VARIABLE

folder = os.path.abspath("/Users/duch/Documents/PhD/knit/2024_prototypes/callibration/flat_no_shortrows")
filename = "flat_no_shortrows_prestrain"


# reconstructed polylines 
file_path = os.path.join(folder, filename + "_tri_path_recons.txt")
# order all the curves in the same direction (right to left, knitting machine direction)
exp_file_path = os.path.join(folder, filename + "_tri_path_recons_exp.txt")
sequence_file_path = os.path.join(folder, filename + "_tri_sequence_dict.pkl")
# order all the curves in the same direction (right to left, knitting machine direction)
feature_file_path = os.path.join(folder, filename + "_feature.txt") # the feature is for alignment

pixel_data_file_path = os.path.join(folder, filename + "_pixel_data_dict.pkl")
bitmap_file_path =  os.path.join(folder, filename + "_export_wo_optim.bmp")

# the distance between two polylines
distance = 4.762  * 1.85
dis_diag = 4.762  * 1.5

bbscale = 1.018
resX = 20
resY = 20
resZ = 2

# feature dictionary, key: geometric key of a point, value: color of the point
feature_dict = {}
with open(feature_file_path, 'r') as file:
    for line in file:
        # Remove whitespace and newline characters, then split by semicolon
        point, color  = line.strip().split('; ')
        gkey = geometric_key(map(float, point.split(',')))
        color = tuple(map(int, color.split(',')))
        feature_dict[gkey] = color
    
        
# OPTIONAL: additional features
# color marks
feature_dict_opt = {}
feature_file_path_opt = os.path.join(folder, filename + "_feature_pattern.txt")
with open(feature_file_path_opt, 'r') as file:
    for line in file:
        # Remove whitespace and newline characters, then split by semicolon
        point, color  = line.strip().split('; ')
        gkey = geometric_key(map(float, point.split(',')))
        color = tuple(map(int, color.split(',')))
        feature_dict_opt[gkey] = color

print(len(feature_dict_opt.keys()))


# # tiles
feature_tile_dict = {}
# tile_file_path = os.path.join(folder, filename + "_feature_tiles.txt")
# with open(tile_file_path, 'r') as file:
#     for line in file:
#         # Remove whitespace and newline characters, then split by semicolon
#         point, color  = line.strip().split('; ')
#         gkey = geometric_key(map(float, point.split(',')))
#         color = tuple(map(int, color.split(',')))
#         feature_tile_dict[gkey] = color

# print(len(feature_tile_dict.keys()))

# stiffness
feature_stiff_dict = {}
stiff_file_path = os.path.join(folder, filename + "_feature_soft.txt")
with open(stiff_file_path, 'r') as file:
    for line in file:
        # Remove whitespace and newline characters, then split by semicolon
        point, color  = line.strip().split('; ')
        gkey = geometric_key(map(float, point.split(',')))
        color = tuple(map(int, color.split(',')))
        feature_stiff_dict[gkey] = color

print(len(feature_stiff_dict.keys()))



polylines = []
with open(file_path, 'r') as file:
    for line in file:
        # Remove whitespace and newline characters, then split by semicolon
        point_strs = line.strip().split('; ')
        if point_strs != ['']:
            polyline = [list(map(float, point.split(','))) for point in point_strs]
            polylines.append(polyline)
        else:
            print("empty line")
            
            

with open(sequence_file_path, 'rb') as file:
    sequence_dict = pickle.load(file)

# print("Loaded dictionary:", sequence_dict)


print(sequence_dict[0])

remains = list(sequence_dict.keys())
total_polys = len(remains)
sequence = []
 
index = 0
i = 0

start = remains[0]

# while remains:
while remains != []:
    i += 1 
    temp_sequence = []
    temp_sequence.append(start)
    remains.remove(start)

    next_start = deepcopy(start)
    while True:
        nexts = sequence_dict[next_start]['next']
        if nexts == []:
            break
        found = False
        for next in nexts:
            if next in remains:
                temp_sequence.append(next)
                remains.remove(next)
                next_start = next
                found = True
                break 
        if not found:
            break
            
    prev_start = deepcopy(start)

    while True:
        prevs = sequence_dict[prev_start]['prev']
        if prevs == []:
            break   
        found = False
        for prev in prevs:
            if prev in remains:
                temp_sequence.insert(0, prev)
                remains.remove(prev)
                prev_start = prev
                found = True
                break

        if not found: 
            break
    
    # print(i, 'temp', temp_sequence)
    
    st_prevs = sequence_dict[temp_sequence[0]]['prev']
    ed_nexts = sequence_dict[temp_sequence[-1]]['next']
    
    single_entry_toggle = True
    # print('s', sequence)
    if sequence != []:
        for s in sequence:
            for prev in st_prevs:
                if prev in s:
                    prev_idx = s.index(prev)
                    # print(prev, prev_idx, s)
                    # print(s[prev_idx+1], ed_nexts, temp_sequence)
                    if prev_idx < len(s)-1 and s[prev_idx+1] in ed_nexts:
                    # if s[prev_idx+1] in ed_nexts:
                        s[prev_idx+1:prev_idx+1] = temp_sequence
                        single_entry_toggle = False
                        break
                    
            # for next in nexts:
            #     if next in s:
            #         next_idx = s.index(next)
            
            # if next_idx != None and prev_idx != None:
            #     if next_idx - prev_idx == 1:
            #         s[prev_idx+1:prev_idx+1] = temp_sequence
            #         single_entry_toggle = False
            #         break
        if single_entry_toggle:
            sequence.append(temp_sequence)
            index += 1
        
    else:
        sequence.append(temp_sequence)
        index += 1
    # print(i, sequence)
    if remains != []:
        start = remains[0]

print('finished, the sequence is ', sequence)
# print('0',remains)
print(total_polys, len(np.concatenate(sequence).tolist()))

# dictionary that saves the direction of the polylines 
polyline_dir_dict = {}

# order all the curves in the same direction (right to left, knitting machine direction) ==========================================

prev_dir = None
prev_s = None

for index, s in enumerate(sequence[0]):
    flip = False
    polyline = polylines[s]
    
    # average direction of the poyline
    diff = np.diff(polyline, axis=0)
    norms = np.linalg.norm(diff, axis=1, keepdims=True)
    normalised_diff = diff / norms
    dir = np.mean(normalised_diff, axis=0)
    
    if index != 0:
        # method 1: check distance
        dis = np.linalg.norm(np.array(polyline[0]) - np.array(prev_poyline[0]))
        if dis < dis_diag:
            pass
        elif np.linalg.norm(np.array(polyline[0]) - np.array(prev_poyline[-1])) < dis_diag:
            polyline = polyline[::-1]
            dir = dir * -1
            flip = True
        else:
            # method 2: checke dot product 
            dot_product = np.dot(dir, prev_dir)
            if dot_product < 0:
                polyline = polyline[::-1]
                dir = dir * -1
                flip = True
    
    polyline_dir_dict[s] = flip  # for checking later
    
    prev_dir = dir
    prev_poyline = polyline

# align the rest of the lists

for index, s_list in enumerate(sequence[1:]):
    # print(sequence_dict[s_list[0]], sequence_dict[s_list[-1]])
    if sequence_dict[s_list[0]]['prev'] == []:
        if sequence_dict[s_list[-1]]['next'] == []:
            print(s_list)
            raise ValueError("soemthing wrong")
        else:
            prev_polyline = polylines[sequence_dict[s_list[-1]]['next'][0]]
            if polyline_dir_dict[sequence_dict[s_list[-1]]['next'][0]] is True:
               prev_polyline = prev_polyline[::-1]
            s_list = s_list[::-1]
            
    else:
        prev_polyline = polylines[sequence_dict[s_list[0]]['prev'][0]]
    
        if polyline_dir_dict[sequence_dict[s_list[0]]['prev'][0]] is True:
            prev_polyline = prev_polyline[::-1]
        
    diff = np.diff(prev_polyline, axis=0)
    norms = np.linalg.norm(diff, axis=1, keepdims=True)
    normalised_diff = diff / norms
    prev_dir = np.mean(normalised_diff, axis=0)
    
    for s in s_list:
        flip = False
        polyline = polylines[s]
        
        # average direction of the poyline
        diff = np.diff(polyline, axis=0)
        norms = np.linalg.norm(diff, axis=1, keepdims=True)
        normalised_diff = diff / norms
        dir = np.mean(normalised_diff, axis=0)

        # method 1: check distance
        dis = np.linalg.norm(np.array(polyline[0]) - np.array(prev_poyline[0]))
        if dis < dis_diag:
            pass
        elif np.linalg.norm(np.array(polyline[0]) - np.array(prev_poyline[-1])) < dis_diag:
            polyline = polyline[::-1]
            dir = dir * -1
            flip = True
        else:
            # method 2: checke dot product 
            dot_product = np.dot(dir, prev_dir)
            if dot_product < 0:
                polyline = polyline[::-1]
                dir = dir * -1
                flip = True
        
        polyline_dir_dict[s] = flip  # for checking later
        
        prev_dir = dir
        prev_poyline = polyline
        

    
# align all the polylines in the same direction 
for i, polyline in enumerate(polylines):
    if polyline_dir_dict[i]:
        polylines[i] = polyline[::-1]



# Create a dictionary to store the pixel data ====================================================
def find_biggest_x_for_given_y(pixel_data, target_y):
    # Initialize variables to track the smallest x and the associated key
    biggest_x = -100000
    biggest_x_key = None

    # Iterate over each key in the dictionary
    for key in pixel_data.keys():
        x, y = key  # Unpack the tuple key into x and y
        # Check if this key's y matches the target y
        if y == target_y:
            # Check if this is the first match or if this x is smaller than the current smallest_x
            if x > biggest_x:
                biggest_x = x
                biggest_x_key = key

    return biggest_x


pixel_data = {}
polyline_pixol = {}

x = 0
y = 0
x_prev = 0
prev_polyline = None 

for idx in sequence[0]:
    polyline_pixol[idx] = []
    polyline = polylines[idx]
    
    if prev_polyline is not None:
        differences = np.array(polyline) - np.array(prev_polyline[0])
        distances = np.sqrt(np.sum(differences**2, axis=1))
        smallest_distance = np.min(distances)
        i_min = np.argmin(distances)
        
        if i_min == 0:
            differences = np.array(prev_polyline) - np.array(polyline[0])
            distances = np.sqrt(np.sum(differences**2, axis=1))
            smallest_distance = np.min(distances)
            i_min = np.argmin(distances)
            x = x_prev - i_min
            # check whether the next start is further from the start
        else:
            x = x_prev + i_min
            
        x_prev = x
    # define teh start point 
    # x = ? 
    
    for i, point in enumerate(polyline):
        if geometric_key(point) in feature_dict.keys():
            pixel_data[(x, y)] = feature_dict[geometric_key(point)]
            pixel_data[(x, y+1)] = feature_dict[geometric_key(point)]
        elif geometric_key(point) in feature_dict_opt.keys():
            pixel_data[(x, y)] = feature_dict_opt[geometric_key(point)]
            pixel_data[(x, y+1)] = feature_dict_opt[geometric_key(point)]
        elif geometric_key(point) in feature_tile_dict.keys():
            pixel_data[(x, y)] = feature_tile_dict[geometric_key(point)]
            pixel_data[(x, y+1)] = feature_tile_dict[geometric_key(point)]
        elif geometric_key(point) in feature_stiff_dict.keys():
            pixel_data[(x, y)] = feature_stiff_dict[geometric_key(point)]
            pixel_data[(x, y+1)] = feature_stiff_dict[geometric_key(point)]
        else:
            pixel_data[(x, y)] = (0, 0, 0)  # black
            pixel_data[(x, y+1)] = (255, 0, 0) # red
        polyline_pixol[idx].extend([(x, y), (x, y+1)])
        
        x -= 1
    prev_polyline = polyline
        
    y += 2 


pixel_data_extra = {}
insertion_location_direction = {} 
prev_polyline_set = set()
next_polyline_set = set()

for index, s_list in enumerate(sequence[1:]):
    # print(s_list[0], sequence_dict[s_list[0]], )
    len_s_list = len(s_list)
     
    prev_polyline_indices = sequence_dict[s_list[0]]['prev']
    next_polyline_indices = sequence_dict[s_list[-1]]['next']
    
    if len(set(prev_polyline_indices).intersection(set(sequence[0]))) != 0: 
        prev_polyline_idx = None
        prev_polyline_indices = list(set(prev_polyline_indices).intersection(set(sequence[0])))
        # prev_polyline_idx = list(set(prev_polyline_indices).intersection(set(sequence[0])))[0]
        for prev_polyline_idx in prev_polyline_indices:
            if prev_polyline_idx in prev_polyline_set:
                continue
            else:
                prev_polyline_set.add(prev_polyline_idx)
                break
        if prev_polyline_idx is None:
            raise ValueError("something wrong")
        sequence0_idx = sequence[0].index(prev_polyline_idx)
        prev_polyline = polylines[prev_polyline_idx]
        x_prev = find_biggest_x_for_given_y(pixel_data, sequence0_idx * 2) + 1 # whether i should minus one? 
        y = sequence0_idx*2
        insertion_location_direction[sequence0_idx*2] = {'direction': '+', 'len': len_s_list} 
        print('sequence insertion', prev_polyline_idx, sequence0_idx*2, insertion_location_direction[sequence0_idx*2])
        # print(insertion_location_direction)
        
        pixel_data_extra[sequence0_idx*2] = {}
        
        for s in s_list:
                
            polyline = polylines[s]
            differences = np.array(polyline) - np.array(prev_polyline[0])
            distances = np.sqrt(np.sum(differences**2, axis=1))
            smallest_distance = np.min(distances)
            i_min = np.argmin(distances)
            
            if i_min == 0:
                differences = np.array(prev_polyline) - np.array(polyline[0])
                distances = np.sqrt(np.sum(differences**2, axis=1))
                smallest_distance = np.min(distances)
                i_min = np.argmin(distances)
                x = x_prev - i_min
                # check whether the next start is further from the start
            else:
                x = x_prev + i_min
            x_prev = x
            
            print(s, x, x_prev)
            for i, point in enumerate(polyline):
                if geometric_key(point) in feature_dict.keys():
                    pixel_data_extra[sequence0_idx*2][(x, y)] = feature_dict[geometric_key(point)]
                    pixel_data_extra[sequence0_idx*2][(x, y+1)] = feature_dict[geometric_key(point)]
                else:
                    pixel_data_extra[sequence0_idx*2][(x, y)] = (0, 255, 0)  
                    pixel_data_extra[sequence0_idx*2][(x, y+1)] = (255, 255, 0)
            
                x -= 1
                
            prev_polyline = polyline
                
            y += 2 
    elif len(set(next_polyline_indices).intersection(set(sequence[0]))) != 0: 
        # next_polyline_idx = list(set(next_polyline_indices).intersection(set(sequence[0])))[0]
        next_polyline_idx = None
        next_polyline_indices = list(set(next_polyline_indices).intersection(set(sequence[0])))
        for next_polyline_idx in next_polyline_indices:
            if next_polyline_idx in next_polyline_set:
                continue
            else:
                next_polyline_set.add(next_polyline_idx)
                break
        if next_polyline_idx is None:
            print(next_polyline_set, next_polyline_indices)
            raise ValueError("something wrong")
        sequence0_idx = sequence[0].index(next_polyline_idx)
        
        prev_polyline = polylines[next_polyline_idx]
        x_prev = find_biggest_x_for_given_y(pixel_data, sequence0_idx * 2)  # whether i should minus one? 
        y = sequence0_idx*2
        insertion_location_direction[sequence0_idx*2] = {'direction': '-', 'len': len_s_list} 
        pixel_data_extra[sequence0_idx*2] = {}
        for s in s_list:
            
            polyline = polylines[s]
            differences = np.array(polyline) - np.array(prev_polyline[0])
            distances = np.sqrt(np.sum(differences**2, axis=1))
            smallest_distance = np.min(distances)
            i_min = np.argmin(distances)
            
            if i_min == 0:
                differences = np.array(prev_polyline) - np.array(polyline[0])
                distances = np.sqrt(np.sum(differences**2, axis=1))
                smallest_distance = np.min(distances)
                i_min = np.argmin(distances)
                x = x_prev - i_min
                # check whether the next start is further from the start
            else:
                x = x_prev + i_min
                
            x_prev = x
            for i, point in enumerate(polyline):
                pixel_data_extra[sequence0_idx*2][(x, y)] = (0, 0, 255)  
                pixel_data_extra[sequence0_idx*2][(x, y+1)] = (255, 0, 255)
                x -= 1
            prev_polyline = polyline
            y += 2 
    else:
        raise ValueError("something wrong")

print(insertion_location_direction)
# print("pixel_data_extra", pixel_data_extra.keys())
# print(pixel_data_extra[360])


pixel_data_modified = {}

pixel_data_copy = {}
for (x,y), value in pixel_data.items():
    if y not in pixel_data_copy.keys():
        pixel_data_copy[y] = {}
    pixel_data_copy[y][(x, y)] = value
    
total_add_num = 0

for line in sorted(pixel_data_copy.keys())[::2]:
    if line in insertion_location_direction.keys():
        
        direction = insertion_location_direction[line]['direction']
        add_items_num = insertion_location_direction[line]['len']*2
        
        
        if direction == '+':
            for (x,y), value in pixel_data_copy[line].items():
                pixel_data_modified[(x, y+total_add_num)] = value
            for (x,y), value in pixel_data_copy[line+1].items():
                pixel_data_modified[(x, y+total_add_num)] = value
            
            for (x,y), value in pixel_data_extra[line].items():
                pixel_data_modified[(x, y+total_add_num+2)] = value
                
                
            # for (x,y), value in pixel_data_extra[line].items():
            #     pixel_data_modified[(x, y+total_add_num)] = value
            # for (x,y), value in pixel_data_copy[line].items():
            #     pixel_data_modified[(x, y+total_add_num+add_items_num)] = value
            total_add_num += add_items_num
        elif direction == '-':
            for (x,y), value in pixel_data_extra[line].items():
                pixel_data_modified[(x, y+total_add_num)] = value
                
            for (x,y), value in pixel_data_copy[line].items():
                pixel_data_modified[(x, y+total_add_num+add_items_num)] = value
            for (x,y), value in pixel_data_copy[line+1].items():
                pixel_data_modified[(x, y+total_add_num+add_items_num)] = value
            total_add_num += add_items_num
        
    else:
        for (x,y), value in pixel_data_copy[line].items():
            pixel_data_modified[(x, y+total_add_num)] = value
        for (x,y), value in pixel_data_copy[line+1].items():
            pixel_data_modified[(x, y+total_add_num)] = value
        
        
pixel_data = pixel_data_modified



# TEMPORARY!!!! ------------------------------------------------
alignment = None
shift = 0
pixel_data_alignment = {}
for pixel_y in sorted(pixel_data_copy.keys()):
    if alignment is None:
        
        for (x,y), color in pixel_data_copy[pixel_y].items():
            if color == (0, 255, 255):
                alignment = x
                break
        for (x,y), color in pixel_data_copy[pixel_y].items():
            pixel_data_alignment[(x, y)] = color
    else:
        for (x,y), color in pixel_data_copy[pixel_y].items():
            if color == (0, 255 ,255): 
                shift = alignment - x
                break
        for (x,y), color in pixel_data_copy[pixel_y].items():
            pixel_data_alignment[(x+shift, y)] = color
            
            
pixel_data = pixel_data_alignment
# TEMPORARY!!!! ------------------------------------------------
    


with open(pixel_data_file_path, 'wb') as file:
    pickle.dump(pixel_data, file)

print(f"Dictionary has been pickled and saved to {pixel_data_file_path}")



x_all = [xy[0] for xy in pixel_data.keys()]
y_all = [xy[1] for xy in pixel_data.keys()]

min_x = min(x_all)
max_x = max(x_all)
min_y = min(y_all)
max_y = max(y_all)

x_size = max_x - min_x + 1
y_size = max_y - min_y + 1

# make sure the size fits the knitting bed
assert x_size <= 365

image = Image.new('RGB', (x_size, y_size), "white")

# optimise for the knittability
# check every second row: 0, 2, 4
# Note that in the pixel iteration, always from left to right, bottom to up
# for y in range(min_y, max_y+1, 2):
#     for x in range(min_x, max_x+1):
     
#         # the point to check
#         if (x, y) in pixel_data.keys() and (x+1, y) not in pixel_data.keys() and (x+1, y-1) in pixel_data.keys():
            
#             if (x+1, y+2) in pixel_data.keys():
#                 x += 1
#                 while (x, y+2) in pixel_data.keys():
#                     # pixel_data[(x, y)] = pixel_data[(x, y+2)]
#                     pixel_data[(x, y)] = 

#                     pixel_data.pop((x, y+2))
#                     x += 1
                    
#             else:    
#                 break
        
            
            


# print(max_x, min_x, x_size, min_y, max_y, y_size)
for (x, y), color in pixel_data.items():
    # print((x-min_x, y-min_y))
    image.putpixel((x-min_x, y-min_y), color)


# Save the image, need to flip for the machine software
flipped_image = image.transpose(Image.FLIP_TOP_BOTTOM)
flipped_image.save(bitmap_file_path)


print("Bitmap image created successfully!", x_size, y_size)
