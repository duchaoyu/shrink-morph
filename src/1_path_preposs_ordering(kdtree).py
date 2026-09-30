import os
import itertools
import numpy as np
from compas_view2.app import App
from compas.datastructures import Network, Mesh
import pickle
from scipy.spatial import KDTree


# VARIABLE

folder = os.path.abspath("/Users/duch/Documents/PhD/knit/2024_prototypes/callibration/flat_no_shortrows")
filename = "flat_no_shortrows_prestrain"
# filename = "semi_sphere_tri"
# reconstructed polylines 
file_path = os.path.join(folder, filename + "_tri_path_recons.txt")
# order all the curves in the same direction (right to left, knitting machine direction)
exp_file_path = os.path.join(folder, filename + "_tri_path_recons_exp.txt")
sequence_file_path = os.path.join(folder, filename + "_tri_sequence_dict.pkl")
field_path = os.path.join(folder, filename + "_vertex_directional_field.txt")
mesh_path = os.path.join(folder, filename + ".obj")

# the distance between two polylines
distance = 4.762 * 1.85

bbscale = 1.02
resX = 10
resY = 10
resZ = 2

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


vecs = []
with open(field_path, 'r') as file:
    for line in file:
        # Remove whitespace and newline characters, then split by semicolon
        vec = [float(x) for x in line.split()]
        vecs.append(vec)

def get_grid_index(P, bb_scale, resolutionX, resolutionY, resolutionZ):
    # Size of index_list
    bb_min = np.min(P, axis=0)
    bb_max = np.max(P, axis=0)

    # Bounding box dimensions
    dim = bb_max - bb_min
    # a flat axis gives zero grid spacing (nan indices), so offset the
    # bounds on that axis to a non-zero extent around the geometry
    fallback = np.max(dim) if np.max(dim) > 0 else 1.0
    dim = np.where(dim > 0, dim, fallback)
    bb_min_m = bb_max - bb_scale * dim
    bb_max_m = bb_min + bb_scale * dim
    dim_m = bb_max_m - bb_min_m

    # Grid spacing
    dx = dim_m[0] / (resolutionX - 1)
    dy = dim_m[1] / (resolutionY - 1)
    dz = dim_m[2] / (resolutionZ - 1)

    grid_dim = np.array([dx, dy, dz])
    
    # index_list = [[] for _ in range(resolutionX * resolutionY * resolutionZ)]
    index_dict ={}
    for i in range(resolutionX-1):
        for j in range(resolutionY-1):
            for k in range(resolutionZ-1):
                index_dict[(i, j, k)] = []
    # Check each pt in which idx cell it belongs to

    for i in range(P.shape[0]):
        # Check the coordinate, and find the index
        pt = P[i, :]
        location = (pt - bb_min_m) / grid_dim
        grid_location = np.floor(location).astype(int)
        # idx = grid_location[0] + (resolutionX - 1) * (grid_location[1] + (resolutionY - 1) * grid_location[2])
        # Append the point index to the corresponding grid cell
        index_dict[tuple(grid_location)].append(i)
    return index_dict



def get_grid_center(P, bb_scale, resolutionX, resolutionY, resolutionZ):
    # Size of index_list
    bb_min = np.min(P, axis=0)
    bb_max = np.max(P, axis=0)

    # Bounding box dimensions
    dim = bb_max - bb_min
    # a flat axis gives zero grid spacing (nan indices), so offset the
    # bounds on that axis to a non-zero extent around the geometry
    fallback = np.max(dim) if np.max(dim) > 0 else 1.0
    dim = np.where(dim > 0, dim, fallback)
    bb_min_m = bb_max - bb_scale * dim
    bb_max_m = bb_min + bb_scale * dim
    dim_m = bb_max_m - bb_min_m

    # Grid spacing
    dx = dim_m[0] / (resolutionX - 1)
    dy = dim_m[1] / (resolutionY - 1)
    dz = dim_m[2] / (resolutionZ - 1)

    grid_dim = np.array([dx, dy, dz])
    
    # index_list = [[] for _ in range(resolutionX * resolutionY * resolutionZ)]
    index_dict ={}
    for i in range(resolutionX-1):
        for j in range(resolutionY-1):
            for k in range(resolutionZ-1):
                index_dict[(i, j, k)] = bb_min_m + np.array([(i+0.5) * dx, (j+0.5) * dy, (k+0.5) * dz]) 
    return index_dict

