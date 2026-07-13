"""
OpenFOAM process automation module.
Provides utility functions to initialize OpenFOAM case directories,
run meshing/solving commands, and query mesh metrics.
"""

import os
import shutil
import subprocess
import time
import logging
from src.config import TEMPLATE_DIR, WING_SPAN, SOLVER_NAME

# Set up logger for this module
logger = logging.getLogger(__name__)

def execute_shell_command(cmd, cwd=None):
    """
    Run a shell command, capture stdout/stderr, and handle process failures.
    
    Args:
        cmd (list): List of command arguments
        cwd (str, optional): Directory to execute the command in
        
    Returns:
        str: Captured stdout string
        
    Raises:
        subprocess.CalledProcessError: If the process returns a non-zero exit code
    """
    logger.info("Executing: %s (cwd: %s)", " ".join(cmd), cwd or os.getcwd())
    start_time = time.time()
    
    try:
        res = subprocess.run(
            cmd, 
            cwd=cwd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            check=True
        )
        elapsed = time.time() - start_time
        logger.debug("Command succeeded in %.2fs", elapsed)
        return res.stdout
    except subprocess.CalledProcessError as e:
        logger.error("Process failed with exit code %d: %s", e.returncode, " ".join(cmd))
        logger.error("STDOUT:\n%s", e.stdout)
        logger.error("STDERR:\n%s", e.stderr)
        raise

def initialize_openfoam_case(case_dir, sweep_parameter, nx, ny):
    """
    Create an OpenFOAM case folder by copying templates and injecting geometry.
    
    Args:
        case_dir (str): Target case directory path
        sweep_parameter (float): Active aero parameter t (0.0 to 1.0)
        nx (int): Number of background grid cells in X direction
        ny (int): Number of background grid cells in Y direction
    """
    logger.info("Initializing case %s (t=%s, grid=%dx%d)", case_dir, sweep_parameter, nx, ny)
    
    # 1. Clean existing case directory
    if os.path.exists(case_dir):
        logger.debug("Removing existing directory: %s", case_dir)
        shutil.rmtree(case_dir)
        
    # 2. Copy OpenFOAM template directories
    try:
        shutil.copytree(os.path.join(TEMPLATE_DIR, "system"), os.path.join(case_dir, "system"))
        shutil.copytree(os.path.join(TEMPLATE_DIR, "constant"), os.path.join(case_dir, "constant"))
        shutil.copytree(os.path.join(TEMPLATE_DIR, "0.orig"), os.path.join(case_dir, "0"))
    except IOError as e:
        logger.critical("Failed to copy template folders from %s: %s", TEMPLATE_DIR, str(e))
        raise
        
    # 3. Create constant/triSurface directory for the geometry STL
    geometry_dir = os.path.join(case_dir, "constant", "triSurface")
    os.makedirs(geometry_dir, exist_ok=True)
    stl_path = os.path.join(geometry_dir, "wing.stl")
    
    # 4. Generate geometry stl by invoking generate_geometry.py
    cmd = [
        "python3", 
        "generate_geometry.py", 
        "-t", str(sweep_parameter), 
        "-o", stl_path, 
        "-s", str(WING_SPAN)
    ]
    execute_shell_command(cmd)
    
    # 5. Modify background blockMesh resolution
    block_dict_path = os.path.join(case_dir, "system", "blockMeshDict")
    if not os.path.exists(block_dict_path):
        raise FileNotFoundError(f"blockMeshDict template missing: {block_dict_path}")
        
    with open(block_dict_path, 'r') as f:
        content = f.read()
        
    old_block_pattern = "hex (0 1 2 3 4 5 6 7) (150 80 1) simpleGrading (1 1 1)"
    new_block_pattern = f"hex (0 1 2 3 4 5 6 7) ({nx} {ny} 1) simpleGrading (1 1 1)"
    
    if old_block_pattern not in content:
        raise ValueError(f"Could not find default block description in {block_dict_path}")
        
    content = content.replace(old_block_pattern, new_block_pattern)
    
    with open(block_dict_path, 'w') as f:
        f.write(content)
        
    logger.debug("Successfully configured grid resolution in blockMeshDict")

def query_cell_count(case_dir):
    """
    Execute checkMesh and parse the final cell count.
    
    Args:
        case_dir (str): Path of the OpenFOAM case
        
    Returns:
        int: Number of mesh cells, or None if parsing fails
    """
    try:
        output = execute_shell_command(["checkMesh", "-case", case_dir])
        for line in output.split("\n"):
            if "cells:" in line:
                parts = line.split()
                # Line format: "    cells:            12345"
                return int(parts[-1])
    except (subprocess.CalledProcessError, ValueError, IndexError) as e:
        logger.warning("Could not extract cell count for %s: %s", case_dir, str(e))
    return None

def execute_openfoam_pipeline(case_dir):
    """
    Run the mesh generation and flow solver sequence.
    
    Args:
        case_dir (str): OpenFOAM case directory path
        
    Returns:
        int: Final mesh cell count
    """
    logger.info("Starting OpenFOAM solver sequence for: %s", case_dir)
    
    # 1. Background grid generation
    execute_shell_command(["blockMesh", "-case", case_dir])
    
    # 2. Surface refinement & snapping
    execute_shell_command(["snappyHexMesh", "-case", case_dir, "-overwrite"])
    
    # 3. 2D Extrusion
    execute_shell_command(["extrudeMesh", "-case", case_dir])
    
    # 4. Modify boundary patch types
    execute_shell_command(["changeDictionary", "-case", case_dir])
    
    # 5. Clean up snappyHexMesh residues in time folders by re-copying the clean 0 directory
    zero_dir = os.path.join(case_dir, "0")
    if os.path.exists(zero_dir):
        shutil.rmtree(zero_dir)
    shutil.copytree(os.path.join(TEMPLATE_DIR, "0.orig"), zero_dir)
    
    # 6. Execute RANS solver
    logger.info("Executing flow solver (%s) for %s...", SOLVER_NAME, case_dir)
    execute_shell_command([SOLVER_NAME, "-case", case_dir])
    
    # 7. Query and return cell count
    cell_count = query_cell_count(case_dir)
    return cell_count
