"""
Geometry generation module for the 2026 F1 Rear Wing.
Generates NACA 4-digit airfoil profiles, applies slot positioning/rotations,
and extrudes profiles to generate watertight 3D STL files.
"""

import os
import numpy as np
from src.config import (
    MAINPLANE_CHORD, MAINPLANE_AOA, MAINPLANE_CAMBER, MAINPLANE_CAMBER_POS, MAINPLANE_THICKNESS,
    FLAP1_CHORD, FLAP1_AOA_X_MODE, FLAP1_AOA_Z_MODE, FLAP1_OVERLAP, FLAP1_GAP, FLAP1_CAMBER, FLAP1_CAMBER_POS, FLAP1_THICKNESS,
    FLAP2_CHORD, FLAP2_AOA_X_MODE, FLAP2_AOA_Z_MODE, FLAP2_OVERLAP, FLAP2_GAP, FLAP2_CAMBER, FLAP2_CAMBER_POS, FLAP2_THICKNESS
)

def generate_naca4_airfoil(max_camber, max_camber_position, thickness, chord, num_points=150):
    """
    Generate coordinates for a standard NACA 4-digit airfoil.
    
    Args:
        max_camber (float): Maximum camber as fraction of chord (e.g., 0.04)
        max_camber_position (float): Position of max camber in tenths of chord (e.g., 0.4)
        thickness (float): Maximum thickness as fraction of chord (e.g., 0.12)
        chord (float): Chord length in meters
        num_points (int): Number of points along the upper/lower surfaces
        
    Returns:
        tuple: (x_coordinates, y_coordinates) representing the closed airfoil outline
    """
    # Use cosine spacing for better resolution near the leading and trailing edges
    theta = np.linspace(0, np.pi, num_points)
    x = chord * 0.5 * (1.0 - np.cos(theta))
    
    camber_line = np.zeros_like(x)
    camber_gradient = np.zeros_like(x)
    
    if max_camber_position > 0:
        # Front of maximum camber location
        front_mask = x <= max_camber_position * chord
        if np.any(front_mask):
            camber_line[front_mask] = (
                (max_camber / max_camber_position**2) * 
                (2 * max_camber_position * (x[front_mask] / chord) - (x[front_mask] / chord)**2) * 
                chord
            )
            camber_gradient[front_mask] = (
                (2.0 * max_camber / max_camber_position**2) * 
                (max_camber_position - x[front_mask] / chord)
            )
        
        # Back of maximum camber location
        back_mask = x > max_camber_position * chord
        if np.any(back_mask):
            camber_line[back_mask] = (
                (max_camber / (1.0 - max_camber_position)**2) * 
                ((1.0 - 2.0 * max_camber_position) + 2.0 * max_camber_position * (x[back_mask] / chord) - (x[back_mask] / chord)**2) * 
                chord
            )
            camber_gradient[back_mask] = (
                (2.0 * max_camber / (1.0 - max_camber_position)**2) * 
                (max_camber_position - x[back_mask] / chord)
            )
    
    # Thickness distribution
    thickness_dist = 5.0 * thickness * chord * (
        0.2969 * np.sqrt(x/chord) 
        - 0.1260 * (x/chord) 
        - 0.3516 * (x/chord)**2 
        + 0.2843 * (x/chord)**3 
        - 0.1015 * (x/chord)**4
    )
    
    theta_c = np.arctan(camber_gradient)
    
    x_upper = x - thickness_dist * np.sin(theta_c)
    y_upper = camber_line + thickness_dist * np.cos(theta_c)
    x_lower = x + thickness_dist * np.sin(theta_c)
    y_lower = camber_line - thickness_dist * np.cos(theta_c)
    
    # Combine upper and lower coordinate arrays into a closed loop (CCW)
    # Starts at trailing edge, runs along upper surface to LE, then along lower to TE
    x_coords = np.concatenate([x_upper[::-1], x_lower[1:]])
    y_coords = np.concatenate([y_upper[::-1], y_lower[1:]])
    
    return x_coords, y_coords