def get_grid_pts(P, bb_scale, resolutionX, resolutionY, resolutionZ):
    # Initialize the arrays for storing grid points
    grid_points = []

    # Grid bounds: axis-aligned bounding box
    bb_min = np.min(P, axis=0)
    bb_max = np.max(P, axis=0)

    # Bounding box dimensions
    dim = bb_max - bb_min
    # a flat axis gives zero grid spacing (nan indices), so offset the
    # bounds on that axis to a non-zero extent around the geometry
    fallback = np.max(dim) if np.max(dim) > 0 else 1.0
    dim = np.where(dim > 0, dim, fallback)
    bb_min_m = bb_max - bb_scale * dim
    bb_max_m = bb_min + bb_scale * dim
    dim_m = bb_max_m - bb_min_m

    # Grid spacing
    dx = dim_m[0] / (resolutionX - 1)
    dy = dim_m[1] / (resolutionY - 1)
    dz = dim_m[2] / (resolutionZ - 1)

    # 3D positions of the grid points
    # grid_points = np.zeros((resolutionX * resolutionY * resolutionZ, 3))

    # Create each grid point
    index = 0
    for x in range(resolutionX):
        for y in range(resolutionY):
            for z in range(resolutionZ):
                # 3D point at (x, y, z)
                grid_points.append(bb_min_m + np.array([x * dx, y * dy, z * dz]))
                index += 1

    return grid_points

def get_grid_lines(grid_points, resolutionX, resolutionY, resolutionZ):
    nnodes = grid_points.shape[0]
    grid_lines = np.zeros((3 * nnodes, 6))  # Preallocate for maximum possible lines
    num_lines = 0

    # Create lines connecting adjacent grid points
    for x in range(resolutionX):
        for y in range(resolutionY):
            for z in range(resolutionZ):
                index = x + resolutionX * (y + resolutionZ * z)
                
                # Connect lines along the x-axis
                if x < resolutionX - 1:
                    index1 = (x + 1) + y * resolutionX + z * resolutionX * resolutionY
                    grid_lines[num_lines, :3] = grid_points[index]
                    grid_lines[num_lines, 3:] = grid_points[index1]
                    num_lines += 1

                # Connect lines along the y-axis
                if y < resolutionY - 1:
                    index1 = x + (y + 1) * resolutionX + z * resolutionX * resolutionY
                    grid_lines[num_lines, :3] = grid_points[index]
                    grid_lines[num_lines, 3:] = grid_points[index1]
                    num_lines += 1

                # Connect lines along the z-axis
                if z < resolutionZ - 1:
                    index1 = x + y * resolutionX + (z + 1) * resolutionX * resolutionY
                    grid_lines[num_lines, :3] = grid_points[index]
                    grid_lines[num_lines, 3:] = grid_points[index1]
                    num_lines += 1

    # Resize grid_lines to the actual number of lines created
    grid_lines = grid_lines[:num_lines]

    return grid_lines

def distance_point_to_segment(P, A, B):
    # Vector from A to P and A to B
    P = np.array(P)
    A = np.array(A)
    B = np.array(B)
    distance = np.linalg.norm(np.cross(B-A, A-P))/np.linalg.norm(B-A)
    return distance


# pts = list(itertools.chain.from_iterable(polylines))

# save all previous polylines and the next polylines 
sequence_dict = {}
for i, polyline in enumerate(polylines):
    sequence_dict[i] = {}
    sequence_dict[i]['prev'] = []
    sequence_dict[i]['next'] = []

# create a network to save information
network = Network()
# end: 0 means not the end, 1 means the end
network.update_default_node_attributes({'end': 0, 'grid': None, 'index': None})  
network.update_default_edge_attributes({'index': None, 'sequence': None})
for i, polyline in enumerate(polylines):
    # add the first element
    network.add_node(attr_dict={'x': polyline[0][0], 'y': polyline[0][1], 'z': polyline[0][2], 'end': 1, 'index':i})
    for (a, b) in zip(polyline[:-1], polyline[1:]):
        key = network.add_node(attr_dict={'x': b[0], 'y': b[1], 'z': b[2], 'index': i})
        network.add_edge(key-1, key, attr_dict={'index': i})
    network.node_attribute(key, 'end', 1) # modify the node attribute of the last node

