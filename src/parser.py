"""
Post-processing data parsing module.
Provides clean functions to extract force coefficients, surface pressure
distributions (Cp), and wake velocity profiles from OpenFOAM output files.
"""

import os
import logging
import numpy as np
from src.config import WAKE_SAMPLING_TIME, CP_SAMPLING_TIME

logger = logging.getLogger(__name__)

def extract_force_coefficients(case_dir):
    """
    Parse forceCoeffs output file to get averaged Cd and Cl coefficients.
    
    Args:
        case_dir (str): OpenFOAM case directory path
        
    Returns:
        tuple: (avg_cd, avg_cl) or (None, None) if files are missing or empty
    """
    # Potential ESI OpenFOAM coefficient file paths
    possible_paths = [
        os.path.join(case_dir, "postProcessing", "forceCoeffs", "0", "coefficient.dat"),
        os.path.join(case_dir, "postProcessing", "forceCoeffs", "0", "forceCoeffs.dat")
    ]
    
    filepath = None
    for path in possible_paths:
        if os.path.exists(path):
            filepath = path
            break
            
    if filepath is None:
        logger.warning("Aerodynamic force coefficient data not found in %s", case_dir)
        return None, None
        
    drag_coeffs = []
    lift_coeffs = []
    
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                # Skip comments and empty lines
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        cd_val = float(parts[1])
                        cl_val = float(parts[2])
                        drag_coeffs.append(cd_val)
                        lift_coeffs.append(cl_val)
                    except ValueError:
                        logger.debug("Skipping unparseable row in %s at line %d", filepath, line_num)
                        continue
    except OSError as e:
        logger.error("OS error reading force coefficients from %s: %s", filepath, str(e))
        return None, None
        
    if not drag_coeffs:
        logger.warning("Force coefficient file %s contains no numeric data", filepath)
        return None, None
        
    # Average the last 50 iterations to ensure convergence
    num_samples = len(drag_coeffs)
    num_avg = min(50, num_samples)
    
    avg_cd = float(np.mean(drag_coeffs[-num_avg:]))
    avg_cl = float(np.mean(lift_coeffs[-num_avg:]))
    
    logger.info("Parsed %s: Cd = %.4f, Cl = %.4f (averaged over last %d iterations)", case_dir, avg_cd, avg_cl, num_avg)
    return avg_cd, avg_cl

def extract_surface_pressure_distribution(case_dir, time_step=CP_SAMPLING_TIME):
    """
    Parse the VTK file of sampled surfaces to extract coordinates and Cp values.
    
    Args:
        case_dir (str): OpenFOAM case directory path
        time_step (int): Time directory where output is stored
        
    Returns:
        tuple: (x_coords, y_coords, cp_values) as numpy arrays, or None if failed
    """
    filepath = os.path.join(case_dir, "postProcessing", "sampleCp", str(time_step), "wingSurface.vtk")
    if not os.path.exists(filepath):
        logger.warning("VTK Cp file not found at: %s", filepath)
        return None
        
    points = []
    pressures = []
    
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
    except OSError as e:
        logger.error("OS error reading VTK surface pressure from %s: %s", filepath, str(e))
        return None
        
    line_idx = 0
    num_points = 0
    total_lines = len(lines)
    
    try:
        while line_idx < total_lines:
            line = lines[line_idx].strip()
            if line.startswith("POINTS"):
                parts = line.split()
                num_points = int(parts[1])
                line_idx += 1
                for _ in range(num_points):
                    if line_idx >= total_lines:
                        raise ValueError("Unexpected EOF while parsing POINTS")
                    pt_parts = lines[line_idx].strip().split()
                    points.append([float(pt_parts[0]), float(pt_parts[1]), float(pt_parts[2])])
                    line_idx += 1
                continue
            
            if line.startswith("SCALARS p") or line.startswith("LOOKUP_TABLE"):
                if line.startswith("SCALARS p"):
                    line_idx += 1  # skip to next line (lookup table or values)
                if line_idx < total_lines and lines[line_idx].strip().startswith("LOOKUP_TABLE"):
                    line_idx += 1
                for _ in range(num_points):
                    if line_idx >= total_lines:
                        raise ValueError("Unexpected EOF while parsing pressure SCALARS")
                    pressures.append(float(lines[line_idx].strip()))
                    line_idx += 1
                break
            line_idx += 1
    except (ValueError, IndexError) as e:
        logger.error("Format error parsing VTK Cp data from %s: %s", filepath, str(e))
        return None
        
    if len(points) == len(pressures) and len(points) > 0:
        pts = np.array(points)
        ps = np.array(pressures)
        # Cp = pressure / (0.5 * rho_solver * U^2)
        # solver density = 1.0, velocity = 50 => dynamic pressure = 1250 Pa
        cp = ps / 1250.0
        return pts[:, 0], pts[:, 1], cp
        
    logger.error("Mismatch in points (%d) vs pressures (%d) parsed from %s", len(points), len(pressures), filepath)
    return None

def extract_wake_velocity_profile(case_dir, time_step=WAKE_SAMPLING_TIME):
    """
    Parse wake velocity sampling files (.xy format) to get vertical velocity deficit.
    
    Args:
        case_dir (str): OpenFOAM case directory path
        time_step (int): Solver time directory (e.g. 500)
        
    Returns:
        tuple: (y_coordinates, ux_velocities) as numpy arrays, or None if failed
    """
    filepath = os.path.join(case_dir, "postProcessing", "sampleWake", str(time_step), "wakeLine_U.xy")
    if not os.path.exists(filepath):
        logger.warning("Wake sampling file not found at: %s", filepath)
        return None
        
    y_coords, ux_velocities = [], []
    
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        y_val = float(parts[0])
                        ux_val = float(parts[1])
                        y_coords.append(y_val)
                        ux_velocities.append(ux_val)
                    except ValueError:
                        logger.debug("Skipping unparseable row in %s at line %d", filepath, line_num)
                        continue
    except OSError as e:
        logger.error("OS error reading wake data from %s: %s", filepath, str(e))
        return None
        
    if y_coords:
        return np.array(y_coords), np.array(ux_velocities)
        
    logger.warning("Wake velocity file %s contains no valid data", filepath)
    return None