def rotate_profile_points(x_coords, y_coords, angle_degrees, pivot_point=(0.0, 0.0)):
    """
    Rotate coordinates clockwise around a specified pivot point.
    
    Args:
        x_coords (np.ndarray): 1D array of X coordinates
        y_coords (np.ndarray): 1D array of Y coordinates
        angle_degrees (float): Angle of rotation in degrees (clockwise)
        pivot_point (tuple): (x, y) coordinates of pivot point
        
    Returns:
        tuple: (x_rotated, y_rotated)
    """
    rad = np.radians(-angle_degrees)  # negative for clockwise rotation
    cos_angle, sin_angle = np.cos(rad), np.sin(rad)
    
    x_shifted = x_coords - pivot_point[0]
    y_shifted = y_coords - pivot_point[1]
    
    x_rotated = x_shifted * cos_angle - y_shifted * sin_angle + pivot_point[0]
    y_rotated = x_shifted * sin_angle + y_shifted * cos_angle + pivot_point[1]
    
    return x_rotated, y_rotated

def build_multielement_profile(sweep_parameter):
    """
    Build the multi-element rear wing profile for a specific sweep parameter.
    
    Args:
        sweep_parameter (float): Value from 0.0 (X-mode, flat) to 1.0 (Z-mode, steep)
        
    Returns:
        tuple: (mainplane_coords, flap1_coords, flap2_coords, flap1_aoa, flap2_aoa)
               Where coords are (x_coords, y_coords) tuples.
    """
    # 1. Compute active flap angles of attack
    flap1_aoa = FLAP1_AOA_X_MODE + sweep_parameter * (FLAP1_AOA_Z_MODE - FLAP1_AOA_X_MODE)
    flap2_aoa = FLAP2_AOA_X_MODE + sweep_parameter * (FLAP2_AOA_Z_MODE - FLAP2_AOA_X_MODE)
    
    # 2. Mainplane Generation (fixed)
    main_x, main_y = generate_naca4_airfoil(
        MAINPLANE_CAMBER, MAINPLANE_CAMBER_POS, MAINPLANE_THICKNESS, MAINPLANE_CHORD
    )
    main_x, main_y = rotate_profile_points(main_x, main_y, MAINPLANE_AOA, pivot_point=(0.0, 0.0))
    mainplane_trailing_edge = (main_x[0], main_y[0])
    
    # 3. Flap 1 Generation & Positioning
    # Translate gap and overlap relative to mainplane trailing edge, accounting for mainplane AoA
    rad_main = np.radians(-MAINPLANE_AOA)
    cos_main, sin_main = np.cos(rad_main), np.sin(rad_main)
    
    dx1_local = -FLAP1_OVERLAP
    dy1_local = -FLAP1_GAP
    dx1 = dx1_local * cos_main - dy1_local * sin_main
    dy1 = dx1_local * sin_main + dy1_local * cos_main
    
    flap1_pivot = (mainplane_trailing_edge[0] + dx1, mainplane_trailing_edge[1] + dy1)
    
    f1_x, f1_y = generate_naca4_airfoil(
        FLAP1_CAMBER, FLAP1_CAMBER_POS, FLAP1_THICKNESS, FLAP1_CHORD
    )
    f1_x, f1_y = rotate_profile_points(f1_x, f1_y, flap1_aoa, pivot_point=(0.0, 0.0))
    f1_x += flap1_pivot[0]
    f1_y += flap1_pivot[1]
    flap1_trailing_edge = (f1_x[0], f1_y[0])
    
    # 4. Flap 2 Generation & Positioning
    rad_f1 = np.radians(-flap1_aoa)
    cos_f1, sin_f1 = np.cos(rad_f1), np.sin(rad_f1)
    
    dx2_local = -FLAP2_OVERLAP
    dy2_local = -FLAP2_GAP
    dx2 = dx2_local * cos_f1 - dy2_local * sin_f1
    dy2 = dx2_local * sin_f1 + dy2_local * cos_f1
    
    flap2_pivot = (flap1_trailing_edge[0] + dx2, flap1_trailing_edge[1] + dy2)
    
    f2_x, f2_y = generate_naca4_airfoil(
        FLAP2_CAMBER, FLAP2_CAMBER_POS, FLAP2_THICKNESS, FLAP2_CHORD
    )
    f2_x, f2_y = rotate_profile_points(f2_x, f2_y, flap2_aoa, pivot_point=(0.0, 0.0))
    f2_x += flap2_pivot[0]
    f2_y += flap2_pivot[1]
    
    # 5. Flip Y-coordinates to generate downforce (making it an inverted wing)
    main_y = -main_y
    f1_y = -f1_y
    f2_y = -f2_y
    
    # 6. Global translation: shift wing so mainplane leading edge is exactly at (0,0)
    dx_shift = -main_x[-1]
    dy_shift = -main_y[-1]
    
    main_x += dx_shift; main_y += dy_shift
    f1_x += dx_shift; f1_y += dy_shift
    f2_x += dx_shift; f2_y += dy_shift
    
    return (main_x, main_y), (f1_x, f1_y), (f2_x, f2_y), flap1_aoa, flap2_aoa