print(network)
pts = []    

# iterate through the nodes, and check the locations of the nodes 
for node in network.nodes():
    pts.append(network.node_coordinates(node))

pts_array = np.array(pts)
# TODO: shall i align the points with the axis?

# in each cell, which vertices are there 
cell_pt_dict = get_grid_index(pts_array, bbscale, resX, resY, resZ)
cell_poly_dict = dict.fromkeys(cell_pt_dict, set()) # key: grid; value: which polylines are contained 
for grid, indices in cell_pt_dict.items():
    grid_value = grid[0]+(resX-1)*(grid[1]+(resY-1)*grid[2])
    polyline_indices = set()
    for idx in indices:
        network.node_attribute(idx, 'grid', grid_value) # set nodes attribute grid
        polyline_indices.add(network.node_attribute(idx, 'index'))
    cell_poly_dict[grid] = polyline_indices  # get the node attribute poyline index
    
# in each cell, calculate the vector field 
mesh_xyzs = []
mesh = Mesh.from_obj(mesh_path)
for vkey in mesh.vertices():
    xyz = mesh.vertex_coordinates(vkey)
    mesh_xyzs.append(xyz)
mesh_xyzs_array = np.array(mesh_xyzs)
cell_mesh_xyz_dict = get_grid_index(mesh_xyzs_array, bbscale, resX, resY, resZ)
cell_vector_dict = dict.fromkeys(cell_pt_dict, list())
cell_center_dict = get_grid_center(pts_array, bbscale, resX, resY, resZ)
mesh_xyzs_tree = KDTree(mesh_xyzs_array)

for grid, vkeys in cell_mesh_xyz_dict.items():
    if len(vkeys) == 1:
        vkey = vkeys[0]
        cell_vector_dict[grid] = vecs[vkey]
    elif len(vkeys) > 1:
        cell_vecs = [vecs[vkey] for vkey in vkeys]
        cell_vector_dict[grid] = list(np.mean(cell_vecs, axis=0))
    else:
        # nothing in the vkeys, find the closest vkey, and use the vector at that point
        cell_center = cell_center_dict[grid]
        d, i = mesh_xyzs_tree.query(cell_center, k=1)
        cell_vector_dict[grid] = vecs[i]
        
# print(cell_vector_dict)

# which polyline each node belongs to
node_poly_index = {node: network.node_attribute(node, 'index') for node in network.nodes()}

# the points of each cell together with those of its adjacent cells, so that two
# polylines that are close but sit on opposite sides of a cell border can still
# be linked. the vector field stays per cell.
cell_nbr_pt_dict = {}
for cell in cell_pt_dict:
    nbr_pts = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for dk in (-1, 0, 1):
                nbr = (cell[0] + di, cell[1] + dj, cell[2] + dk)
                if nbr in cell_pt_dict:
                    nbr_pts.extend(cell_pt_dict[nbr])
    cell_nbr_pt_dict[cell] = nbr_pts