def extrude_and_triangulate_profile(x_coords, y_coords, z_min, z_max):
    """
    Extrude 2D coordinates to 3D and generate a list of triangular facets.
    
    Args:
        x_coords (np.ndarray): 1D array of closed profile X coordinates
        y_coords (np.ndarray): 1D array of closed profile Y coordinates
        z_min (float): Left spanwise limit (meters)
        z_max (float): Right spanwise limit (meters)
        
    Returns:
        list: A list of facets, where each facet is a tuple: (normal, v1, v2, v3)
    """
    num_points = len(x_coords)
    facets = []
    
    # 3D vertices for left and right caps
    vertices_left = np.column_stack([x_coords, y_coords, np.full(num_points, z_min)])
    vertices_right = np.column_stack([x_coords, y_coords, np.full(num_points, z_max)])
    
    # Centroid points to triangulate the cap polygons
    centroid_left = np.array([np.mean(x_coords), np.mean(y_coords), z_min])
    centroid_right = np.array([np.mean(x_coords), np.mean(y_coords), z_max])
    
    for i in range(num_points):
        next_i = (i + 1) % num_points
        
        # Lateral faces (quadrilaterals split into 2 triangles)
        # Triangle 1
        v1, v2, v3 = vertices_left[i], vertices_right[next_i], vertices_right[i]
        normal1 = np.cross(v2 - v1, v3 - v1)
        norm_val1 = np.linalg.norm(normal1)
        if norm_val1 > 1e-12:
            normal1 = normal1 / norm_val1
            facets.append((normal1, v1, v2, v3))
            
        # Triangle 2
        v1, v2, v3 = vertices_left[i], vertices_left[next_i], vertices_right[next_i]
        normal2 = np.cross(v2 - v1, v3 - v1)
        norm_val2 = np.linalg.norm(normal2)
        if norm_val2 > 1e-12:
            normal2 = normal2 / norm_val2
            facets.append((normal2, v1, v2, v3))
            
        # Left end cap (facing outward in -Z direction)
        v1, v2, v3 = centroid_left, vertices_left[next_i], vertices_left[i]
        normal_left = np.array([0.0, 0.0, -1.0])
        facets.append((normal_left, v1, v2, v3))
        
        # Right end cap (facing outward in +Z direction)
        v1, v2, v3 = centroid_right, vertices_right[i], vertices_right[next_i]
        normal_right = np.array([0.0, 0.0, 1.0])
        facets.append((normal_right, v1, v2, v3))
        
    return facets

def export_stl_file(filename, facets):
    """
    Write triangular facets to an ASCII STL file.
    
    Args:
        filename (str): Target STL filepath
        facets (list): List of facets in (normal, v1, v2, v3) format
    """
    with open(filename, 'w') as f:
        f.write("solid wing\n")
        for normal, v1, v2, v3 in facets:
            f.write(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {v1[0]:.6f} {v1[1]:.6f} {v1[2]:.6f}\n")
            f.write(f"      vertex {v2[0]:.6f} {v2[1]:.6f} {v2[2]:.6f}\n")
            f.write(f"      vertex {v3[0]:.6f} {v3[1]:.6f} {v3[2]:.6f}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid wing\n")