# iterate through all the cells
# check whether all the polylines have 2 neighbors 
for (cell, cell_polyline_indices) in cell_poly_dict.items():
    # all the points in the cell and in the cells around it
    cell_pts = cell_nbr_pt_dict[cell]
    print(cell)
    if len(cell_polyline_indices) > 0:
        for idx in cell_polyline_indices: 
                
            # print(cell_polyline_indices)
            if sequence_dict[idx]['next'] == [] or sequence_dict[idx]['prev'] == []:
                checked_indices = set(sequence_dict[idx]['next'] + sequence_dict[idx]['prev'])
                
                nodes = list(network.nodes_where({'index': idx, 'grid': cell[0]+(resX-1)*(cell[1]+(resY-1)*cell[2])}))  # the nodes indices are in order
                # print(cell, nodes)
                
                min_node = min(nodes)
                max_node = max(nodes)
                mid_node = (min_node + max_node) // 2 
                
                other_nodes = []
                for pt in cell_pts:
                    pt_idx = node_poly_index[pt]
                    if pt_idx != idx and pt_idx not in checked_indices:
                        other_nodes.append(pt)
                
                if len(other_nodes) == 0:
                    continue
                
                # other_nodes = set(cell_pts).difference(set(nodes))
                # print(cell, cell_pts, nodes, other_nodes)         
                other_nodes_list = list(other_nodes)
                other_nodes_xyz = [network.node_coordinates(node) for node in other_nodes_list]
                
                other_tree = KDTree(np.array(other_nodes_xyz))
            
                node_xyz = network.node_coordinates(mid_node)
                results = other_tree.query_ball_point(node_xyz, distance)
                nearby_points = [other_nodes_list[i] for i in results]
                nearby_points_xyz = [other_nodes_xyz[i] for i in results]
                
                for (nbr_pt, nbr_pt_xyz) in zip(nearby_points, nearby_points_xyz):
                    nbr_polyline_idx = node_poly_index[nbr_pt]
                    if nbr_polyline_idx not in checked_indices:
                        min_node_nbr_pt_vec = [b-a for (a, b) in zip(node_xyz, nbr_pt_xyz)]
                        if np.dot(min_node_nbr_pt_vec, cell_vector_dict[cell]) > 0:
                            sequence_dict[idx]['next'].append(nbr_polyline_idx)
                        else:
                            sequence_dict[idx]['prev'].append(nbr_polyline_idx)
                        checked_indices.add(nbr_polyline_idx)
                
                
                
                
                # a_diff = np.array(other_nodes_xyz) - np.array(min_node_xyz)
                # a_distances = np.sqrt(np.sum(a_diff**2, axis=1))
                # a_min_dis = np.min(a_distances)

                # if a_min_dis < distance:
                #     closest_index = np.argmin(a_distances)
                #     closest_node = other_nodes_list[closest_index]
                #     cloeset_polyline_index = network.node_attribute(closest_node, 'index')
                    
                #     if min_node_xyz[0] < other_nodes_xyz[closest_index][0]:  # OR CHANGE THE COMPARISON TO VECTOR FIELD
                #         sequence_dict[idx]['next'].append(cloeset_polyline_index)
                #         sequence_dict[cloeset_polyline_index]['prev'].append(idx)
                #     else:
                #         sequence_dict[idx]['prev'].append(cloeset_polyline_index)
                #         sequence_dict[cloeset_polyline_index]['next'].append(idx)
                #     continue
                
                # max_node_xyz = network.node_coordinates(max_node)
                # b_diff = np.array(other_nodes_xyz) - np.array(max_node_xyz)
                # b_distances = np.sqrt(np.sum(b_diff**2, axis=1))
                # b_min_dis = np.min(b_distances)
                
                # if b_min_dis < distance:
                #     closest_index = np.argmin(b_distances)
                #     closest_node = other_nodes_list[closest_index]
                #     cloeset_polyline_index = network.node_attribute(closest_node, 'index')
                    
                #     if max_node_xyz[0] < other_nodes_xyz[closest_index][0]:  # OR CHANGE THE COMPARISON TO VECTOR FIELD
                #         sequence_dict[idx]['next'].append(cloeset_polyline_index)
                #         sequence_dict[cloeset_polyline_index]['prev'].append(idx)
                #     else:
                #         sequence_dict[idx]['prev'].append(cloeset_polyline_index)
                #         sequence_dict[cloeset_polyline_index]['next'].append(idx)
                            
                        

for key in sequence_dict.keys():
    sequence_dict[key]['prev'] = list(set(sequence_dict[key]['prev']))
    sequence_dict[key]['next'] = list(set(sequence_dict[key]['next']))
    

print(sequence_dict)



with open(sequence_file_path, 'wb') as file:
    pickle.dump(sequence_dict, file)

print(f"Dictionary has been pickled and saved to {sequence_file_path}")




# viewer = App(width=800, height=800)
# # viewer.view.camera.rz = -300
# # viewer.view.camera.rx = -600
# # viewer.view.camera.tx = 0
# # viewer.view.camera.distance = 2000


# from compas.geometry import Point
# from compas.colors import Color
# from random import random

# for i, (cell, indices) in enumerate(cell_pt_dict.items()):
#     color = Color(random(), random(), random())
#     for idx in indices[::10]:
#         point = Point(*pts[idx])
#         viewer.add(point, color=color)

# # for pt in pts[::50]:
# #     point = Point(*pt)
# #     viewer.add(point)

# grid_pts = get_grid_pts(pts_array, bbscale, resX, resY, resZ)
# for grid_pt in grid_pts:
#     viewer.add(Point(*grid_pt), pointcolor=(1, 0, 0))

# viewer.show()



